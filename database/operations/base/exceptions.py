"""
Operations-specific exceptions for the Canvas Tracker database operations.

This module defines custom exceptions that provide specific error handling
for database operations, validation, and transaction management.

These exceptions extend the base database exceptions from utils.exceptions
to provide operation-layer specific context and handling.
"""

from typing import Any, Dict, List, Optional, Union
from database.utils.exceptions import (
    CanvasTrackerDatabaseError, 
    DataValidationError as BaseDataValidationError,
    TransactionError as BaseTransactionError,
    ConnectionError as BaseConnectionError,
    SyncError as BaseSyncError,
    ConfigurationError as BaseConfigurationError
)


class OperationError(CanvasTrackerDatabaseError):
    """
    Base exception for all operation-related errors.
    
    This is the parent class for all custom exceptions in the operations layer.
    Provides structured error information and context.
    """
    
    def __init__(
        self, 
        message: str, 
        operation_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize the operation error.
        
        Args:
            message: Human-readable error message
            operation_name: Name of the operation that failed
            context: Additional context information
            original_exception: The original exception that was caught
        """
        super().__init__(message)
        self.message = message
        self.operation_name = operation_name
        self.context = context or {}
        self.original_exception = original_exception
    
    def __str__(self) -> str:
        """Return a formatted error message."""
        parts = [self.message]
        if self.operation_name:
            parts.append(f"Operation: {self.operation_name}")
        if self.context:
            parts.append(f"Context: {self.context}")
        return " | ".join(parts)


class ValidationError(BaseDataValidationError):
    """
    Exception raised when data validation fails during operations.
    
    Used when input data doesn't meet the required format, type, or
    business rule constraints.
    """
    
    def __init__(
        self,
        message: str,
        field_name: Optional[str] = None,
        invalid_value: Any = None,
        expected_format: Optional[str] = None,
        operation_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize validation error.
        
        Args:
            message: Human-readable validation error message
            field_name: Name of the field that failed validation
            invalid_value: The value that failed validation
            expected_format: Description of expected format/value
            operation_name: Name of the operation that failed validation
            **kwargs: Additional arguments passed to base classes
        """
        # Add operation-specific fields as attributes
        self.field_name = field_name
        self.invalid_value = invalid_value
        self.expected_format = expected_format
        self.operation_name = operation_name
        
        # Initialize base class - it handles field_name and invalid_value in details
        super().__init__(message, field_name=field_name, invalid_value=invalid_value, **kwargs)


class TransactionError(BaseTransactionError):
    """
    Exception raised when database transaction operations fail.
    
    Used for commit failures, rollback issues, or transaction state problems.
    """
    
    def __init__(
        self,
        message: str,
        transaction_state: Optional[str] = None,
        affected_tables: Optional[List[str]] = None,
        **kwargs
    ):
        """
        Initialize transaction error.
        
        Args:
            message: Human-readable transaction error message
            transaction_state: Current state of the transaction
            affected_tables: List of tables affected by the failed transaction
            **kwargs: Additional arguments passed to OperationError
        """
        super().__init__(message, **kwargs)
        self.transaction_state = transaction_state
        self.affected_tables = affected_tables or []


class DatabaseConnectionError(BaseConnectionError):
    """
    Exception raised when database connection issues occur.
    
    Used for connection timeouts, database unavailability, or
    session management problems.
    """
    
    def __init__(
        self,
        message: str,
        connection_details: Optional[Dict[str, Any]] = None,
        retry_count: Optional[int] = None,
        operation_name: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize database connection error.
        
        Args:
            message: Human-readable connection error message
            connection_details: Information about the failed connection
            retry_count: Number of connection attempts made
            operation_name: Name of the operation that failed
            **kwargs: Additional arguments passed to base classes
        """
        super().__init__(message, **kwargs)
        self.connection_details = connection_details or {}
        self.retry_count = retry_count
        self.operation_name = operation_name


class BulkOperationError(OperationError):
    """
    Exception raised when bulk operations encounter errors.
    
    Used for batch processing failures, partial success scenarios,
    or bulk validation issues.
    """
    
    def __init__(
        self,
        message: str,
        total_items: Optional[int] = None,
        processed_items: Optional[int] = None,
        failed_items: Optional[List[Dict[str, Any]]] = None,
        **kwargs
    ):
        """
        Initialize bulk operation error.
        
        Args:
            message: Human-readable bulk operation error message
            total_items: Total number of items in the bulk operation
            processed_items: Number of items successfully processed
            failed_items: List of items that failed with error details
            **kwargs: Additional arguments passed to OperationError
        """
        super().__init__(message, **kwargs)
        self.total_items = total_items
        self.processed_items = processed_items
        self.failed_items = failed_items or []


class DataIntegrityError(OperationError):
    """
    Exception raised when data integrity constraints are violated.
    
    Used for foreign key violations, unique constraint failures,
    or referential integrity issues.
    """
    
    def __init__(
        self,
        message: str,
        constraint_name: Optional[str] = None,
        table_name: Optional[str] = None,
        conflicting_data: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        """
        Initialize data integrity error.
        
        Args:
            message: Human-readable integrity error message
            constraint_name: Name of the violated constraint
            table_name: Name of the table where violation occurred
            conflicting_data: Data that caused the integrity violation
            **kwargs: Additional arguments passed to OperationError
        """
        super().__init__(message, **kwargs)
        self.constraint_name = constraint_name
        self.table_name = table_name
        self.conflicting_data = conflicting_data or {}


class SyncOperationError(BaseSyncError):
    """
    Exception raised during Canvas synchronization operations.
    
    Used for Canvas API errors, data mapping issues, or
    synchronization state problems.
    """
    
    def __init__(
        self,
        message: str,
        canvas_resource_type: Optional[str] = None,
        canvas_resource_id: Optional[Union[str, int]] = None,
        sync_phase: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize sync operation error.
        
        Args:
            message: Human-readable sync error message
            canvas_resource_type: Type of Canvas resource (course, student, etc.)
            canvas_resource_id: ID of the Canvas resource that failed
            sync_phase: Phase of sync where error occurred (fetch, transform, store)
            **kwargs: Additional arguments passed to OperationError
        """
        super().__init__(message, **kwargs)
        self.canvas_resource_type = canvas_resource_type
        self.canvas_resource_id = canvas_resource_id
        self.sync_phase = sync_phase


class ConfigurationError(BaseConfigurationError):
    """
    Exception raised when configuration issues prevent operations.
    
    Used for missing settings, invalid configurations, or
    environment setup problems.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None,
        expected_type: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Human-readable configuration error message
            config_key: Configuration key that has issues
            config_value: Invalid configuration value
            expected_type: Expected type or format for the configuration
            **kwargs: Additional arguments passed to OperationError
        """
        super().__init__(message, **kwargs)
        self.config_key = config_key
        self.config_value = config_value
        self.expected_type = expected_type


# Convenience function for error handling
def handle_operation_error(
    operation_name: str,
    exception: Exception,
    context: Optional[Dict[str, Any]] = None
) -> OperationError:
    """
    Convert generic exceptions to operation-specific errors.
    
    This utility function helps standardize error handling across
    all operation classes by converting generic exceptions into
    our structured operation errors.
    
    Args:
        operation_name: Name of the operation that failed
        exception: The original exception that was caught
        context: Additional context about the operation
    
    Returns:
        OperationError: Structured operation error with context
    """
    if isinstance(exception, OperationError):
        # Already an operation error, preserve and enhance
        if context:
            exception.context.update(context)
        if not exception.operation_name:
            exception.operation_name = operation_name
        return exception
    
    # Map common exception types to specific operation errors
    error_mapping = {
        ValueError: ValidationError,
        TypeError: ValidationError,
        ConnectionError: DatabaseConnectionError,
        TimeoutError: DatabaseConnectionError,
    }
    
    error_class = error_mapping.get(type(exception), OperationError)
    
    # Create the appropriate error type with proper initialization
    if error_class == ValidationError:
        return ValidationError(
            message=str(exception),
            operation_name=operation_name,
            context=context,
            original_exception=exception
        )
    elif error_class == DatabaseConnectionError:
        return DatabaseConnectionError(
            message=str(exception),
            operation_name=operation_name,
            context=context,
            original_exception=exception
        )
    else:
        return OperationError(
            message=str(exception),
            operation_name=operation_name,
            context=context,
            original_exception=exception
        )
