"""
Pytest configuration and shared fixtures for database tests.

This module provides common test fixtures that can be reused across
all test modules, including database setup/teardown and mock objects.
"""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch

# Add the project root to Python path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from database.config import DatabaseConfig
from database.session import DatabaseManager
from database.base import Base, BaseModel, CanvasBaseModel
from database.utils.exceptions import CanvasTrackerDatabaseError
from sqlalchemy import Column, String, Integer


@pytest.fixture(scope="session")
def test_db_config():
    """
    Fixture providing test database configuration.
    
    Uses in-memory SQLite for fast, isolated testing.
    """
    return DatabaseConfig('test')


@pytest.fixture(scope="function")
def db_manager(test_db_config):
    """
    Fixture providing a fresh database manager for each test.
    
    Creates and tears down the database manager, ensuring test isolation.
    """
    manager = DatabaseManager(test_db_config)
    yield manager
    manager.close()


@pytest.fixture(scope="function")
def db_session(db_manager):
    """
    Fixture providing a database session within a transaction.
    
    Automatically rolls back the transaction after each test to maintain
    test isolation while preserving database schema.
    """
    # Create all tables
    db_manager.create_all_tables()
    
    # Get a session
    session = db_manager.get_session()
    
    # Begin a transaction
    transaction = session.begin()
    
    yield session
    
    # Rollback transaction and close session
    transaction.rollback()
    session.close()


@pytest.fixture(scope="function") 
def temporary_db_file():
    """
    Fixture providing a temporary database file path.
    
    Creates a temporary file for testing file-based database operations.
    Cleans up the file after the test.
    """
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = tmp.name
    
    yield db_path
    
    # Clean up with retry for Windows file locking
    import time
    for attempt in range(3):  # Try 3 times
        try:
            os.unlink(db_path)
            break  # Success, exit the loop
        except (FileNotFoundError, PermissionError):
            if attempt < 2:  # Not the last attempt
                time.sleep(0.1)  # Wait briefly and try again
            # On final attempt, just pass (acceptable for cleanup)


# Test model classes for use in tests (not collected by pytest)
class _TestModel(BaseModel):
    """Simple test model for database operations testing."""
    __tablename__ = 'test_model'
    
    name = Column(String(100), nullable=False)
    value = Column(Integer, default=0)
    
    # Using BaseModel's default __repr__


class _TestCanvasModel(CanvasBaseModel):
    """Canvas test model for sync-related testing."""
    __tablename__ = 'test_canvas_model' 
    
    canvas_id = Column(Integer, nullable=False, unique=True)
    description = Column(String(200))
    
    # Using CanvasBaseModel's default __repr__


@pytest.fixture(scope="session")
def test_model_class():
    """Fixture providing the test model class."""
    return _TestModel


@pytest.fixture(scope="session")
def test_canvas_model_class():
    """Fixture providing the test Canvas model class."""
    return _TestCanvasModel


@pytest.fixture(scope="function")
def sample_test_data():
    """
    Fixture providing sample test data for database operations.
    
    Returns a dictionary with various test data structures.
    """
    return {
        'students': [
            {'name': 'John Doe', 'canvas_id': 12345, 'description': 'Test student 1'},
            {'name': 'Jane Smith', 'canvas_id': 67890, 'description': 'Test student 2'},
            {'name': 'Bob Johnson', 'canvas_id': 11111, 'description': 'Test student 3'},
        ],
        'courses': [
            {'name': 'Introduction to Python', 'canvas_id': 101},
            {'name': 'Advanced JavaScript', 'canvas_id': 102},
            {'name': 'Database Design', 'canvas_id': 103},
        ],
        'test_objects': [
            {'name': 'Object 1', 'value': 10},
            {'name': 'Object 2', 'value': 20},
            {'name': 'Object 3', 'value': 30},
        ]
    }


@pytest.fixture(scope="function")
def mock_canvas_api_response():
    """
    Fixture providing mock Canvas API response data.
    
    Useful for testing sync operations without actual API calls.
    """
    return {
        'students': [
            {
                'id': 12345,
                'name': 'John Doe',
                'login_id': 'john.doe@example.com',
                'email': 'john.doe@example.com',
            },
            {
                'id': 67890, 
                'name': 'Jane Smith',
                'login_id': 'jane.smith@example.com',
                'email': 'jane.smith@example.com',
            }
        ],
        'courses': [
            {
                'id': 101,
                'name': 'Introduction to Python',
                'course_code': 'CS101',
                'start_at': '2025-01-15T00:00:00Z',
                'end_at': '2025-05-15T00:00:00Z',
            }
        ]
    }


@pytest.fixture(autouse=True)
def reset_global_state():
    """
    Fixture that automatically resets global state before each test.
    
    Ensures that global variables and singletons don't leak between tests.
    """
    # Reset database manager singleton
    import database.session
    database.session._db_manager = None
    
    # Reset config singleton
    import database.config
    database.config._config_instance = None
    
    yield
    
    # Clean up after test
    database.session._db_manager = None
    database.config._config_instance = None


# Pytest markers for categorizing tests
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )


# Helper functions for tests
def create_test_objects(session, model_class, data_list):
    """
    Helper function to create multiple test objects in the database.
    
    Args:
        session: Database session
        model_class: SQLAlchemy model class
        data_list: List of dictionaries with object data
        
    Returns:
        List of created objects
    """
    objects = []
    for data in data_list:
        obj = model_class(**data)
        session.add(obj)
        objects.append(obj)
    
    session.flush()  # Get IDs without committing
    return objects


def assert_database_state(session, model_class, expected_count):
    """
    Helper function to assert the state of a database table.
    
    Args:
        session: Database session  
        model_class: SQLAlchemy model class to check
        expected_count: Expected number of records
    """
    actual_count = session.query(model_class).count()
    assert actual_count == expected_count, (
        f"Expected {expected_count} {model_class.__name__} records, "
        f"but found {actual_count}"
    )