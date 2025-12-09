"""
SQLModel database models for the RSS Bot platform.
Defines core entities and provides model introspection capabilities.

This module implements a canonical feed deduplication system where:
- Feed: Single source of truth for RSS feeds (keyed by normalized URL)
- FeedAssignment: Maps Feed -> Channel -> User with per-channel styling
- FeedContent: Individual RSS items with content-based deduplication
- PublishedMessage: Tracks delivery across channels without content duplication
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
import hashlib
import json
from urllib.parse import urlparse, urlunparse

from sqlmodel import SQLModel, Field, Relationship, create_engine, Column, String, Integer, Text, JSON, Table
from sqlalchemy import Index, UniqueConstraint, CheckConstraint, ForeignKey, DateTime, Table, Column
from pydantic import BaseModel, validator


class ModelRegistry:
    """Registry for tracking SQLModel classes for introspection."""
    _models: Dict[str, type] = {}
    
    @classmethod
    def register(cls, model_class: type):
        """Register a model for introspection."""
        cls._models[model_class.__name__] = model_class
        return model_class
    
    @classmethod
    def get_models(cls) -> Dict[str, type]:
        """Get all registered models."""
        return cls._models.copy()
    
    @classmethod
    def get_model(cls, name: str) -> Optional[type]:
        """Get a specific model by name."""
        return cls._models.get(name)


# Base model with common fields
class BaseEntity(SQLModel):
    """Base entity with common timestamp fields."""
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)


# User management models
@ModelRegistry.register
class User(BaseEntity, table=True):
    """User profiles and authentication."""
    telegram_id: int = Field(unique=True, index=True)
    username: Optional[str] = Field(default=None, index=True)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = Field(default="en")
    is_active: bool = Field(default=True)
    subscription_level: str = Field(default="free")  # free, premium, enterprise
    
    # Preferences JSON field
    preferences: Optional[str] = Field(default="{}")  # JSON string for flexibility
    
    # Relationships
    subscriptions: List["Subscription"] = Relationship(back_populates="user")
    payments: List["PaymentRecord"] = Relationship(back_populates="user")
    owned_channels: List["Channel"] = Relationship(back_populates="owner")
    owned_styles: List["Style"] = Relationship(back_populates="owner")


# Utility functions for feed URL normalization and content hashing
def normalize_feed_url(url: str) -> str:
    """Normalize feed URL for deduplication."""
    try:
        parsed = urlparse(url.strip().lower())
        # Remove fragment and common tracking parameters
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path.rstrip('/'),
            parsed.params,
            # Remove common tracking parameters
            '&'.join(p for p in (parsed.query or '').split('&') 
                    if not any(p.startswith(track) for track in ['utm_', 'ref=', 'source=', 'campaign='])),
            ''  # Remove fragment
        ))
        return normalized
    except Exception:
        return url.strip().lower()


def compute_content_hash(title: str, link: str, description: str = None, guid: str = None) -> str:
    """Compute content hash for deduplication."""
    # Primary: use GUID if available and looks like a hash/uuid
    if guid and len(guid) > 10 and not guid.startswith('http'):
        return hashlib.sha256(f"guid:{guid}".encode()).hexdigest()[:16]
    
    # Secondary: use link if unique enough
    if link and len(link) > 20:
        return hashlib.sha256(f"link:{link}".encode()).hexdigest()[:16]
    
    # Fallback: title + first 100 chars of description
    content = f"title:{title or ''}"
    if description:
        content += f":desc:{description[:100]}"
    
    return hashlib.sha256(content.encode()).hexdigest()[:16]


# Channel and Feed models (NEW ARCHITECTURE)
@ModelRegistry.register
class Channel(BaseEntity, table=True):
    """Telegram channels managed by the bot."""
    telegram_id: int = Field(unique=True, index=True)
    title: str
    username: Optional[str] = Field(default=None, index=True)
    description: Optional[str] = None
    is_public: bool = Field(default=True)  # Public/private visibility
    is_active: bool = Field(default=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    
    # Default style for this channel
    default_style_id: Optional[int] = Field(default=None, foreign_key="style.id")
    
    # Channel metadata as structured JSON
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationships
    owner: "User" = Relationship(back_populates="owned_channels")
    subscriptions: List["Subscription"] = Relationship(back_populates="channel")
    feed_assignments: List["FeedAssignment"] = Relationship(back_populates="channel")
    default_style: Optional["Style"] = Relationship()
    published_messages: List["PublishedMessage"] = Relationship(back_populates="channels", link_table="publishedmessage_channel_link")
    
    __table_args__ = (
        CheckConstraint('telegram_id != 0', name='valid_telegram_id'),
    )


@ModelRegistry.register
class Style(BaseEntity, table=True):
    """Formatting and styling rules for content rendering."""
    name: str = Field(max_length=100, index=True)
    description: Optional[str] = None
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")  # NULL = system style
    is_public: bool = Field(default=False)  # Can be used by others
    is_active: bool = Field(default=True)
    
    # Structured formatting rules
    template: Optional[str] = Field(default=None)  # Markdown/HTML template
    hashtags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    max_length: int = Field(default=4000)  # Telegram limit
    include_summary: bool = Field(default=True)
    include_link: bool = Field(default=True)
    include_media: bool = Field(default=True)
    
    # Quote/prefix rules
    quote_prefix: Optional[str] = Field(default=None)
    quote_suffix: Optional[str] = Field(default=None)
    
    # Advanced rules (JSON for flexibility)
    advanced_rules: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationships
    owner: Optional["User"] = Relationship()
    feed_assignments: List["FeedAssignment"] = Relationship(back_populates="style")
    channels_using_default: List["Channel"] = Relationship(back_populates="default_style")


@ModelRegistry.register
class Feed(BaseEntity, table=True):
    """Canonical RSS feed sources with deduplication by normalized URL."""
    # Canonical feed identification
    url: str = Field(index=True)  # Original URL as provided
    normalized_url: str = Field(unique=True, index=True)  # Normalized for deduplication
    url_hash: str = Field(unique=True, index=True)  # Hash of normalized URL
    
    # Feed metadata
    title: Optional[str] = None
    description: Optional[str] = None
    language: Optional[str] = Field(default="en")
    
    # Processing metadata
    last_checked: Optional[datetime] = None
    last_modified: Optional[str] = None  # HTTP Last-Modified header
    etag: Optional[str] = None  # HTTP ETag header
    check_interval: int = Field(default=600)  # Default check interval in seconds
    error_count: int = Field(default=0)  # Consecutive error count
    last_error: Optional[str] = None
    
    # Content statistics
    total_items_processed: int = Field(default=0)
    last_item_date: Optional[datetime] = None
    
    # Feed health and validation
    is_active: bool = Field(default=True)
    is_valid: bool = Field(default=True)
    
    # Relationships
    feed_assignments: List["FeedAssignment"] = Relationship(back_populates="feed")
    feed_contents: List["FeedContent"] = Relationship(back_populates="feed")
    
    def __init__(self, url: str, **kwargs):
        normalized_url = normalize_feed_url(url)
        url_hash = hashlib.sha256(normalized_url.encode()).hexdigest()[:16]
        super().__init__(url=url, normalized_url=normalized_url, url_hash=url_hash, **kwargs)
    
    __table_args__ = (
        Index('ix_feed_url_hash', 'url_hash'),
        Index('ix_feed_normalized_url', 'normalized_url'),
        Index('ix_feed_active', 'is_active', 'is_valid'),
    )


@ModelRegistry.register
class FeedAssignment(BaseEntity, table=True):
    """Maps canonical Feed to Channel with per-channel configuration."""
    feed_id: int = Field(foreign_key="feed.id", index=True)
    channel_id: int = Field(foreign_key="channel.id", index=True)
    assigned_by_user_id: int = Field(foreign_key="user.id", index=True)
    
    # Per-assignment styling
    style_id: Optional[int] = Field(default=None, foreign_key="style.id")
    
    # Per-assignment limits and controls
    is_active: bool = Field(default=True)
    is_paused: bool = Field(default=False)
    priority: int = Field(default=0)  # Higher = more important
    
    # Usage limits (for billing/quotas)
    monthly_limit: Optional[int] = Field(default=None)  # Max items per month
    daily_limit: Optional[int] = Field(default=None)  # Max items per day
    premium_only: bool = Field(default=False)  # Requires premium subscription
    
    # Usage tracking
    messages_sent_today: int = Field(default=0)
    messages_sent_this_month: int = Field(default=0)
    last_message_date: Optional[datetime] = None
    
    # Custom overrides
    custom_check_interval: Optional[int] = Field(default=None)  # Override feed's default
    custom_filters: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Relationships
    feed: "Feed" = Relationship(back_populates="feed_assignments")
    channel: "Channel" = Relationship(back_populates="feed_assignments")
    assigned_by_user: "User" = Relationship()
    style: Optional["Style"] = Relationship(back_populates="feed_assignments")
    
    __table_args__ = (
        UniqueConstraint('feed_id', 'channel_id', name='unique_feed_channel_assignment'),
        Index('ix_feedassignment_active', 'is_active', 'is_paused'),
        Index('ix_feedassignment_limits', 'daily_limit', 'monthly_limit'),
        CheckConstraint('monthly_limit IS NULL OR monthly_limit > 0', name='valid_monthly_limit'),
        CheckConstraint('daily_limit IS NULL OR daily_limit > 0', name='valid_daily_limit'),
    )


@ModelRegistry.register
class FeedContent(BaseEntity, table=True):
    """Individual RSS feed items with content-based deduplication."""
    feed_id: int = Field(foreign_key="feed.id", index=True)
    
    # Content identification (deduplication keys)
    content_id: str = Field(index=True)  # RSS guid or generated ID
    content_hash: str = Field(index=True)  # Hash for content deduplication
    url: str = Field(index=True)  # Item URL
    
    # Content data
    title: str
    description: Optional[str] = None
    summary: Optional[str] = None  # AI-generated summary
    author: Optional[str] = None
    
    # Temporal data
    published_date: Optional[datetime] = Field(index=True)
    updated_date: Optional[datetime] = None
    
    # Content metadata
    content_type: Optional[str] = Field(default="text")  # text, video, image, etc.
    language: Optional[str] = None
    tags: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    categories: Optional[List[str]] = Field(default_factory=list, sa_column=Column(JSON))
    
    # Processing status
    is_processed: bool = Field(default=False)
    processing_error: Optional[str] = None
    
    # Raw content for analysis
    raw_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    
    # Relationships
    feed: "Feed" = Relationship(back_populates="feed_contents")
    published_messages: List["PublishedMessage"] = Relationship(back_populates="feed_content")
    
    def __init__(self, title: str, url: str, feed_id: int, content_id: str = None, **kwargs):
        if not content_id:
            content_id = kwargs.get('guid', url)
        
        content_hash = compute_content_hash(
            title=title,
            link=url,
            description=kwargs.get('description'),
            guid=content_id
        )
        
        super().__init__(
            feed_id=feed_id,
            content_id=content_id,
            content_hash=content_hash,
            url=url,
            title=title,
            **kwargs
        )
    
    __table_args__ = (
        UniqueConstraint('feed_id', 'content_hash', name='unique_feed_content'),
        Index('ix_feedcontent_hash_date', 'content_hash', 'published_date'),
        Index('ix_feedcontent_processed', 'is_processed'),
    )


# Association table for many-to-many relationship between PublishedMessage and Channel
publishedmessage_channel_link = Table(
    "publishedmessage_channel_link",
    SQLModel.metadata,
    Column("published_message_id", Integer, ForeignKey("publishedmessage.id"), primary_key=True),
    Column("channel_id", Integer, ForeignKey("channel.id"), primary_key=True),
    Column("telegram_message_id", Integer, nullable=True),  # Telegram's message ID in this channel
    Column("sent_at", DateTime, nullable=True),
    Column("send_status", String(20), default="pending"),  # pending, sent, failed
    Column("error_message", String(500), nullable=True),
)


@ModelRegistry.register
class PublishedMessage(BaseEntity, table=True):
    """Tracks canonical published content across multiple channels."""
    feed_content_id: int = Field(foreign_key="feedcontent.id", index=True)
    
    # Message state
    status: str = Field(default="pending", index=True)  # pending, processing, sent, failed
    scheduled_for: Optional[datetime] = Field(default=None, index=True)
    
    # Formatted content cache (base format before per-channel styling)
    base_formatted_content: Optional[str] = Field(default=None, sa_column=Column(Text))
    formatting_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, sa_column=Column(JSON))
    
    # Delivery tracking
    total_channels: int = Field(default=0)
    successful_deliveries: int = Field(default=0)
    failed_deliveries: int = Field(default=0)
    
    # Error tracking
    last_error: Optional[str] = None
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    
    # Relationships
    feed_content: "FeedContent" = Relationship(back_populates="published_messages")
    channels: List["Channel"] = Relationship(back_populates="published_messages", link_table=publishedmessage_channel_link)
    
    __table_args__ = (
        Index('ix_publishedmessage_status_scheduled', 'status', 'scheduled_for'),
        Index('ix_publishedmessage_content', 'feed_content_id'),
    )


# Subscription management
@ModelRegistry.register
class Subscription(BaseEntity, table=True):
    """User subscriptions to channels."""
    user_id: int = Field(foreign_key="user.id", index=True)
    channel_id: int = Field(foreign_key="channel.id", index=True)
    is_active: bool = Field(default=True)
    subscription_type: str = Field(default="free")  # free, premium
    
    # Notification preferences
    notify_new_posts: bool = Field(default=True)
    custom_filters: Optional[str] = Field(default="{}")  # JSON filters
    
    # Relationships
    user: User = Relationship(back_populates="subscriptions")
    channel: Channel = Relationship(back_populates="subscriptions")


# Payment models
class PaymentStatus(str, Enum):
    """Payment status enumeration."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"
    CANCELLED = "cancelled"


@ModelRegistry.register
class PaymentRecord(BaseEntity, table=True):
    """Payment transaction records."""
    user_id: int = Field(foreign_key="user.id", index=True)
    amount: float  # Amount in USD cents or smallest currency unit
    currency: str = Field(default="USD")
    status: PaymentStatus = Field(default=PaymentStatus.PENDING)
    
    # Payment provider details
    provider: str  # "telegram", "stripe", etc.
    external_id: Optional[str] = Field(index=True)  # Provider's transaction ID
    
    # Product information
    plan_id: Optional[str] = None  # Subscription plan identifier
    description: str
    
    # Metadata
    metadata: Optional[str] = Field(default="{}")  # JSON for additional data
    
    # Relationships
    user: User = Relationship(back_populates="payments")


# Service registry models (for controller service)
@ModelRegistry.register
class ServiceInstance(BaseEntity, table=True):
    """Service registry for microservice discovery."""
    name: str = Field(index=True)
    version: str
    base_url: str
    health_endpoint: str = Field(default="/health")
    
    # Service metadata
    capabilities: Optional[str] = Field(default="[]")  # JSON list of capabilities
    status: str = Field(default="healthy")  # healthy, unhealthy, unknown
    last_heartbeat: Optional[datetime] = None
    
    # Service configuration
    metadata: Optional[str] = Field(default="{}")  # JSON metadata


# Schema models for API responses
class ModelInfo(BaseModel):
    """Model information for introspection API."""
    name: str
    fields: Dict[str, Any]
    relationships: List[str]
    table_name: Optional[str]


class TableInfo(BaseModel):
    """Table information for introspection API."""
    name: str
    model_name: str
    columns: List[str]
    primary_key: List[str]
    foreign_keys: List[str]