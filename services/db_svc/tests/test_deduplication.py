"""
Tests for feed deduplication and canonical feed management.
"""

import pytest
import tempfile
import os
from datetime import datetime
from sqlmodel import Session, create_engine, SQLModel
from sqlalchemy import text

# Add parent directory to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from db.models import (
    User, Channel, Feed, FeedAssignment, Style, FeedContent, 
    PublishedMessage, normalize_feed_url, compute_content_hash
)
from db.feed_manager import FeedManager


@pytest.fixture
def test_engine():
    """Create test database engine."""
    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    return engine


@pytest.fixture
def test_session(test_engine):
    """Create test database session."""
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def test_user(test_session):
    """Create test user."""
    user = User(
        telegram_id=123456789,
        username="testuser",
        first_name="Test",
        last_name="User"
    )
    test_session.add(user)
    test_session.commit()
    test_session.refresh(user)
    return user


@pytest.fixture
def test_style(test_session, test_user):
    """Create test style."""
    style = Style(
        name="Test Style",
        description="Test style for testing",
        owner_id=test_user.id,
        template="<b>{title}</b>\n{description}\n{tags}\n<a href='{url}'>Link</a>",
        hashtags=["#test"],
        is_public=True
    )
    test_session.add(style)
    test_session.commit()
    test_session.refresh(style)
    return style


@pytest.fixture
def test_channels(test_session, test_user, test_style):
    """Create test channels."""
    channels = []
    for i in range(2):
        channel = Channel(
            telegram_id=-1001000000000 - i,
            title=f"Test Channel {i+1}",
            username=f"test_channel_{i+1}",
            owner_id=test_user.id,
            default_style_id=test_style.id,
            is_public=True
        )
        test_session.add(channel)
        channels.append(channel)
    
    test_session.commit()
    for channel in channels:
        test_session.refresh(channel)
    return channels


class TestURLNormalization:
    """Test URL normalization for deduplication."""
    
    def test_basic_normalization(self):
        """Test basic URL normalization."""
        urls = [
            "https://example.com/feed.xml",
            "HTTPS://EXAMPLE.COM/feed.xml",
            "https://example.com/feed.xml/",
            "https://example.com/feed.xml?utm_source=test&ref=social",
        ]
        
        normalized = [normalize_feed_url(url) for url in urls]
        
        # All should normalize to the same URL
        assert len(set(normalized)) == 1
        assert normalized[0] == "https://example.com/feed.xml"
    
    def test_parameter_removal(self):
        """Test removal of tracking parameters."""
        url_with_tracking = "https://example.com/feed?utm_source=test&utm_campaign=social&other_param=keep"
        normalized = normalize_feed_url(url_with_tracking)
        
        assert "utm_" not in normalized
        assert "other_param=keep" in normalized
    
    def test_invalid_url_handling(self):
        """Test handling of invalid URLs."""
        invalid_urls = [
            "not-a-url",
            "",
            "ftp://invalid",
        ]
        
        for url in invalid_urls:
            normalized = normalize_feed_url(url)
            # Should return lowercased version as fallback
            assert isinstance(normalized, str)


class TestContentHashing:
    """Test content hashing for deduplication."""
    
    def test_guid_based_hashing(self):
        """Test hashing based on GUID."""
        hash1 = compute_content_hash(
            title="Test Article",
            link="https://example.com/article",
            guid="unique-guid-12345"
        )
        
        hash2 = compute_content_hash(
            title="Different Title",
            link="https://different.com/article", 
            guid="unique-guid-12345"
        )
        
        # Should be the same because GUID is the same
        assert hash1 == hash2
    
    def test_url_based_hashing(self):
        """Test hashing based on URL when no GUID."""
        hash1 = compute_content_hash(
            title="Test Article",
            link="https://example.com/unique-article"
        )
        
        hash2 = compute_content_hash(
            title="Different Title",
            link="https://example.com/unique-article"
        )
        
        # Should be the same because URL is the same
        assert hash1 == hash2
    
    def test_content_based_hashing(self):
        """Test hashing based on title and description."""
        hash1 = compute_content_hash(
            title="Unique Title",
            link="https://example.com/article1",
            description="This is the article description"
        )
        
        hash2 = compute_content_hash(
            title="Unique Title",
            link="https://example.com/article2",
            description="This is the article description"
        )
        
        # Should be the same because title and description are the same
        assert hash1 == hash2


class TestFeedModel:
    """Test Feed model with deduplication."""
    
    def test_feed_creation(self, test_session):
        """Test creating canonical feeds."""
        feed = Feed(
            url="https://example.com/feed.xml",
            title="Test Feed"
        )
        test_session.add(feed)
        test_session.commit()
        
        assert feed.normalized_url == "https://example.com/feed.xml"
        assert feed.url_hash is not None
        assert len(feed.url_hash) == 16
    
    def test_duplicate_feed_prevention(self, test_session):
        """Test that duplicate feeds are prevented."""
        # Create first feed
        feed1 = Feed(
            url="https://example.com/feed.xml",
            title="Feed 1"
        )
        test_session.add(feed1)
        test_session.commit()
        
        # Try to create duplicate with different URL format
        feed2 = Feed(
            url="HTTPS://EXAMPLE.COM/feed.xml/",
            title="Feed 2"
        )
        test_session.add(feed2)
        
        # Should raise integrity error due to unique constraint
        with pytest.raises(Exception):  # IntegrityError or similar
            test_session.commit()


class TestFeedAssignment:
    """Test FeedAssignment model and relationships."""
    
    def test_assignment_creation(self, test_session, test_channels, test_user, test_style):
        """Test creating feed assignments."""
        # Create feed
        feed = Feed(url="https://example.com/feed.xml", title="Test Feed")
        test_session.add(feed)
        test_session.flush()
        
        # Create assignment
        assignment = FeedAssignment(
            feed_id=feed.id,
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id,
            style_id=test_style.id,
            daily_limit=100,
            monthly_limit=3000
        )
        test_session.add(assignment)
        test_session.commit()
        
        assert assignment.feed.url == "https://example.com/feed.xml"
        assert assignment.channel.title == "Test Channel 1"
        assert assignment.daily_limit == 100
    
    def test_unique_feed_channel_constraint(self, test_session, test_channels, test_user):
        """Test unique constraint on feed-channel assignments."""
        # Create feed
        feed = Feed(url="https://example.com/feed.xml", title="Test Feed")
        test_session.add(feed)
        test_session.flush()
        
        # Create first assignment
        assignment1 = FeedAssignment(
            feed_id=feed.id,
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id
        )
        test_session.add(assignment1)
        test_session.commit()
        
        # Try to create duplicate assignment
        assignment2 = FeedAssignment(
            feed_id=feed.id,
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id
        )
        test_session.add(assignment2)
        
        # Should raise integrity error
        with pytest.raises(Exception):
            test_session.commit()


class TestFeedManager:
    """Test FeedManager for high-level operations."""
    
    def test_upsert_new_feed(self, test_session, test_channels, test_user, test_style):
        """Test adding a new feed creates both Feed and FeedAssignment."""
        manager = FeedManager(test_session)
        
        feed, assignment, created = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id,
            style_id=test_style.id,
            custom_config={'daily_limit': 50}
        )
        
        assert created is True
        assert feed.url == "https://example.com/rss.xml"
        assert assignment.channel_id == test_channels[0].id
        assert assignment.daily_limit == 50
    
    def test_upsert_existing_feed_new_channel(self, test_session, test_channels, test_user, test_style):
        """Test adding existing feed to new channel."""
        manager = FeedManager(test_session)
        
        # First assignment
        feed1, assignment1, created1 = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id,
            style_id=test_style.id
        )
        
        # Second assignment to different channel (same feed)
        feed2, assignment2, created2 = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",  # Same URL
            channel_id=test_channels[1].id,  # Different channel
            assigned_by_user_id=test_user.id,
            style_id=test_style.id
        )
        
        assert created1 is True
        assert created2 is True
        assert feed1.id == feed2.id  # Same canonical feed
        assert assignment1.id != assignment2.id  # Different assignments
        assert assignment1.channel_id != assignment2.channel_id
    
    def test_upsert_duplicate_assignment(self, test_session, test_channels, test_user, test_style):
        """Test updating existing assignment."""
        manager = FeedManager(test_session)
        
        # First assignment
        feed1, assignment1, created1 = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",
            channel_id=test_channels[0].id,
            assigned_by_user_id=test_user.id,
            style_id=test_style.id,
            custom_config={'daily_limit': 50}
        )
        
        # Same assignment with different config
        feed2, assignment2, created2 = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",  # Same URL
            channel_id=test_channels[0].id,  # Same channel
            assigned_by_user_id=test_user.id,
            style_id=test_style.id,
            custom_config={'daily_limit': 100}  # Different limit
        )
        
        assert created1 is True
        assert created2 is False  # Updated existing
        assert feed1.id == feed2.id
        assert assignment1.id == assignment2.id  # Same assignment object
        assert assignment2.daily_limit == 100  # Updated limit
    
    def test_deduplication_with_url_variants(self, test_session, test_channels, test_user, test_style):
        """Test that URL variants are deduplicated correctly."""
        manager = FeedManager(test_session)
        
        url_variants = [
            "https://example.com/feed.xml",
            "HTTPS://EXAMPLE.COM/feed.xml",
            "https://example.com/feed.xml/",
            "https://example.com/feed.xml?utm_source=test"
        ]
        
        canonical_feed_id = None
        
        for i, url in enumerate(url_variants):
            feed, assignment, created = manager.upsert_feed_assignment(
                feed_url=url,
                channel_id=test_channels[0].id,
                assigned_by_user_id=test_user.id,
                style_id=test_style.id
            )
            
            if canonical_feed_id is None:
                canonical_feed_id = feed.id
                assert created is True  # First assignment created
            else:
                assert feed.id == canonical_feed_id  # Same canonical feed
                assert created is False  # Assignment updated, not created
        
        # Verify only one canonical feed exists
        all_feeds = test_session.exec(select(Feed)).all()
        normalized_urls = [f.normalized_url for f in all_feeds]
        assert len(set(normalized_urls)) == 1  # Only one unique normalized URL


class TestFeedContent:
    """Test FeedContent model with content deduplication."""
    
    def test_content_creation(self, test_session, test_channels, test_user):
        """Test creating feed content with deduplication."""
        # Create feed
        feed = Feed(url="https://example.com/feed.xml", title="Test Feed")
        test_session.add(feed)
        test_session.flush()
        
        # Create content
        content = FeedContent(
            feed_id=feed.id,
            title="Test Article",
            url="https://example.com/article1",
            description="This is a test article",
            content_id="article-123"
        )
        test_session.add(content)
        test_session.commit()
        
        assert content.content_hash is not None
        assert len(content.content_hash) == 16
        assert content.feed_id == feed.id
    
    def test_content_deduplication(self, test_session, test_channels, test_user):
        """Test that identical content is deduplicated."""
        # Create feed
        feed = Feed(url="https://example.com/feed.xml", title="Test Feed")
        test_session.add(feed)
        test_session.flush()
        
        # Create first content
        content1 = FeedContent(
            feed_id=feed.id,
            title="Test Article",
            url="https://example.com/article",
            description="Description",
            content_id="guid-123"
        )
        test_session.add(content1)
        test_session.commit()
        
        # Try to create duplicate content (same GUID)
        content2 = FeedContent(
            feed_id=feed.id,
            title="Different Title",  # Different title
            url="https://example.com/different",  # Different URL
            description="Different description",
            content_id="guid-123"  # Same GUID
        )
        test_session.add(content2)
        
        # Should raise integrity error due to unique constraint
        with pytest.raises(Exception):
            test_session.commit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])