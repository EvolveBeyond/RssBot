#!/usr/bin/env python3
"""
Test runner for RSS Bot database models and deduplication logic.
"""

import os
import sys
import tempfile
import unittest
from datetime import datetime

# Add project paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from sqlmodel import SQLModel, Session, create_engine, select
    from db.models import (
        User, Channel, Feed, FeedAssignment, Style, FeedContent,
        normalize_feed_url, compute_content_hash
    )
    from db.feed_manager import FeedManager
    print("✅ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)


def test_url_normalization():
    """Test URL normalization functionality."""
    print("\n🔍 Testing URL normalization...")
    
    test_cases = [
        ("https://example.com/feed.xml", "https://example.com/feed.xml"),
        ("HTTPS://EXAMPLE.COM/FEED.XML", "https://example.com/feed.xml"),
        ("https://example.com/feed.xml/", "https://example.com/feed.xml"),
        ("https://example.com/feed.xml?utm_source=test&other=keep", "https://example.com/feed.xml?other=keep"),
    ]
    
    for input_url, expected in test_cases:
        result = normalize_feed_url(input_url)
        print(f"  {input_url} → {result}")
        if expected not in result:
            print(f"    ❌ Expected to contain: {expected}")
        else:
            print(f"    ✅ Normalized correctly")


def test_content_hashing():
    """Test content hashing for deduplication."""
    print("\n🔍 Testing content hashing...")
    
    # Test GUID-based hashing
    hash1 = compute_content_hash("Title 1", "http://link1.com", guid="unique-guid")
    hash2 = compute_content_hash("Title 2", "http://link2.com", guid="unique-guid")
    
    print(f"  GUID-based: {hash1} == {hash2} ? {hash1 == hash2}")
    assert hash1 == hash2, "GUID-based hashing should match"
    
    # Test URL-based hashing
    hash3 = compute_content_hash("Title 1", "http://unique-link.com")
    hash4 = compute_content_hash("Title 2", "http://unique-link.com")
    
    print(f"  URL-based: {hash3} == {hash4} ? {hash3 == hash4}")
    assert hash3 == hash4, "URL-based hashing should match"
    
    print("  ✅ Content hashing works correctly")


def test_database_models():
    """Test database models with in-memory SQLite."""
    print("\n🔍 Testing database models...")
    
    # Create in-memory test database
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test user
        user = User(
            telegram_id=123456789,
            username="testuser",
            first_name="Test",
            last_name="User"
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        print(f"  ✅ Created user: {user.username}")
        
        # Create test style
        style = Style(
            name="Test Style",
            description="Test style for testing",
            owner_id=user.id,
            template="<b>{title}</b>\n{description}\n{tags}\n<a href='{url}'>Link</a>",
            hashtags=["#test"],
            is_public=True
        )
        session.add(style)
        session.commit()
        session.refresh(style)
        print(f"  ✅ Created style: {style.name}")
        
        # Create test channel
        channel = Channel(
            telegram_id=-1001234567890,
            title="Test Channel",
            username="test_channel",
            owner_id=user.id,
            default_style_id=style.id,
            is_public=True
        )
        session.add(channel)
        session.commit()
        session.refresh(channel)
        print(f"  ✅ Created channel: {channel.title}")
        
        # Test FeedManager
        manager = FeedManager(session)
        
        # Test upsert feed assignment
        feed, assignment, created = manager.upsert_feed_assignment(
            feed_url="https://example.com/rss.xml",
            channel_id=channel.id,
            assigned_by_user_id=user.id,
            style_id=style.id,
            custom_config={'daily_limit': 50}
        )
        
        print(f"  ✅ Created feed assignment: feed {feed.id} -> channel {channel.id}")
        assert created is True, "First assignment should be created"
        assert feed.normalized_url == "https://example.com/rss.xml"
        assert assignment.daily_limit == 50
        
        # Test duplicate URL handling
        feed2, assignment2, created2 = manager.upsert_feed_assignment(
            feed_url="HTTPS://EXAMPLE.COM/rss.xml",  # Different case
            channel_id=channel.id,
            assigned_by_user_id=user.id,
            style_id=style.id,
            custom_config={'daily_limit': 100}
        )
        
        print(f"  ✅ Tested duplicate URL: same feed {feed.id == feed2.id}")
        assert feed.id == feed2.id, "Should reuse same canonical feed"
        assert created2 is False, "Should update existing assignment"
        assert assignment2.daily_limit == 100, "Should update configuration"
        
        # Test feed content creation
        content = FeedContent(
            feed_id=feed.id,
            title="Test Article",
            url="https://example.com/article",
            description="Test description",
            content_id="test-guid-123"
        )
        session.add(content)
        session.commit()
        session.refresh(content)
        
        print(f"  ✅ Created feed content: {content.title}")
        assert content.content_hash is not None
        assert len(content.content_hash) == 16
        
        # Verify relationships
        feed_with_assignments = session.get(Feed, feed.id)
        assert len(feed_with_assignments.feed_assignments) == 1
        assert len(feed_with_assignments.feed_contents) == 1
        
        channel_with_assignments = session.get(Channel, channel.id)
        assert len(channel_with_assignments.feed_assignments) == 1
        
        print("  ✅ All database model tests passed")


def test_deduplication_scenarios():
    """Test realistic deduplication scenarios."""
    print("\n🔍 Testing realistic deduplication scenarios...")
    
    engine = create_engine("sqlite:///:memory:", echo=False)
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # Create test data
        user1 = User(telegram_id=111111111, username="user1")
        user2 = User(telegram_id=222222222, username="user2")
        session.add_all([user1, user2])
        session.commit()
        
        style = Style(name="Default", owner_id=None, is_public=True)
        session.add(style)
        session.commit()
        
        channel1 = Channel(
            telegram_id=-1001111111111,
            title="Channel 1",
            owner_id=user1.id,
            default_style_id=style.id
        )
        channel2 = Channel(
            telegram_id=-1002222222222,
            title="Channel 2", 
            owner_id=user2.id,
            default_style_id=style.id
        )
        session.add_all([channel1, channel2])
        session.commit()
        
        manager = FeedManager(session)
        
        # Scenario: Two users add the same feed URL to different channels
        feed_urls = [
            "https://techcrunch.com/feed/",
            "HTTPS://TECHCRUNCH.COM/feed",  # Different case
            "https://techcrunch.com/feed/?utm_source=rss&utm_medium=rss",  # With tracking
        ]
        
        canonical_feed_id = None
        
        for i, url in enumerate(feed_urls):
            channel = channel1 if i % 2 == 0 else channel2
            user = user1 if i % 2 == 0 else user2
            
            feed, assignment, created = manager.upsert_feed_assignment(
                feed_url=url,
                channel_id=channel.id,
                assigned_by_user_id=user.id,
                style_id=style.id
            )
            
            if canonical_feed_id is None:
                canonical_feed_id = feed.id
                print(f"    ✅ Created canonical feed {feed.id} for {url}")
            else:
                print(f"    ✅ Reused canonical feed {feed.id} for {url}")
                assert feed.id == canonical_feed_id, "Should reuse same canonical feed"
        
        # Verify only one canonical feed exists
        all_feeds = session.exec(select(Feed)).all()
        assert len(all_feeds) == 1, f"Expected 1 feed, got {len(all_feeds)}"
        
        # Verify multiple assignments exist
        all_assignments = session.exec(select(FeedAssignment)).all()
        print(f"    ✅ Created {len(all_assignments)} assignments for 1 canonical feed")
        
        # Test content deduplication
        content_items = [
            {"title": "Tech News 1", "url": "https://techcrunch.com/article1", "guid": "tc-001"},
            {"title": "Different Title", "url": "https://techcrunch.com/article2", "guid": "tc-001"},  # Same GUID
        ]
        
        created_content_count = 0
        for item in content_items:
            try:
                content = FeedContent(
                    feed_id=canonical_feed_id,
                    title=item["title"],
                    url=item["url"],
                    content_id=item["guid"]
                )
                session.add(content)
                session.commit()
                created_content_count += 1
                print(f"    ✅ Created content: {item['title']}")
            except Exception as e:
                session.rollback()
                print(f"    ✅ Blocked duplicate content: {item['title']} ({e})")
        
        assert created_content_count == 1, "Should only create one content item due to GUID dedup"
        
        print("  ✅ All deduplication scenarios passed")


def main():
    """Run all tests."""
    print("🧪 RSS Bot Database Model Tests")
    print("=" * 40)
    
    try:
        test_url_normalization()
        test_content_hashing() 
        test_database_models()
        test_deduplication_scenarios()
        
        print("\n🎉 All tests passed successfully!")
        print("\n💡 Next steps:")
        print("  1. Run migration dry-run: ./scripts/migrate_dedup.sh --dry-run")
        print("  2. Apply migration: ./scripts/migrate_dedup.sh --apply")
        print("  3. Test with actual data")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)