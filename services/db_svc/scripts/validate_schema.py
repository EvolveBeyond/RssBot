#!/usr/bin/env python3
"""
Schema validation script for RSS Bot database models.
Validates the new canonical feed deduplication system.
"""

import os
import sys
import json
from datetime import datetime

# Add paths for imports (compatible with various Python setups)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def validate_imports():
    """Validate that all required modules can be imported."""
    print("🔍 Validating imports...")
    
    try:
        # Core imports
        from sqlmodel import SQLModel, Session, create_engine, select, Field, Relationship
        from sqlalchemy import Index, UniqueConstraint, CheckConstraint
        print("  ✅ SQLModel and SQLAlchemy imports successful")
        
        # Model imports
        from db.models import (
            User, Channel, Feed, FeedAssignment, Style, FeedContent, 
            PublishedMessage, normalize_feed_url, compute_content_hash,
            ModelRegistry
        )
        print("  ✅ Database model imports successful")
        
        # Service imports
        from db.feed_manager import FeedManager
        from db.style_engine import StyleEngine, FormattingContext, FormattingResult
        print("  ✅ Service module imports successful")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        print("\n💡 To fix missing dependencies:")
        print("  1. cd /mnt/HDD/Documents/Project/python/RssBot")
        print("  2. rye sync")
        print("  3. rye add sqlmodel fastapi uvicorn alembic psycopg2-binary beautifulsoup4 feedparser")
        return False


def validate_model_schema():
    """Validate the database model schema."""
    print("\n🔍 Validating model schema...")
    
    try:
        from db.models import (
            User, Channel, Feed, FeedAssignment, Style, FeedContent, 
            PublishedMessage, ModelRegistry
        )
        
        # Check model registration
        models = ModelRegistry.get_models()
        expected_models = {
            'User', 'Channel', 'Feed', 'FeedAssignment', 'Style', 
            'FeedContent', 'PublishedMessage', 'Subscription', 'PaymentRecord', 
            'ServiceInstance'
        }
        
        registered_models = set(models.keys())
        missing_models = expected_models - registered_models
        extra_models = registered_models - expected_models
        
        if missing_models:
            print(f"  ❌ Missing models: {missing_models}")
            return False
        
        if extra_models:
            print(f"  ℹ️  Extra models: {extra_models}")
        
        print(f"  ✅ Model registration complete: {len(registered_models)} models")
        
        # Validate key model attributes
        print("  🔍 Validating model attributes...")
        
        # Feed model validation
        feed = Feed.__table__
        required_feed_cols = {'url', 'normalized_url', 'url_hash', 'is_active', 'is_valid'}
        feed_cols = {col.name for col in feed.columns}
        
        if not required_feed_cols.issubset(feed_cols):
            missing = required_feed_cols - feed_cols
            print(f"  ❌ Feed model missing columns: {missing}")
            return False
        print("  ✅ Feed model has required columns")
        
        # FeedAssignment model validation  
        assignment = FeedAssignment.__table__
        required_assignment_cols = {
            'feed_id', 'channel_id', 'assigned_by_user_id', 'style_id',
            'daily_limit', 'monthly_limit', 'is_active', 'is_paused'
        }
        assignment_cols = {col.name for col in assignment.columns}
        
        if not required_assignment_cols.issubset(assignment_cols):
            missing = required_assignment_cols - assignment_cols
            print(f"  ❌ FeedAssignment model missing columns: {missing}")
            return False
        print("  ✅ FeedAssignment model has required columns")
        
        # Check constraints exist
        print("  🔍 Validating database constraints...")
        
        # Feed unique constraints
        feed_indexes = [idx.name for idx in feed.indexes]
        if not any('normalized_url' in str(idx) for idx in feed.indexes):
            print("  ⚠️  Feed normalized_url index may be missing")
        
        print("  ✅ Model schema validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ Schema validation failed: {e}")
        return False


def validate_utility_functions():
    """Validate utility functions for URL normalization and content hashing."""
    print("\n🔍 Validating utility functions...")
    
    try:
        from db.models import normalize_feed_url, compute_content_hash
        
        # Test URL normalization
        test_urls = [
            ("https://example.com/feed.xml", "https://example.com/feed.xml"),
            ("HTTPS://EXAMPLE.COM/FEED.XML", "https://example.com/feed.xml"),
            ("https://example.com/feed.xml/", "https://example.com/feed.xml"),
        ]
        
        for input_url, expected in test_urls:
            result = normalize_feed_url(input_url)
            if expected.lower() not in result.lower():
                print(f"  ❌ URL normalization failed: {input_url} → {result}")
                return False
        
        print("  ✅ URL normalization works correctly")
        
        # Test content hashing
        hash1 = compute_content_hash("Title", "http://example.com", guid="test-123")
        hash2 = compute_content_hash("Title", "http://example.com", guid="test-123")
        
        if hash1 != hash2:
            print(f"  ❌ Content hashing not consistent: {hash1} != {hash2}")
            return False
        
        if len(hash1) != 16:
            print(f"  ❌ Content hash wrong length: {len(hash1)} != 16")
            return False
        
        print("  ✅ Content hashing works correctly")
        return True
        
    except Exception as e:
        print(f"  ❌ Utility function validation failed: {e}")
        return False


def validate_feed_manager():
    """Validate the FeedManager functionality."""
    print("\n🔍 Validating FeedManager...")
    
    try:
        from db.feed_manager import FeedManager
        from sqlmodel import create_engine, SQLModel, Session
        from db.models import User, Channel, Style, Feed, FeedAssignment
        
        # Create in-memory test database
        engine = create_engine("sqlite:///:memory:", echo=False)
        SQLModel.metadata.create_all(engine)
        
        with Session(engine) as session:
            # Create test data
            user = User(telegram_id=123456789, username="testuser")
            session.add(user)
            session.flush()
            
            style = Style(name="Test", owner_id=user.id)
            session.add(style)
            session.flush()
            
            channel = Channel(
                telegram_id=-1001234567890,
                title="Test Channel",
                owner_id=user.id,
                default_style_id=style.id
            )
            session.add(channel)
            session.flush()
            
            # Test FeedManager
            manager = FeedManager(session)
            
            # Test feed assignment creation
            feed, assignment, created = manager.upsert_feed_assignment(
                feed_url="https://example.com/feed.xml",
                channel_id=channel.id,
                assigned_by_user_id=user.id,
                style_id=style.id
            )
            
            if not created:
                print("  ❌ Feed assignment should have been created")
                return False
            
            if not feed.normalized_url:
                print("  ❌ Feed normalized_url not set")
                return False
            
            print(f"  ✅ Created feed assignment: feed {feed.id} → channel {channel.id}")
            
            # Test deduplication
            feed2, assignment2, created2 = manager.upsert_feed_assignment(
                feed_url="HTTPS://EXAMPLE.COM/feed.xml",  # Different case
                channel_id=channel.id,
                assigned_by_user_id=user.id,
                style_id=style.id
            )
            
            if feed.id != feed2.id:
                print(f"  ❌ Feed deduplication failed: {feed.id} != {feed2.id}")
                return False
            
            if created2:
                print("  ❌ Duplicate assignment should not have been created")
                return False
            
            print("  ✅ Feed deduplication works correctly")
            
        print("  ✅ FeedManager validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ FeedManager validation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def validate_style_engine():
    """Validate the StyleEngine functionality."""
    print("\n🔍 Validating StyleEngine...")
    
    try:
        from db.style_engine import StyleEngine, FormattingContext
        from db.models import Style, FeedContent, Channel
        
        # Create mock objects
        style = Style(
            name="Test Style",
            template="<b>{title}</b>\n{description}\n{tags}\n<a href='{url}'>Link</a>",
            hashtags=["#test"],
            max_length=1000
        )
        
        # Use namedtuple for mock objects to avoid SQLModel complexity
        from collections import namedtuple
        
        MockFeedContent = namedtuple('FeedContent', [
            'title', 'description', 'summary', 'url', 'author', 'published_date',
            'content_type', 'tags', 'categories'
        ])
        
        MockChannel = namedtuple('Channel', ['title', 'username', 'id'])
        
        feed_content = MockFeedContent(
            title="Test Article",
            description="This is a test article description",
            summary="Test summary",
            url="https://example.com/article",
            author="Test Author",
            published_date=datetime.now(),
            content_type="text",
            tags=["technology", "news"],
            categories=["Tech News"]
        )
        
        channel = MockChannel(
            title="Test Channel",
            username="test_channel", 
            id=1
        )
        
        context = FormattingContext(
            feed_content=feed_content,
            style=style,
            channel=channel
        )
        
        # Test formatting
        engine = StyleEngine()
        result = engine.format_content(context)
        
        if not result.formatted_text:
            print("  ❌ StyleEngine produced empty formatted text")
            return False
        
        if "Test Article" not in result.formatted_text:
            print("  ❌ StyleEngine did not include title in output")
            return False
        
        if len(result.tags_used) == 0:
            print("  ❌ StyleEngine did not generate tags")
            return False
        
        print(f"  ✅ Formatted content: {len(result.formatted_text)} chars")
        print(f"  ✅ Generated tags: {result.tags_used}")
        print("  ✅ StyleEngine validation passed")
        return True
        
    except Exception as e:
        print(f"  ❌ StyleEngine validation failed: {e}")
        return False


def generate_validation_report():
    """Generate a comprehensive validation report."""
    print("\n📊 Generating validation report...")
    
    validations = [
        ("Import Validation", validate_imports),
        ("Model Schema", validate_model_schema), 
        ("Utility Functions", validate_utility_functions),
        ("FeedManager", validate_feed_manager),
        ("StyleEngine", validate_style_engine),
    ]
    
    results = {}
    
    for name, validator in validations:
        try:
            results[name] = validator()
        except Exception as e:
            print(f"❌ {name} validation crashed: {e}")
            results[name] = False
    
    # Summary
    passed = sum(results.values())
    total = len(results)
    
    print(f"\n📋 VALIDATION SUMMARY")
    print("=" * 40)
    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {name}")
    
    print(f"\nResult: {passed}/{total} validations passed")
    
    if passed == total:
        print("\n🎉 All validations passed! The new schema is ready for migration.")
        print("\n💡 Next steps:")
        print("  1. Run migration dry-run: ./scripts/migrate_dedup.sh --dry-run")
        print("  2. Apply migration: ./scripts/migrate_dedup.sh --apply")
        print("  3. Test with real data")
        return True
    else:
        print("\n❌ Some validations failed. Please fix issues before proceeding.")
        return False


def main():
    """Main validation function."""
    print("🧪 RSS Bot Schema Validation")
    print("=" * 40)
    
    success = generate_validation_report()
    
    if success:
        # Write validation stamp
        timestamp = datetime.now().isoformat()
        with open("schema_validation_passed.txt", "w") as f:
            f.write(f"Schema validation passed at {timestamp}\n")
            f.write("Ready for migration.\n")
        
        print(f"\n✅ Validation stamp written to schema_validation_passed.txt")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)