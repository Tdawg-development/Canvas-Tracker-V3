#!/usr/bin/env python3
"""
Test Database Helpers

Import this module at the start of any test script to ensure consistent database configuration.
"""

import os
import sys

# Set test environment BEFORE any other imports
os.environ['DATABASE_ENV'] = 'test'

# Add project root to Python path (parent directory since we're in test-environment/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the standardized setup function
from setup_test_database import setup_test_database, get_test_database_path


def ensure_test_database():
    """
    Ensure test database is set up and ready.
    Call this at the start of any test script.
    """
    success = setup_test_database(force_recreate=False)
    if not success:
        print("❌ Failed to set up test database")
        sys.exit(1)
    return get_test_database_path()


def get_test_session():
    """Get a database session configured for testing."""
    ensure_test_database()
    from database.session import get_session
    return get_session()


def reset_test_database():
    """Reset the test database (force recreate)."""
    success = setup_test_database(force_recreate=True)
    if not success:
        print("❌ Failed to reset test database")
        sys.exit(1)
    return get_test_database_path()