"""
Database utilities for Canvas Tracker V3.

This package contains utility modules for database operations:
- exceptions: Custom exception classes for database operations
- validators: Data validation helpers (to be implemented)
- transformers: Canvas API to database transformations (to be implemented)
"""

from .exceptions import (
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

__all__ = [
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