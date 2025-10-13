"""
Canvas Tracker V3 Database Module.

This module provides a complete database layer for the Canvas Tracker application,
organized by architectural layers with clean separation of concerns.

Quick Start:
    from database import get_session, initialize_database
    from database.config import get_config
    
    # Initialize database
    initialize_database()
    
    # Use database sessions
    with get_session() as session:
        # Your database operations here
        pass

Architecture:
    - Layer 0: Object lifecycle management (future implementation)
    - Layer 1: Pure Canvas data (sync-managed)
    - Layer 2: Historical data (sync-generated) 
    - Layer 3: User metadata (persistent)
"""

# Core database infrastructure
from .config import (
    DatabaseConfig,
    get_config,
    get_database_url,
    create_engine_for_environment,
    get_development_engine,
    get_test_engine,
    get_production_engine,
    validate_configuration
)

from .session import (
    DatabaseManager,
    get_db_manager,
    get_session,
    initialize_database,
    close_database,
    create_tables,
    drop_tables,
    recreate_tables,
    health_check,
    with_session,
    with_transaction
)

from .base import (
    Base,
    BaseModel,
    CanvasBaseModel,
    HistoricalBaseModel,
    MetadataBaseModel,
    TimestampMixin,
    SyncTrackingMixin,
    CanvasObjectMixin,
    MetadataMixin,
    CommonColumns
)

# Database utilities
from .utils import (
    CanvasTrackerDatabaseError,
    ConfigurationError,
    ConnectionError,
    SyncError,
    DataValidationError,
    ObjectNotFoundError,
    DuplicateObjectError,
    OperationNotAllowedError,
    TransactionError,
    MigrationError,
    handle_sqlalchemy_error,
    reraise_as_canvas_error,
    DatabaseErrorHandler
)

# Version information
__version__ = "3.0.0"
__author__ = "Canvas Tracker Development Team"

# Main exports
__all__ = [
    # Configuration
    'DatabaseConfig',
    'get_config',
    'get_database_url',
    'create_engine_for_environment',
    'get_development_engine',
    'get_test_engine', 
    'get_production_engine',
    'validate_configuration',
    
    # Session management
    'DatabaseManager',
    'get_db_manager',
    'get_session',
    'initialize_database',
    'close_database',
    'create_tables',
    'drop_tables',
    'recreate_tables',
    'health_check',
    'with_session',
    'with_transaction',
    
    # Base models and mixins
    'Base',
    'BaseModel',
    'CanvasBaseModel',
    'HistoricalBaseModel',
    'MetadataBaseModel',
    'TimestampMixin',
    'SyncTrackingMixin',
    'CanvasObjectMixin',
    'MetadataMixin',
    'CommonColumns',
    
    # Exceptions
    'CanvasTrackerDatabaseError',
    'ConfigurationError',
    'ConnectionError',
    'SyncError',
    'DataValidationError',
    'ObjectNotFoundError',
    'DuplicateObjectError',
    'OperationNotAllowedError',
    'TransactionError',
    'MigrationError',
    'handle_sqlalchemy_error',
    'reraise_as_canvas_error',
    'DatabaseErrorHandler'
]


def setup_logging(level="INFO"):
    """
    Set up logging for the database module.
    
    Args:
        level (str): Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    import logging
    
    logger = logging.getLogger('database')
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


def get_version():
    """Get the database module version."""
    return __version__


def quick_start():
    """
    Quick start guide for the database module.
    
    Returns:
        str: Quick start instructions
    """
    return """
Canvas Tracker Database Module Quick Start:

1. Import the module:
   from database import get_session, initialize_database

2. Initialize the database:
   initialize_database()

3. Use sessions for database operations:
   with get_session() as session:
       # Your database operations here
       student = session.query(CanvasStudent).first()

4. For different environments:
   from database.config import DatabaseConfig
   config = DatabaseConfig('test')  # or 'dev', 'prod'

5. Handle errors:
   from database import SyncError, DataValidationError
   try:
       # Database operations
       pass
   except SyncError as e:
       print(f"Sync failed: {e}")

For more information, see the documentation in database/README.md
"""


if __name__ == "__main__":
    print("Canvas Tracker Database Module")
    print(f"Version: {__version__}")
    print("\n" + quick_start())