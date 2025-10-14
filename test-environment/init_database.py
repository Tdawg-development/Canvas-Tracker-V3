#!/usr/bin/env python3
"""
Database Initialization Script

Creates all database tables for Canvas Tracker V3.
This script ensures all required tables exist before running integration tests.
"""

import os
import sys

# Add project root to path (parent directory since we're in test-environment/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.session import DatabaseManager
from database.base import Base
from database.models.layer1_canvas import *  # Import all Canvas models
from database.config import get_config


def initialize_database():
    """Initialize database by creating all tables."""
    print("Canvas Tracker V3 - Database Initialization")
    print("=" * 60)
    
    # Set database environment to test
    os.environ['DATABASE_ENV'] = 'test'
    
    config = get_config()
    print(f"Database Environment: {config.environment}")
    print(f"Database URL: {config.database_url}")
    
    if config.is_sqlite():
        db_path = config.get_database_file_path()
        print(f"Database File: {db_path}")
        
        # Check if database file exists
        if db_path and os.path.exists(db_path):
            size = os.path.getsize(db_path)
            print(f"Existing File Size: {size:,} bytes")
        else:
            print("Database file will be created")
    
    print("\nCreating all database tables...")
    
    try:
        # Create database manager
        db_manager = DatabaseManager(config)
        
        # Create all tables
        db_manager.create_all_tables()
        
        print("✅ Database tables created successfully!")
        
        # List created tables
        print("\nCreated tables:")
        for table_name in Base.metadata.tables.keys():
            print(f"  - {table_name}")
            
        # Test database connection
        print("\nTesting database connection...")
        health_check = db_manager.health_check()
        if health_check:
            print("✅ Database connection test passed!")
        else:
            print("❌ Database connection test failed!")
            return
            
        if config.is_sqlite():
            db_path = config.get_database_file_path()
            if db_path and os.path.exists(db_path):
                size = os.path.getsize(db_path)
                print(f"\nFinal database file size: {size:,} bytes")
                
        print("\n🎉 Database initialization complete!")
        print("You can now run the Canvas integration test.")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    initialize_database()