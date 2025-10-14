#!/usr/bin/env python3
"""
Unified Test Database Setup Utility

This script ensures all tests use the same database configuration consistently.
It replaces the scattered database setup logic across multiple scripts.
"""

import os
import sys
from pathlib import Path

# Set test environment BEFORE any other imports
os.environ['DATABASE_ENV'] = 'test'

# Add project root to Python path (parent directory since we're in test-environment/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.session import DatabaseManager
from database.config import get_config
from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
from sqlalchemy import text


def get_test_database_path() -> Path:
    """Get the standardized test database path."""
    config = get_config()
    if not config.is_sqlite():
        raise ValueError("Test configuration should use SQLite")
    return Path(config.get_database_file_path())


def cleanup_old_databases():
    """Remove any old test databases to avoid confusion."""
    old_db_files = [
        'test_database.db',
        'canvas_tracker.db',
    ]
    
    for db_file in old_db_files:
        db_path = Path(db_file)
        if db_path.exists():
            print(f"Removing old database file: {db_path}")
            db_path.unlink()


def setup_test_database(force_recreate: bool = False) -> bool:
    """
    Set up the test database with correct schema.
    
    Args:
        force_recreate: If True, delete existing database and recreate
        
    Returns:
        bool: True if successful, False otherwise
    """
    
    print("Setting up test database...")
    print("=" * 50)
    
    try:
        # Get database configuration
        config = get_config()
        db_path = get_test_database_path()
        
        print(f"Database Environment: {config.environment}")
        print(f"Database URL: {config.database_url}")
        print(f"Database File: {db_path}")
        
        # Clean up old databases first
        cleanup_old_databases()
        
        # Remove existing test database if force_recreate or if it doesn't exist
        if force_recreate or not db_path.exists():
            if db_path.exists():
                print(f"Removing existing database: {db_path}")
                db_path.unlink()
            
            print("Creating new database with correct schema...")
            
            # Create database manager and tables
            db_manager = DatabaseManager()
            db_manager.create_all_tables()
            
            print("✅ Database created successfully!")
        else:
            print(f"Using existing database: {db_path} ({db_path.stat().st_size:,} bytes)")
        
        # Verify schema
        print("\nVerifying database schema...")
        return verify_database_schema()
        
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        import traceback
        traceback.print_exc()
        return False


def verify_database_schema() -> bool:
    """Verify the database schema is correct."""
    try:
        from database.session import get_session
        
        with get_session() as session:
            # Check all expected tables exist
            result = session.execute(text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"))
            tables = [row[0] for row in result.fetchall()]
            
            expected_tables = ['canvas_courses', 'canvas_students', 'canvas_assignments', 'canvas_enrollments']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {missing_tables}")
                return False
            
            print(f"✅ All expected tables present: {expected_tables}")
            
            # Specifically verify canvas_enrollments schema
            result = session.execute(text("PRAGMA table_info(canvas_enrollments)"))
            columns = result.fetchall()
            
            column_info = {col[1]: {'type': col[2], 'pk': bool(col[5])} for col in columns}
            
            # Check for required columns and structure
            if 'id' not in column_info:
                print("❌ canvas_enrollments missing 'id' column")
                return False
                
            if not column_info['id']['pk']:
                print("❌ 'id' column is not primary key")
                return False
                
            required_columns = ['student_id', 'course_id', 'enrollment_date', 'enrollment_status']
            missing_columns = [col for col in required_columns if col not in column_info]
            
            if missing_columns:
                print(f"❌ canvas_enrollments missing columns: {missing_columns}")
                return False
                
            print("✅ canvas_enrollments schema is correct")
            
            # Test database connection
            session.execute(text("SELECT 1"))
            print("✅ Database connection test passed")
            
            return True
            
    except Exception as e:
        print(f"❌ Schema verification failed: {e}")
        return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Set up test database for Canvas Tracker V3')
    parser.add_argument('--force', action='store_true', help='Force recreate database even if it exists')
    parser.add_argument('--verify-only', action='store_true', help='Only verify existing database schema')
    
    args = parser.parse_args()
    
    if args.verify_only:
        print("Verifying existing database schema...")
        success = verify_database_schema()
    else:
        success = setup_test_database(force_recreate=args.force)
    
    if success:
        db_path = get_test_database_path()
        size = db_path.stat().st_size if db_path.exists() else 0
        print(f"\n🎉 Database setup complete!")
        print(f"Database file: {db_path} ({size:,} bytes)")
        print("All tests can now use this database consistently.")
        sys.exit(0)
    else:
        print(f"\n💥 Database setup failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()