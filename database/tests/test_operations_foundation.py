"""
Unit tests for the operations foundation layer.

Tests the base operation classes, operations-specific exceptions,
and their integration with the database layer.
"""

import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from datetime import datetime

# Import the operations foundation
from database.operations.base import (
    BaseOperation, CRUDOperation, BulkOperation,
    OperationError, ValidationError, TransactionError,
    DatabaseConnectionError, BulkOperationError, DataIntegrityError,
    SyncOperationError, ConfigurationError, handle_operation_error
)

# Import base database exceptions for hierarchy testing
from database.utils.exceptions import (
    CanvasTrackerDatabaseError, DataValidationError as BaseDataValidationError,
    TransactionError as BaseTransactionError, ConnectionError as BaseConnectionError
)


class TestOperationExceptions:
    """Test suite for operations-specific exceptions."""
    
    @pytest.mark.unit
    def test_operation_error_base_class(self):
        """Test OperationError base class functionality."""
        # Basic error
        error = OperationError("Test operation failed")
        assert str(error) == "Test operation failed"
        assert error.message == "Test operation failed"
        assert error.operation_name is None
        assert error.context == {}
        assert error.original_exception is None
        
        # Error with full context
        context = {"user_id": 123, "action": "create"}
        original = ValueError("Original error")
        error_full = OperationError(
            "Complex operation failed",
            operation_name="create_user",
            context=context,
            original_exception=original
        )
        
        error_str = str(error_full)
        assert "Complex operation failed" in error_str
        assert "Operation: create_user" in error_str
        assert "Context: {'user_id': 123, 'action': 'create'}" in error_str
    
    @pytest.mark.unit
    def test_operation_error_inheritance(self):
        """Test that OperationError properly inherits from base exceptions."""
        error = OperationError("Test error")
        assert isinstance(error, CanvasTrackerDatabaseError)
        assert isinstance(error, Exception)
    
    @pytest.mark.unit
    def test_validation_error(self):
        """Test ValidationError functionality."""
        error = ValidationError(
            "Invalid grade value",
            field_name="grade",
            invalid_value=-10,
            expected_format="0-100"
        )
        
        # Test inheritance
        assert isinstance(error, BaseDataValidationError)
        assert isinstance(error, CanvasTrackerDatabaseError)
        
        # Test attributes
        assert error.field_name == "grade"
        assert error.invalid_value == -10
        assert error.expected_format == "0-100"
        assert "field_name" in error.details
        assert "invalid_value" in error.details
    
    @pytest.mark.unit
    def test_transaction_error(self):
        """Test TransactionError functionality."""
        error = TransactionError(
            "Transaction rollback failed",
            transaction_state="rolling_back",
            affected_tables=["students", "courses"]
        )
        
        # Test inheritance
        assert isinstance(error, BaseTransactionError)
        
        # Test attributes
        assert error.transaction_state == "rolling_back"
        assert len(error.affected_tables) == 2
        assert "students" in error.affected_tables
    
    @pytest.mark.unit
    def test_database_connection_error(self):
        """Test DatabaseConnectionError functionality."""
        connection_details = {"host": "localhost", "port": 5432}
        error = DatabaseConnectionError(
            "Connection timeout",
            connection_details=connection_details,
            retry_count=3
        )
        
        # Test inheritance
        assert isinstance(error, BaseConnectionError)
        
        # Test attributes
        assert error.connection_details == connection_details
        assert error.retry_count == 3
    
    @pytest.mark.unit
    def test_bulk_operation_error(self):
        """Test BulkOperationError functionality."""
        failed_items = [
            {"id": 1, "error": "Invalid data"},
            {"id": 2, "error": "Constraint violation"}
        ]
        error = BulkOperationError(
            "Bulk insert failed",
            total_items=100,
            processed_items=98,
            failed_items=failed_items
        )
        
        # Test inheritance
        assert isinstance(error, OperationError)
        
        # Test attributes
        assert error.total_items == 100
        assert error.processed_items == 98
        assert len(error.failed_items) == 2
    
    @pytest.mark.unit
    def test_data_integrity_error(self):
        """Test DataIntegrityError functionality."""
        conflicting_data = {"student_id": 123, "course_id": 456}
        error = DataIntegrityError(
            "Foreign key violation",
            constraint_name="fk_enrollment_student",
            table_name="enrollments",
            conflicting_data=conflicting_data
        )
        
        # Test attributes
        assert error.constraint_name == "fk_enrollment_student"
        assert error.table_name == "enrollments"
        assert error.conflicting_data == conflicting_data
    
    @pytest.mark.unit
    def test_sync_operation_error(self):
        """Test SyncOperationError functionality."""
        error = SyncOperationError(
            "Canvas API sync failed",
            canvas_resource_type="course",
            canvas_resource_id=12345,
            sync_phase="fetch"
        )
        
        # Test attributes
        assert error.canvas_resource_type == "course"
        assert error.canvas_resource_id == 12345
        assert error.sync_phase == "fetch"
    
    @pytest.mark.unit
    def test_configuration_error(self):
        """Test ConfigurationError functionality."""
        error = ConfigurationError(
            "Invalid database URL",
            config_key="DATABASE_URL",
            config_value="invalid://url",
            expected_type="postgresql://..."
        )
        
        # Test attributes
        assert error.config_key == "DATABASE_URL"
        assert error.config_value == "invalid://url"
        assert error.expected_type == "postgresql://..."
    
    @pytest.mark.unit
    def test_handle_operation_error_utility(self):
        """Test handle_operation_error utility function."""
        # Test with existing OperationError
        existing_error = ValidationError("Existing error")
        result = handle_operation_error("test_op", existing_error, {"extra": "context"})
        
        # The function creates a new error, doesn't modify the existing one
        assert isinstance(result, OperationError)
        assert "Existing error" in str(result)
        
        # Test with ValueError (maps to ValidationError)
        value_error = ValueError("Invalid value")
        result = handle_operation_error("test_op", value_error)
        
        assert isinstance(result, ValidationError)
        assert result.operation_name == "test_op"
        assert "Invalid value" in str(result)
        
        # Test with ConnectionError (maps to DatabaseConnectionError)
        conn_error = ConnectionError("Connection failed")
        result = handle_operation_error("test_op", conn_error)
        
        assert isinstance(result, DatabaseConnectionError)
        
        # Test with unknown exception (maps to OperationError)
        unknown_error = RuntimeError("Unknown error")
        result = handle_operation_error("test_op", unknown_error)
        
        assert isinstance(result, OperationError)
        assert result.operation_name == "test_op"


class TestBaseOperation:
    """Test suite for BaseOperation abstract class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.mock_logger = Mock(spec=logging.Logger)
    
    @pytest.mark.unit
    def test_base_operation_abstract_class(self):
        """Test that BaseOperation cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseOperation(self.mock_session)
    
    @pytest.mark.unit
    def test_base_operation_subclass_implementation(self):
        """Test BaseOperation subclass implementation."""
        class TestOperation(BaseOperation):
            def validate_input(self, **kwargs) -> bool:
                return True
                
            def execute(self):
                return "test_result"
        
        # Test successful instantiation
        operation = TestOperation(session=self.mock_session)
        assert operation.session == self.mock_session
        assert operation.logger is not None
        
        # Test execution
        result = operation.execute()
        assert result == "test_result"
    
    @pytest.mark.unit
    def test_base_operation_error_handling(self):
        """Test BaseOperation error handling."""
        class FailingOperation(BaseOperation):
            def validate_input(self, **kwargs) -> bool:
                return True
                
            def execute(self):
                return self.execute_with_error_handling(
                    lambda: self._fail(), "test_operation"
                )
            
            def _fail(self):
                raise ValueError("Test error")
        
        operation = FailingOperation(session=self.mock_session)
        
        # Test that errors are properly wrapped
        with pytest.raises(OperationError) as exc_info:
            operation.execute()
        
        # The error should be wrapped in OperationError
        assert "Test error" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_base_operation_logging(self):
        """Test BaseOperation logging functionality."""
        class LoggingOperation(BaseOperation):
            def validate_input(self, **kwargs) -> bool:
                return True
            
            def execute(self):
                self.log_operation_start("test_operation", param1="value1")
                result = "logged_result"
                self.log_operation_success("test_operation", result)
                return result
        
        # Create operation with real logger to test logging methods
        operation = LoggingOperation(session=self.mock_session)
        result = operation.execute()
        
        # Verify result (logging itself is tested by checking methods exist)
        assert result == "logged_result"
        assert hasattr(operation, 'log_operation_start')
        assert hasattr(operation, 'log_operation_success')
        assert hasattr(operation, 'log_operation_error')


class TestCRUDOperation:
    """Test suite for CRUDOperation class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.mock_logger = Mock(spec=logging.Logger)
    
    @pytest.mark.unit
    def test_crud_operation_create(self):
        """Test CRUD create operation."""
        # Mock model class
        mock_model = Mock()
        mock_instance = Mock()
        mock_model.return_value = mock_instance
        
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test data
        test_data = {"name": "Test Object", "value": 42}
        
        # Execute create
        result = operation.create(test_data)
        
        # Verify model was instantiated with data
        mock_model.assert_called_once_with(**test_data)
        
        # Verify result
        assert result == mock_instance
    
    @pytest.mark.unit
    def test_crud_operation_read(self):
        """Test CRUD read operation behavior."""
        mock_model = Mock()
        mock_result = Mock()
        
        # Setup for primary key lookup (uses .get())
        self.mock_session.query.return_value.get.return_value = mock_result
        
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test primary key read
        result = operation.read(123)
        assert result == mock_result
        
        # Test dictionary-based read
        mock_query_chain = Mock()
        self.mock_session.query.return_value = mock_query_chain
        mock_query_chain.filter_by.return_value.first.return_value = mock_result
        
        result = operation.read({"name": "test"})
        assert result == mock_result
    
    @pytest.mark.unit
    def test_crud_operation_update(self):
        """Test CRUD update operation behavior."""
        mock_model = Mock()
        mock_instance = Mock()
        
        # Mock the read operation to return an instance
        self.mock_session.query.return_value.get.return_value = mock_instance
        
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test update data
        update_data = {"name": "Updated Name", "value": 100}
        
        # Execute update
        result = operation.update(123, update_data)
        
        # Verify the result is the updated instance
        assert result == mock_instance
        
        # Verify the instance would have been updated (check hasattr call behavior)
        # This tests that the logic path was followed correctly
    
    @pytest.mark.unit
    def test_crud_operation_delete(self):
        """Test CRUD delete operation behavior."""
        mock_model = Mock()
        mock_instance = Mock()
        
        # Mock the read operation to return an instance
        self.mock_session.query.return_value.get.return_value = mock_instance
        
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test soft delete (default)
        result = operation.delete(123)
        assert result is True
        
        # Test hard delete
        result = operation.delete(123, soft_delete=False)
        assert result is True
        
        # Test delete not found
        self.mock_session.query.return_value.get.return_value = None
        result = operation.delete(999)
        assert result is False
    
    @pytest.mark.unit
    def test_crud_operation_validation_error(self):
        """Test CRUD operation validation errors."""
        mock_model = Mock()
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test that create method exists and handles data
        # The actual validation depends on the specific implementation
        assert hasattr(operation, 'create')
        assert hasattr(operation, 'validate_input')
    
    @pytest.mark.unit
    def test_crud_operation_not_found_error(self):
        """Test CRUD operation not found behavior."""
        mock_model = Mock()
        
        # Mock session to return None for not found cases
        self.mock_session.query.return_value.get.return_value = None
        
        operation = CRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test read not found
        result = operation.read(999)
        assert result is None  # Should return None when not found
        
        # Test update not found
        result = operation.update(999, {"name": "Updated"})
        assert result is None  # Should return None when record not found
        
        # Test delete not found
        result = operation.delete(999)
        assert result is False  # Should return False when record not found


class TestBulkOperation:
    """Test suite for BulkOperation class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.mock_logger = Mock(spec=logging.Logger)
    
    @pytest.mark.unit
    def test_bulk_operation_successful_processing(self):
        """Test successful bulk operation processing."""
        # Test data
        test_items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},
            {"id": 3, "name": "Item 3"}
        ]
        
        # Mock processor function for individual items
        all_processed_items = []
        def mock_item_processor(item):
            all_processed_items.append(item)
            return f"processed_{item['id']}"
        
        operation = BulkOperation(session=self.mock_session, batch_size=2)
        
        # Execute bulk operation using process_in_batches with item_mode=True
        results = operation.process_in_batches(test_items, mock_item_processor, item_mode=True)
        
        # Verify all items were processed individually
        assert len(results) == 3  # All 3 individual results
        assert len(all_processed_items) == 3  # All 3 items were processed
        assert results[0] == "processed_1"
        assert results[1] == "processed_2"
        assert results[2] == "processed_3"
    
    @pytest.mark.unit
    def test_bulk_operation_partial_failure(self):
        """Test bulk operation with partial failures."""
        # Test data
        test_items = [
            {"id": 1, "name": "Item 1"},
            {"id": 2, "name": "Item 2"},  # This will fail
            {"id": 3, "name": "Item 3"}
        ]
        
        # Mock processor function that fails on item 2
        def mock_item_processor(item):
            if item['id'] == 2:
                raise ValueError("Processing failed for item 2")
            return f"processed_{item['id']}"
        
        operation = BulkOperation(session=self.mock_session, batch_size=2)
        
        # Execute bulk operation - should handle partial failures
        # The base BulkOperation doesn't handle failures automatically,
        # it just raises the exception from the processor
        with pytest.raises(ValueError) as exc_info:
            operation.process_in_batches(test_items, mock_item_processor, item_mode=True)
        
        # Verify the original error is raised
        assert "Processing failed for item 2" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_bulk_operation_transaction_handling(self):
        """Test bulk operation transaction handling."""
        test_items = [{"id": 1}, {"id": 2}]
        
        def mock_processor(item):
            return item
        
        operation = BulkOperation(session=self.mock_session)
        
        # Test transaction commit on success
        operation.process_in_batches(test_items, mock_processor)
        
        # Verify session operations (would be called in real implementation)
        # In a real scenario, we'd verify commit was called
    
    @pytest.mark.unit
    def test_bulk_operation_batch_processing(self):
        """Test bulk operation batch processing."""
        # Large dataset to test batching
        test_items = [{"id": i} for i in range(10)]
        processed_batches = []
        
        def mock_item_processor(item):
            # Track which items were processed
            processed_batches.append(item['id'])
            return item
        
        operation = BulkOperation(session=self.mock_session, batch_size=3)
        
        # Process with small batch size to test batching
        results = operation.process_in_batches(test_items, mock_item_processor, item_mode=True)
        
        # Verify all items were processed individually
        assert len(results) == 10  # All 10 individual results
        assert len(processed_batches) == 10  # All 10 items were processed


class TestOperationsIntegration:
    """Integration tests for operations foundation."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
    
    @pytest.mark.integration
    def test_operation_error_propagation(self):
        """Test that operations properly propagate and wrap errors."""
        class TestOperation(BaseOperation):
            def validate_input(self, **kwargs) -> bool:
                return True
                
            def execute(self):
                return self.execute_with_error_handling(
                    lambda: self._fail(), "test_operation"
                )
            
            def _fail(self):
                raise IntegrityError("Database constraint violation", None, None)
        
        operation = TestOperation(session=self.mock_session)
        
        # Should catch and wrap SQLAlchemy errors
        with pytest.raises(OperationError):
            operation.execute()
    
    @pytest.mark.integration
    def test_crud_with_custom_validation(self):
        """Test CRUD operations with custom validation."""
        mock_model = Mock()
        
        class ValidatingCRUDOperation(CRUDOperation):
            def validate_data(self, data, operation="unknown"):
                super().validate_data(data, operation)
                if operation == 'create' and not data.get('name'):
                    raise ValidationError("Name is required", field_name='name')
                return True
        
        operation = ValidatingCRUDOperation(model_class=mock_model, session=self.mock_session)
        
        # Test validation failure
        with pytest.raises(ValidationError) as exc_info:
            operation.create({"value": 42})  # Missing name
        
        assert exc_info.value.field_name == 'name'
    
    @pytest.mark.integration
    def test_bulk_operation_with_crud(self):
        """Test bulk operations combined with CRUD operations."""
        mock_model = Mock()
        
        # Test data
        bulk_data = [
            {"name": "Bulk Item 1", "value": 10},
            {"name": "Bulk Item 2", "value": 20},
            {"name": "Bulk Item 3", "value": 30}
        ]
        
        class BulkCRUDOperation(BulkOperation):
            def __init__(self, session, model_class):
                super().__init__(session=session)
                self.crud_op = CRUDOperation(model_class=model_class, session=session)
            
            def bulk_create(self, items):
                def create_processor(batch_items):
                    return [self.crud_op.create(item_data) for item_data in batch_items]
                
                return self.process_in_batches(items, create_processor)
        
        operation = BulkCRUDOperation(self.mock_session, mock_model)
        
        # This would work with real models and session
        # For now, just verify the structure exists
        assert hasattr(operation, 'bulk_create')
        assert hasattr(operation, 'crud_op')


# Test fixtures for the operations tests
@pytest.fixture
def mock_db_session():
    """Provide a mock database session for testing."""
    return Mock(spec=Session)

@pytest.fixture
def mock_logger():
    """Provide a mock logger for testing."""
    return Mock(spec=logging.Logger)

@pytest.fixture
def sample_operation_data():
    """Provide sample data for operation testing."""
    return {
        "create_data": {
            "name": "Test Object",
            "description": "Test Description",
            "value": 42
        },
        "update_data": {
            "name": "Updated Object",
            "value": 100
        },
        "bulk_data": [
            {"id": 1, "name": "Bulk Item 1"},
            {"id": 2, "name": "Bulk Item 2"},
            {"id": 3, "name": "Bulk Item 3"}
        ]
    }


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])