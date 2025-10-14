"""
Base Operations Package.

Foundation classes and utilities for all database operations including:
- Abstract base classes for operation patterns
- Transaction management and rollback strategies  
- Operations-specific exceptions and error handling
- Common validation and logging patterns

Components:
- base_operations.py: BaseOperation and CRUDOperation abstract classes
- exceptions.py: Operations-specific exception definitions
"""

# Base operations foundation
from .base_operations import BaseOperation, CRUDOperation, BulkOperation
from .exceptions import (
    OperationError,
    ValidationError,
    TransactionError,
    DatabaseConnectionError,
    BulkOperationError,
    DataIntegrityError,
    SyncOperationError,
    ConfigurationError,
    handle_operation_error
)

__all__ = [
    # Base operation classes
    'BaseOperation',
    'CRUDOperation', 
    'BulkOperation',
    # Exception classes
    'OperationError',
    'ValidationError',
    'TransactionError',
    'DatabaseConnectionError',
    'BulkOperationError',
    'DataIntegrityError',
    'SyncOperationError',
    'ConfigurationError',
    # Utility functions
    'handle_operation_error'
]
