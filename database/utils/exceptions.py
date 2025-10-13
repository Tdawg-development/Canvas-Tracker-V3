"""
Custom exceptions for Canvas Tracker V3 database operations.

This module defines specific exceptions for different types of database
operations and error conditions, providing clear error handling throughout
the application.
"""

from typing import Optional, Any, Dict
from sqlalchemy.exc import SQLAlchemyError


class CanvasTrackerDatabaseError(Exception):
    """
    Base exception for all Canvas Tracker database-related errors.
    
    All other database exceptions should inherit from this class.
    """
    
    def __init__(self, message: str, details: Dict[str, Any] = None):
        """
        Initialize database error.
        
        Args:
            message (str): Error message
            details (Dict[str, Any], optional): Additional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self):
        """String representation of the error."""
        if self.details:
            details_str = ", ".join(f"{k}={v}" for k, v in self.details.items())
            return f"{self.message} (details: {details_str})"
        return self.message


class ConfigurationError(CanvasTrackerDatabaseError):
    """
    Exception raised for database configuration errors.
    
    Examples:
    - Invalid database URL
    - Missing required configuration
    - Incompatible database settings
    """
    pass


class ConnectionError(CanvasTrackerDatabaseError):
    """
    Exception raised for database connection issues.
    
    Examples:
    - Cannot connect to database
    - Connection timeout
    - Connection lost during operation
    """
    
    def __init__(self, message: str, database_url: str = None, **kwargs):
        """
        Initialize connection error.
        
        Args:
            message (str): Error message
            database_url (str, optional): Database URL that failed
            **kwargs: Additional details
        """
        details = kwargs
        if database_url:
            details['database_url'] = database_url
        super().__init__(message, details)


class SyncError(CanvasTrackerDatabaseError):
    """
    Exception raised during Canvas data synchronization operations.
    
    Examples:
    - Failed to sync Canvas data
    - Data validation errors during sync
    - Partial sync failures
    """
    
    def __init__(self, message: str, sync_type: str = None, failed_objects: list = None, **kwargs):
        """
        Initialize sync error.
        
        Args:
            message (str): Error message
            sync_type (str, optional): Type of sync operation that failed
            failed_objects (list, optional): List of objects that failed to sync
            **kwargs: Additional details
        """
        details = kwargs
        if sync_type:
            details['sync_type'] = sync_type
        if failed_objects:
            details['failed_objects'] = failed_objects
        super().__init__(message, details)


class DataValidationError(CanvasTrackerDatabaseError):
    """
    Exception raised when data validation fails.
    
    Examples:
    - Invalid Canvas object data
    - Missing required fields
    - Data type mismatches
    - Constraint violations
    """
    
    def __init__(self, message: str, field_name: str = None, invalid_value: Any = None, **kwargs):
        """
        Initialize validation error.
        
        Args:
            message (str): Error message
            field_name (str, optional): Name of the field that failed validation
            invalid_value (Any, optional): The invalid value
            **kwargs: Additional details
        """
        details = kwargs
        if field_name:
            details['field_name'] = field_name
        if invalid_value is not None:
            details['invalid_value'] = invalid_value
        super().__init__(message, details)


class ObjectNotFoundError(CanvasTrackerDatabaseError):
    """
    Exception raised when a requested database object is not found.
    
    Examples:
    - Student ID not found in database
    - Course not found during sync
    - Assignment missing during update
    """
    
    def __init__(self, message: str, object_type: str = None, object_id: Any = None, **kwargs):
        """
        Initialize object not found error.
        
        Args:
            message (str): Error message
            object_type (str, optional): Type of object not found (e.g., 'student', 'course')
            object_id (Any, optional): ID of the object that wasn't found
            **kwargs: Additional details
        """
        details = kwargs
        if object_type:
            details['object_type'] = object_type
        if object_id is not None:
            details['object_id'] = object_id
        super().__init__(message, details)


class DuplicateObjectError(CanvasTrackerDatabaseError):
    """
    Exception raised when attempting to create a duplicate object.
    
    Examples:
    - Student with same Canvas ID already exists
    - Duplicate course enrollment
    - Assignment with same ID in course
    """
    
    def __init__(self, message: str, object_type: str = None, duplicate_key: Any = None, **kwargs):
        """
        Initialize duplicate object error.
        
        Args:
            message (str): Error message
            object_type (str, optional): Type of object being duplicated
            duplicate_key (Any, optional): The key that caused the duplication
            **kwargs: Additional details
        """
        details = kwargs
        if object_type:
            details['object_type'] = object_type
        if duplicate_key is not None:
            details['duplicate_key'] = duplicate_key
        super().__init__(message, details)


class OperationNotAllowedError(CanvasTrackerDatabaseError):
    """
    Exception raised when attempting an operation that is not allowed.
    
    Examples:
    - Trying to delete object with dependent data
    - Modifying sync-managed data directly
    - Invalid state transitions
    """
    
    def __init__(self, message: str, operation: str = None, reason: str = None, **kwargs):
        """
        Initialize operation not allowed error.
        
        Args:
            message (str): Error message
            operation (str, optional): The operation that was attempted
            reason (str, optional): Reason why operation is not allowed
            **kwargs: Additional details
        """
        details = kwargs
        if operation:
            details['operation'] = operation
        if reason:
            details['reason'] = reason
        super().__init__(message, details)


class TransactionError(CanvasTrackerDatabaseError):
    """
    Exception raised for transaction-related errors.
    
    Examples:
    - Transaction deadlock
    - Rollback failures
    - Commit conflicts
    """
    
    def __init__(self, message: str, transaction_id: str = None, **kwargs):
        """
        Initialize transaction error.
        
        Args:
            message (str): Error message
            transaction_id (str, optional): ID of the failed transaction
            **kwargs: Additional details
        """
        details = kwargs
        if transaction_id:
            details['transaction_id'] = transaction_id
        super().__init__(message, details)


class MigrationError(CanvasTrackerDatabaseError):
    """
    Exception raised during database migration operations.
    
    Examples:
    - Schema migration failures
    - Data migration errors
    - Version conflicts
    """
    
    def __init__(self, message: str, migration_version: str = None, **kwargs):
        """
        Initialize migration error.
        
        Args:
            message (str): Error message
            migration_version (str, optional): Version of the migration that failed
            **kwargs: Additional details
        """
        details = kwargs
        if migration_version:
            details['migration_version'] = migration_version
        super().__init__(message, details)


# Exception handling utilities
def handle_sqlalchemy_error(error: SQLAlchemyError, operation: str = None) -> CanvasTrackerDatabaseError:
    """
    Convert SQLAlchemy exceptions to Canvas Tracker exceptions.
    
    Args:
        error (SQLAlchemyError): Original SQLAlchemy error
        operation (str, optional): Description of the operation that failed
        
    Returns:
        CanvasTrackerDatabaseError: Appropriate Canvas Tracker exception
    """
    error_message = str(error)
    
    # Map common SQLAlchemy errors to specific exceptions
    if "connection" in error_message.lower():
        return ConnectionError(
            f"Database connection error during {operation or 'operation'}",
            original_error=str(error)
        )
    
    elif "unique constraint" in error_message.lower() or "duplicate" in error_message.lower():
        return DuplicateObjectError(
            f"Duplicate object error during {operation or 'operation'}",
            original_error=str(error)
        )
    
    elif "foreign key" in error_message.lower():
        return DataValidationError(
            f"Foreign key constraint violation during {operation or 'operation'}",
            original_error=str(error)
        )
    
    elif "not found" in error_message.lower():
        return ObjectNotFoundError(
            f"Object not found during {operation or 'operation'}",
            original_error=str(error)
        )
    
    else:
        # Generic database error
        return CanvasTrackerDatabaseError(
            f"Database error during {operation or 'operation'}: {error_message}",
            details={'original_error': str(error)}
        )


def reraise_as_canvas_error(operation: str):
    """
    Decorator that converts SQLAlchemy errors to Canvas Tracker errors.
    
    Args:
        operation (str): Description of the operation being performed
        
    Usage:
        @reraise_as_canvas_error("student creation")
        def create_student(data):
            # Database operations that might raise SQLAlchemy errors
            pass
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except SQLAlchemyError as e:
                raise handle_sqlalchemy_error(e, operation)
            except CanvasTrackerDatabaseError:
                # Re-raise our own exceptions unchanged
                raise
        return wrapper
    return decorator


# Context manager for exception handling
class DatabaseErrorHandler:
    """
    Context manager for handling database errors with logging and cleanup.
    
    Usage:
        with DatabaseErrorHandler("sync operation") as handler:
            # Database operations
            sync_canvas_data()
    """
    
    def __init__(self, operation: str, logger=None):
        """
        Initialize error handler.
        
        Args:
            operation (str): Description of the operation
            logger: Logger instance for error logging
        """
        self.operation = operation
        self.logger = logger
        
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            # Log the error if logger is available
            if self.logger:
                self.logger.error(f"Error during {self.operation}: {exc_val}")
            
            # Convert SQLAlchemy errors to Canvas Tracker errors
            if issubclass(exc_type, SQLAlchemyError):
                canvas_error = handle_sqlalchemy_error(exc_val, self.operation)
                raise canvas_error from exc_val
        
        return False  # Don't suppress other exceptions


if __name__ == "__main__":
    # Test exception handling
    print("Testing Canvas Tracker database exceptions...")
    
    # Test basic exception creation
    try:
        raise SyncError("Test sync error", sync_type="full_sync", failed_objects=["student_123"])
    except SyncError as e:
        print(f"✓ SyncError: {e}")
    
    try:
        raise DataValidationError("Invalid grade value", field_name="grade", invalid_value=-10)
    except DataValidationError as e:
        print(f"✓ DataValidationError: {e}")
    
    try:
        raise ObjectNotFoundError("Student not found", object_type="student", object_id=12345)
    except ObjectNotFoundError as e:
        print(f"✓ ObjectNotFoundError: {e}")
    
    print("✓ Exception tests completed successfully!")