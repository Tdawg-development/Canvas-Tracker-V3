#!/usr/bin/env python3
"""
Remove Course Statistics Fields Migration

This migration removes the following unnecessary fields from the canvas_courses table:
- total_students
- total_modules  
- total_assignments
- published_assignments
- total_points

These statistical values can be calculated dynamically from relationships
and no longer need to be stored in the database.
"""

import logging
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from database.session import DatabaseManager

logger = logging.getLogger(__name__)

def migrate_remove_course_statistics():
    """Remove statistical fields from canvas_courses table."""
    
    print("🗃️ Course Statistics Fields Removal Migration")
    print("=" * 55)
    
    # Set test environment if we're in the test-environment directory
    if 'test-environment' in os.getcwd():
        os.environ['DATABASE_ENV'] = 'test'
        print("📝 Using test database environment")
    
    db_manager = DatabaseManager()
    engine = db_manager.engine
    
    # Fields to remove
    fields_to_remove = [
        'total_students',
        'total_modules', 
        'total_assignments',
        'published_assignments',
        'total_points'
    ]
    
    try:
        with engine.begin() as conn:
            
            # Check if table exists
            table_check = conn.execute(text("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='canvas_courses'
            """)).fetchone()
            
            if not table_check:
                print("❌ canvas_courses table does not exist - skipping migration")
                return True
            
            # For SQLite, we need to check which columns exist
            # Get current table schema
            columns_result = conn.execute(text("PRAGMA table_info(canvas_courses)")).fetchall()
            existing_columns = [row[1] for row in columns_result]  # row[1] is column name
            
            print(f"📋 Current columns in canvas_courses: {len(existing_columns)} columns")
            
            # Check which statistical fields exist
            fields_to_drop = [field for field in fields_to_remove if field in existing_columns]
            fields_missing = [field for field in fields_to_remove if field not in existing_columns]
            
            if fields_missing:
                print(f"ℹ️ Fields already removed: {fields_missing}")
            
            if not fields_to_drop:
                print("✅ All statistical fields already removed - migration complete")
                return True
            
            print(f"🔄 Removing fields: {fields_to_drop}")
            
            # For SQLite, we need to recreate the table without these columns
            # Step 1: Create new table without the statistical fields
            print("📝 Creating new canvas_courses table without statistical fields...")
            
            create_new_table_sql = """
                CREATE TABLE canvas_courses_new (
                    id INTEGER PRIMARY KEY,
                    name VARCHAR(255),
                    course_code VARCHAR(100),
                    calendar_ics TEXT,
                    created_at DATETIME,
                    updated_at DATETIME,
                    last_synced DATETIME
                );
            """
            conn.execute(text(create_new_table_sql))
            
            # Step 2: Copy data from old table to new table
            print("📋 Copying existing data to new table...")
            copy_data_sql = """
                INSERT INTO canvas_courses_new (
                    id, name, course_code, calendar_ics, created_at, updated_at, last_synced
                )
                SELECT 
                    id, name, course_code, calendar_ics, created_at, updated_at, last_synced
                FROM canvas_courses;
            """
            result = conn.execute(text(copy_data_sql))
            rows_copied = result.rowcount
            print(f"✅ Copied {rows_copied} course records")
            
            # Step 3: Drop old table
            print("🗑️ Dropping old canvas_courses table...")
            conn.execute(text("DROP TABLE canvas_courses"))
            
            # Step 4: Rename new table to original name
            print("🔄 Renaming new table to canvas_courses...")
            conn.execute(text("ALTER TABLE canvas_courses_new RENAME TO canvas_courses"))
            
            # Step 5: Recreate indexes if any existed (SQLite will recreate basic indexes automatically)
            # For now, we'll let SQLAlchemy handle this when the application starts
            
            print("✅ Successfully removed statistical fields from canvas_courses table")
            print(f"   Removed: {', '.join(fields_to_drop)}")
            print(f"   Preserved {rows_copied} course records")
            
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        logger.error(f"Course statistics removal migration failed: {e}", exc_info=True)
        return False

def rollback_migration():
    """
    Rollback migration by adding the statistical fields back.
    
    Note: This will add the columns back but they will be empty.
    A full sync would be needed to repopulate them.
    """
    print("🔄 Rolling back course statistics fields removal...")
    
    db_manager = DatabaseManager()
    engine = db_manager.engine
    
    try:
        with engine.begin() as conn:
            # Add the statistical columns back with default values
            alter_commands = [
                "ALTER TABLE canvas_courses ADD COLUMN total_students REAL",
                "ALTER TABLE canvas_courses ADD COLUMN total_modules REAL", 
                "ALTER TABLE canvas_courses ADD COLUMN total_assignments REAL",
                "ALTER TABLE canvas_courses ADD COLUMN published_assignments REAL",
                "ALTER TABLE canvas_courses ADD COLUMN total_points INTEGER DEFAULT 0"
            ]
            
            for command in alter_commands:
                try:
                    conn.execute(text(command))
                except Exception as e:
                    # Column might already exist
                    if "duplicate column name" not in str(e).lower():
                        raise
            
            print("✅ Rollback completed - statistical fields restored")
            print("⚠️ Note: Fields are empty and would need a full sync to repopulate")
            
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        logger.error(f"Course statistics rollback failed: {e}", exc_info=True)
        return False
    
    return True

def main():
    """Run the migration."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Remove course statistics fields migration")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without executing")
    
    args = parser.parse_args()
    
    if args.dry_run:
        print("🔍 DRY RUN MODE - No changes will be made")
        print("Would remove fields: total_students, total_modules, total_assignments, published_assignments, total_points")
        return
    
    if args.rollback:
        success = rollback_migration()
    else:
        success = migrate_remove_course_statistics()
    
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
        exit(1)

if __name__ == "__main__":
    main()