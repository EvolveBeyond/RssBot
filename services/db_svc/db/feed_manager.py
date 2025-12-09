"""
Feed Manager - High-level operations for feed management with deduplication.

This module provides idempotent operations for:
- Adding feeds with automatic deduplication
- Managing feed assignments per channel
- Content processing and delivery coordination
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from sqlmodel import Session, select
from sqlalchemy.exc import IntegrityError

from .models import (
    Feed, FeedAssignment, Channel, User, Style, FeedContent, 
    PublishedMessage, normalize_feed_url, compute_content_hash
)

logger = logging.getLogger(__name__)


class FeedManager:
    """High-level feed management operations with deduplication support."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def upsert_feed_assignment(
        self, 
        feed_url: str, 
        channel_id: int, 
        assigned_by_user_id: int,
        style_id: Optional[int] = None,
        custom_config: Optional[Dict] = None
    ) -> Tuple[Feed, FeedAssignment, bool]:
        """
        Add or update feed assignment with automatic deduplication.
        
        Returns:
            (feed, assignment, created) where created indicates if assignment was new
        """
        # Normalize URL for deduplication
        normalized_url = normalize_feed_url(feed_url)
        
        # Find or create canonical feed
        feed = self.session.exec(
            select(Feed).where(Feed.normalized_url == normalized_url)
        ).first()
        
        if not feed:
            # Create new canonical feed
            feed = Feed(
                url=feed_url,
                title=custom_config.get('title') if custom_config else None,
                description=custom_config.get('description') if custom_config else None,
                is_active=True,
                is_valid=True
            )
            self.session.add(feed)
            self.session.flush()
            logger.info(f"Created canonical feed {feed.id} for {normalized_url}")
        
        # Check for existing assignment
        existing_assignment = self.session.exec(
            select(FeedAssignment).where(
                FeedAssignment.feed_id == feed.id,
                FeedAssignment.channel_id == channel_id
            )
        ).first()
        
        if existing_assignment:
            # Update existing assignment
            if style_id is not None:
                existing_assignment.style_id = style_id
            if custom_config:
                existing_assignment.custom_check_interval = custom_config.get('check_interval')
                existing_assignment.daily_limit = custom_config.get('daily_limit')
                existing_assignment.monthly_limit = custom_config.get('monthly_limit')
            
            existing_assignment.is_active = True
            self.session.commit()
            return feed, existing_assignment, False
        
        # Create new assignment
        assignment = FeedAssignment(
            feed_id=feed.id,
            channel_id=channel_id,
            assigned_by_user_id=assigned_by_user_id,
            style_id=style_id,
            custom_check_interval=custom_config.get('check_interval') if custom_config else None,
            daily_limit=custom_config.get('daily_limit') if custom_config else None,
            monthly_limit=custom_config.get('monthly_limit') if custom_config else None,
            is_active=True
        )
        
        self.session.add(assignment)
        self.session.commit()
        
        logger.info(f"Created feed assignment {assignment.id}: feed {feed.id} -> channel {channel_id}")
        return feed, assignment, True