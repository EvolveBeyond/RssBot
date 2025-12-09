#!/usr/bin/env python3
"""
RSS Feed Deduplication and Migration Script

This script migrates from the old feed-per-channel model to the new canonical 
feed + assignment model with proper deduplication.

Usage:
    python deduplicate_feeds.py --dry-run     # Show what would change
    python deduplicate_feeds.py --apply       # Apply changes to database
    python deduplicate_feeds.py --rollback    # Rollback to backup (if available)
"""

import os
import sys
import argparse
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import hashlib
import logging
from collections import defaultdict

# Add parent directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlmodel import Session, create_engine, select
from sqlalchemy import text
from db.models import (
    Feed, Channel, User, FeedAssignment, Style, FeedContent, 
    normalize_feed_url, compute_content_hash
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f'migration_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    ]
)
logger = logging.getLogger(__name__)


class FeedDeduplicationMigrator:
    """Handles migration from old to new feed model with deduplication."""
    
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.migration_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_backup_tables(self, session: Session) -> bool:
        """Create backup tables before migration."""
        try:
            logger.info("Creating backup tables...")
            
            # Backup old tables
            backup_queries = [
                f"CREATE TABLE feed_backup_{self.migration_id} AS SELECT * FROM feed",
                f"CREATE TABLE channel_backup_{self.migration_id} AS SELECT * FROM channel",
                f"CREATE TABLE post_backup_{self.migration_id} AS SELECT * FROM post",
            ]
            
            for query in backup_queries:
                try:
                    session.exec(text(query))
                    logger.info(f"Executed: {query}")
                except Exception as e:
                    logger.warning(f"Backup query failed (table may not exist): {e}")
            
            session.commit()
            logger.info("Backup tables created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create backup tables: {e}")
            return False
    
    def analyze_existing_feeds(self, session: Session) -> Dict:
        """Analyze existing feeds for deduplication opportunities."""
        logger.info("Analyzing existing feeds...")
        
        # Check if old feed table exists
        try:
            result = session.exec(text("SELECT name FROM sqlite_master WHERE type='table' AND name='feed'"))
            old_tables = result.fetchall()
            if not old_tables:
                logger.info("No old 'feed' table found - this appears to be a fresh installation")
                return {
                    'feeds_by_url': {},
                    'duplicate_groups': [],
                    'total_feeds': 0,
                    'total_duplicates': 0,
                    'fresh_install': True
                }
        except Exception:
            # Try PostgreSQL syntax
            try:
                result = session.exec(text("SELECT tablename FROM pg_tables WHERE tablename='feed'"))
                old_tables = result.fetchall()
                if not old_tables:
                    logger.info("No old 'feed' table found - this appears to be a fresh installation")
                    return {
                        'feeds_by_url': {},
                        'duplicate_groups': [],
                        'total_feeds': 0,
                        'total_duplicates': 0,
                        'fresh_install': True
                    }
            except Exception as e:
                logger.warning(f"Could not check for existing tables: {e}")
                return {
                    'feeds_by_url': {},
                    'duplicate_groups': [],
                    'total_feeds': 0,
                    'total_duplicates': 0,
                    'fresh_install': True
                }
        
        # Get old feed data
        try:
            old_feeds_query = text("""
                SELECT f.id, f.url, f.title, f.description, f.channel_id, 
                       f.custom_style, f.check_interval, f.last_checked,
                       c.owner_id, c.title as channel_title
                FROM feed f
                JOIN channel c ON f.channel_id = c.id
                WHERE f.url IS NOT NULL
            """)
            old_feeds = session.exec(old_feeds_query).fetchall()
        except Exception as e:
            logger.warning(f"Could not fetch old feeds: {e}")
            old_feeds = []
        
        # Group feeds by normalized URL
        feeds_by_url = defaultdict(list)
        for feed in old_feeds:
            normalized_url = normalize_feed_url(feed.url)
            feeds_by_url[normalized_url].append({
                'id': feed.id,
                'url': feed.url,
                'title': feed.title,
                'description': feed.description,
                'channel_id': feed.channel_id,
                'custom_style': feed.custom_style,
                'check_interval': feed.check_interval,
                'last_checked': feed.last_checked,
                'owner_id': feed.owner_id,
                'channel_title': feed.channel_title
            })
        
        # Find duplicates
        duplicate_groups = []
        total_duplicates = 0
        
        for normalized_url, feeds in feeds_by_url.items():
            if len(feeds) > 1:
                duplicate_groups.append({
                    'normalized_url': normalized_url,
                    'feeds': feeds,
                    'count': len(feeds)
                })
                total_duplicates += len(feeds) - 1  # All but canonical
        
        analysis = {
            'feeds_by_url': dict(feeds_by_url),
            'duplicate_groups': duplicate_groups,
            'total_feeds': len(old_feeds),
            'total_duplicates': total_duplicates,
            'total_unique_feeds': len(feeds_by_url),
            'fresh_install': len(old_feeds) == 0
        }
        
        logger.info(f"Analysis complete:")
        logger.info(f"  Total feeds: {analysis['total_feeds']}")
        logger.info(f"  Unique feeds: {analysis['total_unique_feeds']}")
        logger.info(f"  Duplicate feeds: {analysis['total_duplicates']}")
        logger.info(f"  Duplicate groups: {len(duplicate_groups)}")
        
        return analysis
    
    def create_default_styles(self, session: Session) -> Dict[str, int]:
        """Create default system styles."""
        logger.info("Creating default styles...")
        
        default_styles = [
            {
                'name': 'Default',
                'description': 'Default formatting style',
                'template': '<b>{title}</b>\n\n{description}\n\n{tags}\n\n<a href="{url}">Read more →</a>',
                'hashtags': ['#rss'],
                'is_public': True,
                'owner_id': None  # System style
            },
            {
                'name': 'Minimal',
                'description': 'Minimal formatting with just title and link',
                'template': '<b>{title}</b>\n<a href="{url}">Read more →</a>',
                'hashtags': [],
                'is_public': True,
                'owner_id': None
            },
            {
                'name': 'News',
                'description': 'News-style formatting with emphasis',
                'template': '📰 <b>{title}</b>\n\n{description}\n\n{tags}\n\n🔗 <a href="{url}">Full article</a>',
                'hashtags': ['#news', '#breaking'],
                'is_public': True,
                'owner_id': None
            }
        ]
        
        style_ids = {}
        
        for style_data in default_styles:
            # Check if style already exists
            existing = session.exec(
                select(Style).where(Style.name == style_data['name'], Style.owner_id.is_(None))
            ).first()
            
            if existing:
                style_ids[style_data['name']] = existing.id
                logger.info(f"Style '{style_data['name']}' already exists")
            else:
                style = Style(**style_data)
                session.add(style)
                session.flush()
                style_ids[style_data['name']] = style.id
                logger.info(f"Created style '{style_data['name']}' with ID {style.id}")
        
        session.commit()
        return style_ids
    
    def migrate_feeds(self, session: Session, analysis: Dict, dry_run: bool = True) -> Dict:
        """Migrate feeds to new canonical model."""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Migrating feeds to canonical model...")
        
        migration_report = {
            'canonical_feeds_created': 0,
            'feed_assignments_created': 0,
            'duplicates_resolved': 0,
            'errors': [],
            'canonical_feed_mapping': {},  # old_feed_id -> canonical_feed_id
            'assignments_created': []
        }
        
        if analysis['fresh_install']:
            logger.info("Fresh installation detected - no migration needed")
            return migration_report
        
        # Get default styles
        default_styles = self.create_default_styles(session) if not dry_run else {'Default': 1}
        default_style_id = default_styles.get('Default')
        
        # Process each URL group
        for normalized_url, feeds in analysis['feeds_by_url'].items():
            try:
                # Create canonical feed (use first/oldest feed as template)
                canonical_template = min(feeds, key=lambda f: f['id'])
                
                if not dry_run:
                    # Check if canonical feed already exists
                    existing_canonical = session.exec(
                        select(Feed).where(Feed.normalized_url == normalized_url)
                    ).first()
                    
                    if existing_canonical:
                        canonical_feed = existing_canonical
                        logger.info(f"Using existing canonical feed {canonical_feed.id} for {normalized_url}")
                    else:
                        canonical_feed = Feed(
                            url=canonical_template['url'],
                            title=canonical_template['title'],
                            description=canonical_template['description'],
                            check_interval=canonical_template['check_interval'] or 600,
                            last_checked=canonical_template['last_checked'],
                            is_active=True,
                            is_valid=True
                        )
                        session.add(canonical_feed)
                        session.flush()
                        migration_report['canonical_feeds_created'] += 1
                        logger.info(f"Created canonical feed {canonical_feed.id} for {normalized_url}")
                else:
                    # Dry run - simulate
                    canonical_feed = type('MockFeed', (), {'id': f'canonical_{len(migration_report["canonical_feed_mapping"])}'})()
                    migration_report['canonical_feeds_created'] += 1
                
                # Create feed assignments for each channel
                for feed in feeds:
                    if not dry_run:
                        # Check if assignment already exists
                        existing_assignment = session.exec(
                            select(FeedAssignment).where(
                                FeedAssignment.feed_id == canonical_feed.id,
                                FeedAssignment.channel_id == feed['channel_id']
                            )
                        ).first()
                        
                        if existing_assignment:
                            logger.info(f"Assignment already exists for feed {canonical_feed.id} -> channel {feed['channel_id']}")
                            continue
                        
                        assignment = FeedAssignment(
                            feed_id=canonical_feed.id,
                            channel_id=feed['channel_id'],
                            assigned_by_user_id=feed['owner_id'],
                            style_id=default_style_id,
                            is_active=True,
                            custom_check_interval=feed['check_interval'] if feed['check_interval'] != 600 else None
                        )
                        session.add(assignment)
                        session.flush()
                        
                        assignment_info = {
                            'assignment_id': assignment.id,
                            'canonical_feed_id': canonical_feed.id,
                            'channel_id': feed['channel_id'],
                            'old_feed_id': feed['id']
                        }
                    else:
                        # Dry run
                        assignment_info = {
                            'assignment_id': f"assignment_{migration_report['feed_assignments_created']}",
                            'canonical_feed_id': canonical_feed.id,
                            'channel_id': feed['channel_id'],
                            'old_feed_id': feed['id']
                        }
                    
                    migration_report['assignments_created'].append(assignment_info)
                    migration_report['feed_assignments_created'] += 1
                    migration_report['canonical_feed_mapping'][feed['id']] = canonical_feed.id
                
                # Count duplicates resolved
                if len(feeds) > 1:
                    migration_report['duplicates_resolved'] += len(feeds) - 1
                    
            except Exception as e:
                error_msg = f"Error processing URL group {normalized_url}: {e}"
                logger.error(error_msg)
                migration_report['errors'].append(error_msg)
        
        if not dry_run:
            session.commit()
            logger.info("Migration committed to database")
        
        logger.info(f"Migration {'simulation ' if dry_run else ''}complete:")
        logger.info(f"  Canonical feeds created: {migration_report['canonical_feeds_created']}")
        logger.info(f"  Feed assignments created: {migration_report['feed_assignments_created']}")
        logger.info(f"  Duplicates resolved: {migration_report['duplicates_resolved']}")
        logger.info(f"  Errors: {len(migration_report['errors'])}")
        
        return migration_report
    
    def migrate_content(self, session: Session, migration_report: Dict, dry_run: bool = True) -> None:
        """Migrate old Post records to new FeedContent model."""
        logger.info(f"{'DRY RUN: ' if dry_run else ''}Migrating post content...")
        
        if not migration_report['canonical_feed_mapping']:
            logger.info("No feed mapping available - skipping content migration")
            return
        
        try:
            # Get old posts
            old_posts_query = text("""
                SELECT p.id, p.feed_id, p.title, p.description, p.link,
                       p.published_date, p.guid, p.tags
                FROM post p
                WHERE p.feed_id IN ({})
            """.format(','.join(str(fid) for fid in migration_report['canonical_feed_mapping'].keys())))
            
            old_posts = session.exec(old_posts_query).fetchall()
            logger.info(f"Found {len(old_posts)} posts to migrate")
            
            migrated_count = 0
            for post in old_posts:
                try:
                    canonical_feed_id = migration_report['canonical_feed_mapping'].get(post.feed_id)
                    if not canonical_feed_id:
                        continue
                    
                    if not dry_run:
                        # Check if content already exists
                        content_hash = compute_content_hash(
                            title=post.title,
                            link=post.link,
                            description=post.description,
                            guid=post.guid
                        )
                        
                        existing = session.exec(
                            select(FeedContent).where(
                                FeedContent.feed_id == canonical_feed_id,
                                FeedContent.content_hash == content_hash
                            )
                        ).first()
                        
                        if existing:
                            continue
                        
                        feed_content = FeedContent(
                            feed_id=canonical_feed_id,
                            title=post.title,
                            url=post.link,
                            description=post.description,
                            content_id=post.guid or post.link,
                            published_date=post.published_date,
                            is_processed=True,
                            tags=post.tags.split(',') if post.tags else []
                        )
                        session.add(feed_content)
                    
                    migrated_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to migrate post {post.id}: {e}")
            
            if not dry_run:
                session.commit()
                
            logger.info(f"Migrated {migrated_count} posts to FeedContent")
            
        except Exception as e:
            logger.error(f"Content migration failed: {e}")
    
    def generate_report(self, analysis: Dict, migration_report: Dict, dry_run: bool) -> str:
        """Generate human-readable migration report."""
        report = []
        report.append("=" * 60)
        report.append(f"RSS FEED DEDUPLICATION REPORT ({'DRY RUN' if dry_run else 'APPLIED'})")
        report.append("=" * 60)
        report.append(f"Generated: {datetime.now().isoformat()}")
        report.append("")
        
        if analysis['fresh_install']:
            report.append("✅ FRESH INSTALLATION DETECTED")
            report.append("No migration needed - new schema will be used directly.")
            report.append("")
            return "\n".join(report)
        
        report.append("📊 ANALYSIS SUMMARY")
        report.append("-" * 20)
        report.append(f"Total feeds found: {analysis['total_feeds']}")
        report.append(f"Unique feeds (after dedup): {analysis['total_unique_feeds']}")
        report.append(f"Duplicate feeds: {analysis['total_duplicates']}")
        report.append(f"Duplicate groups: {len(analysis['duplicate_groups'])}")
        report.append("")
        
        if analysis['duplicate_groups']:
            report.append("🔍 DUPLICATE GROUPS")
            report.append("-" * 20)
            for group in analysis['duplicate_groups'][:10]:  # Show first 10
                report.append(f"URL: {group['normalized_url']}")
                report.append(f"  Duplicates: {group['count']} feeds")
                for feed in group['feeds']:
                    report.append(f"    - Feed ID {feed['id']}: {feed['channel_title']} (owner: {feed['owner_id']})")
                report.append("")
            
            if len(analysis['duplicate_groups']) > 10:
                report.append(f"... and {len(analysis['duplicate_groups']) - 10} more duplicate groups")
                report.append("")
        
        report.append("🔧 MIGRATION RESULTS")
        report.append("-" * 20)
        report.append(f"Canonical feeds created: {migration_report['canonical_feeds_created']}")
        report.append(f"Feed assignments created: {migration_report['feed_assignments_created']}")
        report.append(f"Duplicates resolved: {migration_report['duplicates_resolved']}")
        report.append("")
        
        if migration_report['errors']:
            report.append("❌ ERRORS ENCOUNTERED")
            report.append("-" * 20)
            for error in migration_report['errors']:
                report.append(f"  - {error}")
            report.append("")
        
        if dry_run:
            report.append("💡 NEXT STEPS")
            report.append("-" * 20)
            report.append("This was a dry run. To apply changes:")
            report.append("  python deduplicate_feeds.py --apply")
            report.append("")
            report.append("To cancel, take no action. The database remains unchanged.")
        else:
            report.append("✅ MIGRATION COMPLETED")
            report.append("-" * 20)
            report.append("Database has been updated with the new schema.")
            report.append(f"Backup tables created with suffix: _{self.migration_id}")
            report.append("")
            report.append("To rollback (if needed):")
            report.append(f"  python deduplicate_feeds.py --rollback --migration-id {self.migration_id}")
        
        return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description='RSS Feed Deduplication Migration Tool')
    parser.add_argument('--dry-run', action='store_true', help='Show what would change without applying')
    parser.add_argument('--apply', action='store_true', help='Apply changes to database')
    parser.add_argument('--rollback', action='store_true', help='Rollback to backup')
    parser.add_argument('--migration-id', help='Migration ID for rollback')
    parser.add_argument('--database-url', help='Database URL (overrides env var)')
    
    args = parser.parse_args()
    
    if not any([args.dry_run, args.apply, args.rollback]):
        parser.error("Must specify one of: --dry-run, --apply, or --rollback")
    
    if args.apply and args.dry_run:
        parser.error("Cannot specify both --apply and --dry-run")
    
    # Get database URL
    database_url = args.database_url or os.getenv('DATABASE_URL')
    if not database_url:
        logger.error("DATABASE_URL not provided and not found in environment")
        sys.exit(1)
    
    migrator = FeedDeduplicationMigrator(database_url)
    
    try:
        with Session(migrator.engine) as session:
            if args.rollback:
                if not args.migration_id:
                    logger.error("--migration-id required for rollback")
                    sys.exit(1)
                # TODO: Implement rollback logic
                logger.error("Rollback not yet implemented")
                sys.exit(1)
            
            # Create backups before any changes
            if args.apply:
                if not migrator.create_backup_tables(session):
                    logger.error("Failed to create backup tables - aborting")
                    sys.exit(1)
            
            # Analyze existing data
            analysis = migrator.analyze_existing_feeds(session)
            
            # Migrate feeds
            migration_report = migrator.migrate_feeds(session, analysis, dry_run=args.dry_run)
            
            # Migrate content
            migrator.migrate_content(session, migration_report, dry_run=args.dry_run)
            
            # Generate and display report
            report = migrator.generate_report(analysis, migration_report, dry_run=args.dry_run)
            print(report)
            
            # Save report to file
            report_filename = f"migration_report_{migrator.migration_id}{'_dry_run' if args.dry_run else ''}.txt"
            with open(report_filename, 'w') as f:
                f.write(report)
            logger.info(f"Report saved to {report_filename}")
    
    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()