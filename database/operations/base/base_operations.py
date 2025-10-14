"""
Base Operations Abstract Classes.

Provides foundation classes for all database operations with consistent patterns
for session management, validation, error handling, and transaction coordination.

Abstract Classes:
- BaseOperation: Foundation for all database operations
- CRUDOperation: Standard Create, Read, Update, Delete operations
- BulkOperation: Optimized bulk processing operations
"""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from ...session import DatabaseManager, get_session
from .exceptions import OperationError, ValidationError, TransactionError


class BaseOperation(ABC):
    """
    Abstract base class for all database operations.
    
    Provides common functionality including:
    - Database session management
    - Logging configuration
    - Input validation framework
    - Error handling patterns
    - Transaction coordination
    """
    
    def __init__(self, session: Optional[Session] = None, db_manager: Optional[DatabaseManager] = None):
        """
        Initialize base operation.
        
        Args:
            session: Optional database session. If not provided, will create one.
            db_manager: Optional database manager for session creation.
        """
        self.session = session
        self.db_manager = db_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._owns_session = session is None  # Track if we created the session
        
    def _get_session(self) -> Session:
        """Get database session, creating one if needed."""
        if self.session is None:
            if self.db_manager:
                self.session = self.db_manager.get_session()
            else:
                self.session = get_session()
        return self.session
    
    def _close_session_if_owned(self):
        """Close session only if we created it."""
        if self._owns_session and self.session:
            self.session.close()
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """
        Validate operation input parameters.
        
        Args:
            **kwargs: Operation-specific parameters to validate
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        pass
    
    def log_operation_start(self, operation_name: str, **params):
        """Log the start of an operation."""
        self.logger.info(f"Starting {operation_name}", extra={"params": params})
    
    def log_operation_success(self, operation_name: str, result: Any = None):
        """Log successful completion of an operation."""
        self.logger.info(f"Completed {operation_name} successfully", extra={"result": str(result)[:100] if result else None})
    
    def log_operation_error(self, operation_name: str, error: Exception):
        """Log operation error."""
        self.logger.error(f"Error in {operation_name}: {str(error)}", exc_info=True)
    
    def handle_database_error(self, error: SQLAlchemyError, operation_name: str) -> OperationError:
        """
        Convert SQLAlchemy errors to operation-specific errors.
        
        Args:
            error: SQLAlchemy exception
            operation_name: Name of the operation that failed
            
        Returns:
            OperationError: Standardized operation error
        """
        error_msg = f"{operation_name} failed: {str(error)}"
        self.logger.error(error_msg, exc_info=True)
        
        # Convert to appropriate operation error type
        if "UNIQUE constraint failed" in str(error) or "duplicate key" in str(error).lower():
            return OperationError(f"Duplicate record in {operation_name}: {str(error)}")
        elif "FOREIGN KEY constraint failed" in str(error) or "foreign key" in str(error).lower():
            return OperationError(f"Invalid reference in {operation_name}: {str(error)}")
        else:
            return OperationError(error_msg)
    
    def execute_with_error_handling(self, operation_func, operation_name: str, *args, **kwargs):
        """
        Execute operation with comprehensive error handling.
        
        Args:
            operation_func: Function to execute
            operation_name: Name for logging
            *args: Positional arguments for the operation
            **kwargs: Keyword arguments for the operation
            
        Returns:
            Operation result
            
        Raises:
            OperationError: If operation fails
        """
        try:
            self.log_operation_start(operation_name, args=args, kwargs=kwargs)
            result = operation_func(*args, **kwargs)
            self.log_operation_success(operation_name, result)
            return result
        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except SQLAlchemyError as e:
            # Convert database errors
            raise self.handle_database_error(e, operation_name)
        except Exception as e:
            # Handle unexpected errors
            self.log_operation_error(operation_name, e)
            raise OperationError(f"Unexpected error in {operation_name}: {str(e)}", 
                               operation_name=operation_name, original_exception=e)


class CRUDOperation(BaseOperation):
    """
    Abstract base class for Create, Read, Update, Delete operations.
    
    Provides standard CRUD patterns with:
    - Model-specific operations
    - Bulk operation support
    - Change tracking
    - Optimistic locking support
    """
    
    model_class: Type = None  # Must be set in subclasses
    
    def __init__(self, model_class: Optional[Type] = None, **kwargs):
        """
        Initialize CRUD operation.
        
        Args:
            model_class: SQLAlchemy model class for operations
            **kwargs: Additional arguments passed to BaseOperation
        """
        super().__init__(**kwargs)
        if model_class:
            self.model_class = model_class
        
        if not self.model_class:
            raise ValueError(f"{self.__class__.__name__} requires a model_class")
    
    def validate_input(self, **kwargs) -> bool:
        """Basic validation for CRUD operations."""
        # Can be overridden in subclasses for specific validation
        return True
    
    def validate_data(self, data: Dict[str, Any], operation: str = "unknown") -> bool:
        """
        Validate data for CRUD operations.
        
        Args:
            data: Data to validate
            operation: Type of operation (create, update, etc.)
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ValidationError: If validation fails
        """
        # Default implementation - can be overridden
        if not data:
            raise ValidationError(f"No data provided for {operation}", operation_name=operation)
        return True
    
    def create(self, data: Dict[str, Any], commit: bool = True) -> Any:
        """
        Create a new record.
        
        Args:
            data: Dictionary of field values
            commit: Whether to commit the transaction
            
        Returns:
            Created model instance
        """
        def _create():
            session = self._get_session()
            
            # Validate data
            self.validate_data(data, "create")
            
            # Create instance
            instance = self.model_class(**data)
            session.add(instance)
            
            if commit:
                session.commit()
                session.refresh(instance)
            
            return instance
        
        return self.execute_with_error_handling(_create, "create")
    
    def read(self, identifier: Union[int, str, Dict[str, Any]]) -> Optional[Any]:
        """
        Read a record by identifier.
        
        Args:
            identifier: Primary key value or dictionary of filter criteria
            
        Returns:
            Model instance or None if not found
        """
        def _read():
            session = self._get_session()
            
            if isinstance(identifier, dict):
                # Query by multiple criteria
                return session.query(self.model_class).filter_by(**identifier).first()
            else:
                # Query by primary key
                return session.query(self.model_class).get(identifier)
        
        return self.execute_with_error_handling(_read, "read")
    
    def update(self, identifier: Union[int, str, Dict[str, Any]], data: Dict[str, Any], commit: bool = True) -> Optional[Any]:
        """
        Update an existing record.
        
        Args:
            identifier: Primary key value or filter criteria
            data: Dictionary of field updates
            commit: Whether to commit the transaction
            
        Returns:
            Updated model instance or None if not found
        """
        def _update():
            session = self._get_session()
            
            # Validate data
            self.validate_data(data, "update")
            
            # Find existing record
            instance = self.read(identifier)
            if not instance:
                return None
            
            # Update fields
            for key, value in data.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            
            # Update timestamp if available
            if hasattr(instance, 'updated_at'):
                instance.updated_at = datetime.now(timezone.utc)
            
            if commit:
                session.commit()
                session.refresh(instance)
            
            return instance
        
        return self.execute_with_error_handling(_update, "update")
    
    def delete(self, identifier: Union[int, str, Dict[str, Any]], soft_delete: bool = True, commit: bool = True) -> bool:
        """
        Delete a record.
        
        Args:
            identifier: Primary key value or filter criteria
            soft_delete: Whether to perform soft delete (if supported by model)
            commit: Whether to commit the transaction
            
        Returns:
            True if record was deleted, False if not found
        """
        def _delete():
            session = self._get_session()
            
            # Find existing record
            instance = self.read(identifier)
            if not instance:
                return False
            
            if soft_delete and hasattr(instance, 'active'):
                # Soft delete by setting active=False
                instance.active = False
                if hasattr(instance, 'updated_at'):
                    instance.updated_at = datetime.now(timezone.utc)
            else:
                # Hard delete
                session.delete(instance)
            
            if commit:
                session.commit()
            
            return True
        
        return self.execute_with_error_handling(_delete, "delete")
    
    def list_all(self, limit: Optional[int] = None, offset: Optional[int] = None, 
                 filters: Optional[Dict[str, Any]] = None, order_by: Optional[str] = None) -> List[Any]:
        """
        List records with optional filtering and pagination.
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            filters: Dictionary of filter criteria
            order_by: Field name to order by
            
        Returns:
            List of model instances
        """
        def _list():
            session = self._get_session()
            query = session.query(self.model_class)
            
            # Apply filters
            if filters:
                query = query.filter_by(**filters)
            
            # Apply ordering
            if order_by and hasattr(self.model_class, order_by):
                query = query.order_by(getattr(self.model_class, order_by))
            
            # Apply pagination
            if offset:
                query = query.offset(offset)
            if limit:
                query = query.limit(limit)
            
            return query.all()
        
        return self.execute_with_error_handling(_list, "list_all")
    
    def count(self, filters: Optional[Dict[str, Any]] = None) -> int:
        """
        Count records matching criteria.
        
        Args:
            filters: Dictionary of filter criteria
            
        Returns:
            Number of matching records
        """
        def _count():
            session = self._get_session()
            query = session.query(self.model_class)
            
            if filters:
                query = query.filter_by(**filters)
            
            return query.count()
        
        return self.execute_with_error_handling(_count, "count")


class BulkOperation(BaseOperation):
    """
    Abstract base class for bulk operations on large datasets.
    
    Provides patterns for:
    - Batch processing with configurable batch sizes
    - Progress tracking and reporting
    - Memory-efficient processing
    - Rollback strategies for partial failures
    """
    
    DEFAULT_BATCH_SIZE = 1000
    
    def __init__(self, batch_size: int = DEFAULT_BATCH_SIZE, **kwargs):
        """
        Initialize bulk operation.
        
        Args:
            batch_size: Number of records to process per batch
            **kwargs: Additional arguments passed to BaseOperation
        """
        super().__init__(**kwargs)
        self.batch_size = batch_size
    
    def validate_input(self, **kwargs) -> bool:
        """Validate bulk operation inputs."""
        data_list = kwargs.get('data_list', [])
        if not isinstance(data_list, list):
            raise ValidationError("Bulk operations require data_list parameter")
        return True
    
    def process_in_batches(self, data_list: List[Any], process_func, item_mode: bool = False, **kwargs):
        """
        Process large dataset in configurable batches.
        
        Args:
            data_list: List of data to process
            process_func: Function to process each batch or individual items
            item_mode: If True, process_func handles individual items instead of batches
            **kwargs: Additional arguments for process_func
            
        Returns:
            List of results (batch results or flattened individual results)
        """
        results = []
        total_batches = (len(data_list) + self.batch_size - 1) // self.batch_size
        
        for i in range(0, len(data_list), self.batch_size):
            batch_num = (i // self.batch_size) + 1
            batch_data = data_list[i:i + self.batch_size]
            
            self.logger.info(f"Processing batch {batch_num}/{total_batches} ({len(batch_data)} items)")
            
            try:
                if item_mode:
                    # Process individual items and collect results
                    batch_results = []
                    for item in batch_data:
                        item_result = process_func(item, **kwargs)
                        batch_results.append(item_result)
                    results.extend(batch_results)  # Flatten individual results
                else:
                    # Process entire batch
                    batch_result = process_func(batch_data, **kwargs)
                    results.append(batch_result)
            except Exception as e:
                self.logger.error(f"Error processing batch {batch_num}: {str(e)}")
                raise
        
        return results
    
    def bulk_create(self, data_list: List[Dict[str, Any]], model_class: Type, commit: bool = True) -> List[Any]:
        """
        Bulk create records with batch processing.
        
        Args:
            data_list: List of dictionaries with field values
            model_class: SQLAlchemy model class
            commit: Whether to commit after all batches
            
        Returns:
            List of created instances
        """
        def _bulk_create():
            self.validate_input(data_list=data_list)
            
            def process_batch(batch_data):
                session = self._get_session()
                instances = [model_class(**data) for data in batch_data]
                session.add_all(instances)
                session.flush()  # Flush but don't commit yet
                return instances
            
            all_results = self.process_in_batches(data_list, process_batch)
            
            if commit:
                self._get_session().commit()
            
            # Flatten results
            return [instance for batch in all_results for instance in batch]
        
        return self.execute_with_error_handling(_bulk_create, "bulk_create")
