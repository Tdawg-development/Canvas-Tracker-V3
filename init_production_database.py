#!/usr/bin/env python3
"""
Initialize production database tables.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Initialize the production database."""
    print("🔧 INITIALIZING PRODUCTION DATABASE")
    print("=" * 50)
    
    try:
        from database.session import initialize_database
        from database.config import get_config
        
        # Show current database configuration
        config = get_config()
        print(f"Database Environment: {config.environment}")
        print(f"Database URL: {config.database_url}")
        
        if config.is_sqlite():
            db_path = config.get_database_file_path()
            print(f"Database File: {db_path}")
        
        print("\nInitializing database tables...")
        initialize_database()
        
        print("✅ Production database initialized successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)