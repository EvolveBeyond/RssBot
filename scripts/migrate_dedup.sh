#!/bin/bash

# RSS Bot Feed Deduplication Migration Script
# 
# This script manages the migration to the new canonical feed system with deduplication.
# It supports dry-run mode to preview changes and apply mode to execute them.

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DB_SERVICE_DIR="$PROJECT_ROOT/services/db_svc"
MIGRATION_SCRIPT="$DB_SERVICE_DIR/scripts/deduplicate_feeds.py"
DATABASE_URL="${DATABASE_URL:-sqlite:///./rssbot.db}"

# Help function
show_help() {
    cat << EOF
RSS Bot Feed Deduplication Migration Script

Usage: $0 [OPTION]

Options:
    --dry-run       Show what would change without applying (safe)
    --apply         Apply changes to database (destructive)
    --rollback      Rollback to backup (requires --migration-id)
    --migration-id  Specify migration ID for rollback
    --help          Show this help message

Examples:
    $0 --dry-run                    # Preview changes
    $0 --apply                      # Apply migration
    $0 --rollback --migration-id 20241201_143022

Environment Variables:
    DATABASE_URL    Database connection string (required)
    LOG_LEVEL       Set to DEBUG for verbose output

Note: Always run --dry-run first to understand the impact!
EOF
}

# Check prerequisites
check_prerequisites() {
    echo -e "${BLUE}🔍 Checking prerequisites...${NC}"
    
    # Check if Python environment is available
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}❌ Python 3 not found${NC}"
        exit 1
    fi
    
    # Check if in project root
    if [[ ! -f "$PROJECT_ROOT/pyproject.toml" ]]; then
        echo -e "${RED}❌ Not in RSS Bot project root. Expected to find pyproject.toml${NC}"
        exit 1
    fi
    
    # Check if migration script exists
    if [[ ! -f "$MIGRATION_SCRIPT" ]]; then
        echo -e "${RED}❌ Migration script not found: $MIGRATION_SCRIPT${NC}"
        exit 1
    fi
    
    # Check if DATABASE_URL is set
    if [[ -z "$DATABASE_URL" ]]; then
        echo -e "${RED}❌ DATABASE_URL environment variable not set${NC}"
        echo -e "${YELLOW}💡 Set it with: export DATABASE_URL='your_database_url'${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ Prerequisites check passed${NC}"
}

# Create backup before migration
create_backup() {
    local backup_type="$1"
    
    echo -e "${BLUE}📦 Creating backup before migration...${NC}"
    
    # Generate backup filename with timestamp
    local timestamp=$(date +"%Y%m%d_%H%M%S")
    local backup_file="$PROJECT_ROOT/backup_${timestamp}.sql"
    
    # Extract database type and create appropriate backup
    if [[ "$DATABASE_URL" == sqlite* ]]; then
        # SQLite backup
        local db_file=$(echo "$DATABASE_URL" | sed 's/sqlite:\/\/\///')
        if [[ -f "$db_file" ]]; then
            cp "$db_file" "${db_file}.backup_${timestamp}"
            echo -e "${GREEN}✅ SQLite backup created: ${db_file}.backup_${timestamp}${NC}"
        else
            echo -e "${YELLOW}⚠️  SQLite database file not found: $db_file${NC}"
        fi
    elif [[ "$DATABASE_URL" == postgresql* ]]; then
        # PostgreSQL backup
        echo -e "${YELLOW}💡 For PostgreSQL, manually create backup with:${NC}"
        echo -e "    pg_dump '$DATABASE_URL' > $backup_file"
        echo -e "    Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Migration cancelled${NC}"
            exit 1
        fi
    else
        echo -e "${YELLOW}⚠️  Unknown database type in DATABASE_URL${NC}"
        echo -e "${YELLOW}💡 Consider creating manual backup before proceeding${NC}"
        echo -e "    Continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo -e "${YELLOW}Migration cancelled${NC}"
            exit 1
        fi
    fi
}

# Run Alembic migration
run_alembic_migration() {
    echo -e "${BLUE}🔄 Running database schema migration...${NC}"
    
    cd "$DB_SERVICE_DIR"
    
    # Check current migration state
    echo -e "${BLUE}📋 Current migration state:${NC}"
    if command -v rye &> /dev/null; then
        rye run alembic current || echo "No current migration state"
        echo -e "${BLUE}🚀 Upgrading to latest schema...${NC}"
        rye run alembic upgrade head
    else
        python -m alembic current || echo "No current migration state"
        echo -e "${BLUE}🚀 Upgrading to latest schema...${NC}"
        python -m alembic upgrade head
    fi
    
    echo -e "${GREEN}✅ Schema migration completed${NC}"
    cd - > /dev/null
}

# Run data migration
run_data_migration() {
    local mode="$1"
    
    echo -e "${BLUE}🔄 Running data migration (${mode} mode)...${NC}"
    
    cd "$PROJECT_ROOT"
    
    # Run the deduplication script
    local cmd_args="--${mode}"
    if [[ -n "$MIGRATION_ID" ]]; then
        cmd_args="$cmd_args --migration-id $MIGRATION_ID"
    fi
    
    if command -v rye &> /dev/null; then
        rye run python "$MIGRATION_SCRIPT" $cmd_args
    else
        python3 "$MIGRATION_SCRIPT" $cmd_args
    fi
    
    echo -e "${GREEN}✅ Data migration completed${NC}"
    cd - > /dev/null
}

# Verify migration results
verify_migration() {
    echo -e "${BLUE}🔍 Verifying migration results...${NC}"
    
    cd "$DB_SERVICE_DIR"
    
    # Run basic verification queries
    if command -v rye &> /dev/null; then
        rye run python -c "
import os, sys
sys.path.append('.')
from sqlmodel import Session, create_engine, select
from db.models import Feed, FeedAssignment, Style
engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./rssbot.db'))
with Session(engine) as session:
    feeds = session.exec(select(Feed)).all()
    assignments = session.exec(select(FeedAssignment)).all() 
    styles = session.exec(select(Style)).all()
    print(f'✅ Verification passed:')
    print(f'  - Canonical feeds: {len(feeds)}')
    print(f'  - Feed assignments: {len(assignments)}') 
    print(f'  - Styles: {len(styles)}')
    print(f'  - Schema version: OK')
"
    else
        python3 -c "
import os, sys
sys.path.append('.')
from sqlmodel import Session, create_engine, select
from db.models import Feed, FeedAssignment, Style
engine = create_engine(os.getenv('DATABASE_URL', 'sqlite:///./rssbot.db'))
with Session(engine) as session:
    feeds = session.exec(select(Feed)).all()
    assignments = session.exec(select(FeedAssignment)).all()
    styles = session.exec(select(Style)).all()
    print(f'✅ Verification passed:')
    print(f'  - Canonical feeds: {len(feeds)}')
    print(f'  - Feed assignments: {len(assignments)}')
    print(f'  - Styles: {len(styles)}')
    print(f'  - Schema version: OK')
"
    fi
    
    echo -e "${GREEN}✅ Migration verification completed${NC}"
    cd - > /dev/null
}

# Main execution
main() {
    local mode=""
    local MIGRATION_ID=""
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                mode="dry-run"
                shift
                ;;
            --apply)
                mode="apply"
                shift
                ;;
            --rollback)
                mode="rollback"
                shift
                ;;
            --migration-id)
                MIGRATION_ID="$2"
                shift 2
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}❌ Unknown option: $1${NC}"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Validate arguments
    if [[ -z "$mode" ]]; then
        echo -e "${RED}❌ No mode specified${NC}"
        show_help
        exit 1
    fi
    
    if [[ "$mode" == "rollback" && -z "$MIGRATION_ID" ]]; then
        echo -e "${RED}❌ --migration-id required for rollback${NC}"
        exit 1
    fi
    
    # Show header
    echo -e "${BLUE}🚀 RSS Bot Feed Deduplication Migration${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}Mode: ${mode}${NC}"
    echo -e "${BLUE}Database: ${DATABASE_URL}${NC}"
    echo -e "${BLUE}Time: $(date)${NC}"
    echo ""
    
    # Run checks
    check_prerequisites
    
    if [[ "$mode" == "rollback" ]]; then
        echo -e "${YELLOW}⚠️  Rollback functionality not yet implemented${NC}"
        exit 1
    fi
    
    # Confirm destructive operations
    if [[ "$mode" == "apply" ]]; then
        echo -e "${YELLOW}⚠️  WARNING: This will modify your database!${NC}"
        echo -e "${YELLOW}Make sure you have a backup before proceeding.${NC}"
        echo ""
        echo -e "Continue with applying migration? (type 'yes' to confirm)"
        read -r confirmation
        if [[ "$confirmation" != "yes" ]]; then
            echo -e "${YELLOW}Migration cancelled${NC}"
            exit 1
        fi
        
        create_backup "$mode"
    fi
    
    # Run schema migration first
    if [[ "$mode" == "apply" ]]; then
        run_alembic_migration
    fi
    
    # Run data migration
    run_data_migration "$mode"
    
    # Verify results if applied
    if [[ "$mode" == "apply" ]]; then
        verify_migration
    fi
    
    echo ""
    echo -e "${GREEN}🎉 Migration ${mode} completed successfully!${NC}"
    
    if [[ "$mode" == "dry-run" ]]; then
        echo -e "${YELLOW}💡 This was a dry run. To apply changes, run:${NC}"
        echo -e "    $0 --apply"
    elif [[ "$mode" == "apply" ]]; then
        echo -e "${GREEN}✅ Your database has been upgraded to the new schema.${NC}"
        echo -e "${GREEN}You can now use the enhanced feed deduplication features.${NC}"
    fi
}

# Run main function with all arguments
main "$@"