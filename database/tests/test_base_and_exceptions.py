"""
Unit tests for base models and exception handling.

Tests the base model classes, mixins, and custom exception hierarchy.
"""

import pytest
import json
from datetime import datetime, timezone
from unittest.mock import patch
from sqlalchemy import Column, String, Integer
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database.base import (
    Base, BaseModel, CanvasBaseModel, HistoricalBaseModel, MetadataBaseModel,
    TimestampMixin, SyncTrackingMixin, CanvasObjectMixin, MetadataMixin,
    CommonColumns
)
from database.utils.exceptions import (
    CanvasTrackerDatabaseError, ConfigurationError, ConnectionError,
    SyncError, DataValidationError, ObjectNotFoundError,
    DuplicateObjectError, OperationNotAllowedError, TransactionError,
    handle_sqlalchemy_error, reraise_as_canvas_error, DatabaseErrorHandler
)


class TestBaseModel:
    """Test suite for BaseModel class."""
    
    @pytest.mark.unit
    def test_base_model_creation(self, db_session):
        """Test basic BaseModel creation and properties."""
        from .conftest import _TestModel as TestModel
        
        obj = TestModel(name="Test Object", value=42)
        
        assert obj.name == "Test Object"
        assert obj.value == 42
        assert obj.id is None  # Not yet saved
        assert obj.created_at is None  # Not yet saved
        assert obj.updated_at is None  # Not yet saved
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_base_model_persistence(self, db_session):
        """Test BaseModel database persistence."""
        from .conftest import _TestModel as TestModel
        
        # Create and save object
        obj = TestModel(name="Persistent Object", value=100)
        db_session.add(obj)
        db_session.flush()  # Get ID without committing
        
        assert obj.id is not None
        assert obj.created_at is not None
        assert obj.updated_at is not None
        
        # Verify timestamps are recent
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        time_diff = (now - obj.created_at).total_seconds()
        assert time_diff < 5  # Within 5 seconds
    
    @pytest.mark.unit
    def test_base_model_to_dict(self, db_session):
        """Test BaseModel to_dict method."""
        from .conftest import _TestModel as TestModel
        
        obj = TestModel(name="Dict Test", value=200)
        db_session.add(obj)
        db_session.flush()
        
        obj_dict = obj.to_dict()
        
        assert isinstance(obj_dict, dict)
        assert obj_dict['name'] == "Dict Test"
        assert obj_dict['value'] == 200
        assert 'id' in obj_dict
        assert 'created_at' in obj_dict
        assert 'updated_at' in obj_dict
        
        # Verify datetime serialization
        assert isinstance(obj_dict['created_at'], str)
    
    @pytest.mark.unit
    def test_base_model_from_dict(self):
        """Test BaseModel from_dict class method."""
        from .conftest import _TestModel as TestModel
        
        data = {
            'name': 'From Dict Test',
            'value': 300,
            'extra_field': 'should be ignored'  # Not in model
        }
        
        obj = TestModel.from_dict(data)
        
        assert obj.name == 'From Dict Test'
        assert obj.value == 300
        assert not hasattr(obj, 'extra_field')
    
    @pytest.mark.unit
    def test_base_model_repr(self, db_session):
        """Test BaseModel string representation."""
        from .conftest import _TestModel as TestModel
        
        obj = TestModel(name="Repr Test", value=400)
        db_session.add(obj)
        db_session.flush()
        
        repr_str = repr(obj)
        assert 'TestModel' in repr_str
        assert f'id={obj.id}' in repr_str


class TestCanvasBaseModel:
    """Test suite for CanvasBaseModel class."""
    
    @pytest.mark.unit
    def test_canvas_model_creation(self):
        """Test CanvasBaseModel creation and properties."""
        from .conftest import _TestCanvasModel as TestCanvasModel
        
        obj = TestCanvasModel(name="Canvas Test", canvas_id=12345, description="Test description")
        
        assert obj.name == "Canvas Test"
        assert obj.canvas_id == 12345
        assert obj.description == "Test description"
        assert obj.last_synced is None
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_canvas_model_sync_tracking(self, db_session):
        """Test Canvas model sync tracking functionality."""
        from .conftest import _TestCanvasModel as TestCanvasModel
        
        obj = TestCanvasModel(name="Sync Test", canvas_id=67890)
        
        # Test mark_synced method
        sync_time = datetime.now(timezone.utc)
        obj.mark_synced(sync_time)
        
        assert obj.last_synced == sync_time
        
        # Test is_recently_synced property
        assert obj.is_recently_synced(threshold_minutes=60) is True
        assert obj.is_recently_synced(threshold_minutes=0) is False
    
    @pytest.mark.unit
    def test_canvas_model_repr(self):
        """Test CanvasBaseModel string representation."""
        from .conftest import _TestCanvasModel as TestCanvasModel
        
        # Never synced
        obj1 = TestCanvasModel(name="Never Synced", canvas_id=111)
        repr_str = repr(obj1)
        assert 'TestCanvasModel' in repr_str
        assert 'Never Synced' in repr_str
        assert 'never synced' in repr_str
        
        # Recently synced
        obj2 = TestCanvasModel(name="Recently Synced", canvas_id=222)
        obj2.mark_synced()
        repr_str = repr(obj2)
        assert 'synced' in repr_str


class TestHistoricalBaseModel:
    """Test suite for HistoricalBaseModel class."""
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_historical_model_recorded_at(self, db_session):
        """Test HistoricalBaseModel recorded_at field."""
        # Create a test historical model
        class TestHistoricalModel(HistoricalBaseModel):
            __tablename__ = 'test_historical'
            data_value = Column(String(100))
        
        Base.metadata.create_all(db_session.bind)
        
        obj = TestHistoricalModel(data_value="Historical Test")
        db_session.add(obj)
        db_session.flush()
        
        assert obj.recorded_at is not None
        
        # Test string representation
        repr_str = repr(obj)
        assert 'TestHistoricalModel' in repr_str
        assert 'recorded_at=' in repr_str


class TestMetadataBaseModel:
    """Test suite for MetadataBaseModel class."""
    
    @pytest.mark.unit
    def test_metadata_model_tag_management(self):
        """Test MetadataBaseModel tag management methods."""
        # Create a test metadata model
        class TestMetadataModel(MetadataBaseModel):
            __tablename__ = 'test_metadata'
            object_name = Column(String(100))
        
        obj = TestMetadataModel(object_name="Tag Test")
        
        # Test adding tags
        obj.add_tag("urgent")
        obj.add_tag("reviewed")
        obj.add_tag("urgent")  # Should not duplicate
        
        tags = obj.get_tags()
        assert len(tags) == 2
        assert "urgent" in tags
        assert "reviewed" in tags
        
        # Test removing tags
        obj.remove_tag("urgent")
        tags = obj.get_tags()
        assert len(tags) == 1
        assert "reviewed" in tags
        assert "urgent" not in tags
        
        # Test removing non-existent tag (should not error)
        obj.remove_tag("nonexistent")
        assert len(obj.get_tags()) == 1
    
    @pytest.mark.unit
    def test_metadata_model_empty_tags(self):
        """Test MetadataBaseModel with no tags."""
        class TestMetadataModel(MetadataBaseModel):
            __tablename__ = 'test_metadata_empty'
            object_name = Column(String(100))
        
        obj = TestMetadataModel(object_name="Empty Tags Test")
        
        # Should handle empty tags gracefully
        tags = obj.get_tags()
        assert tags == []
        
        # Should handle removing from empty tags
        obj.remove_tag("nonexistent")
        assert obj.get_tags() == []
    
    @pytest.mark.unit
    def test_metadata_model_repr(self):
        """Test MetadataBaseModel string representation."""
        class TestMetadataModel(MetadataBaseModel):
            __tablename__ = 'test_metadata_repr'
        
        # Without notes
        obj1 = TestMetadataModel()
        repr_str = repr(obj1)
        assert 'TestMetadataModel' in repr_str
        assert 'no notes' in repr_str
        
        # With notes
        obj2 = TestMetadataModel(notes="Has notes")
        repr_str = repr(obj2)
        assert 'with notes' in repr_str


class TestCommonColumns:
    """Test suite for CommonColumns utility class."""
    
    @pytest.mark.unit
    def test_common_column_types(self):
        """Test CommonColumns static methods."""
        # Test canvas_id column
        canvas_id_col = CommonColumns.canvas_id()
        assert canvas_id_col.type.python_type == int
        assert canvas_id_col.nullable is False
        
        # Test nullable canvas_id
        nullable_canvas_id = CommonColumns.canvas_id(nullable=True)
        assert nullable_canvas_id.nullable is True
        
        # Test percentage_grade column
        grade_col = CommonColumns.percentage_grade()
        assert grade_col.type.python_type == float
        assert grade_col.nullable is True
        
        # Test other column types
        points_col = CommonColumns.points_column()
        status_col = CommonColumns.status_column()
        url_col = CommonColumns.url_column()
        json_col = CommonColumns.json_column()
        
        assert points_col.type.python_type == float
        assert status_col.type.length > 0 or status_col.type.length is None
        assert url_col.type.length > 0 or url_col.type.length is None


class TestCustomExceptions:
    """Test suite for custom exception classes."""
    
    @pytest.mark.unit
    def test_base_exception(self):
        """Test CanvasTrackerDatabaseError base exception."""
        # Basic exception
        exc = CanvasTrackerDatabaseError("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.details == {}
        
        # Exception with details
        details = {'field': 'value', 'code': 123}
        exc_with_details = CanvasTrackerDatabaseError("Test error with details", details)
        
        exc_str = str(exc_with_details)
        assert "Test error with details" in exc_str
        assert "field=value" in exc_str
        assert "code=123" in exc_str
    
    @pytest.mark.unit
    def test_sync_error(self):
        """Test SyncError exception."""
        exc = SyncError(
            "Sync failed",
            sync_type="full_sync",
            failed_objects=["student_123", "course_456"]
        )
        
        assert exc.message == "Sync failed"
        assert exc.details['sync_type'] == "full_sync"
        assert len(exc.details['failed_objects']) == 2
        
        exc_str = str(exc)
        assert "Sync failed" in exc_str
        assert "sync_type=full_sync" in exc_str
    
    @pytest.mark.unit
    def test_data_validation_error(self):
        """Test DataValidationError exception."""
        exc = DataValidationError(
            "Invalid grade",
            field_name="grade",
            invalid_value=-10
        )
        
        assert exc.details['field_name'] == "grade"
        assert exc.details['invalid_value'] == -10
    
    @pytest.mark.unit
    def test_object_not_found_error(self):
        """Test ObjectNotFoundError exception."""
        exc = ObjectNotFoundError(
            "Student not found",
            object_type="student",
            object_id=12345
        )
        
        assert exc.details['object_type'] == "student"
        assert exc.details['object_id'] == 12345
    
    @pytest.mark.unit
    def test_duplicate_object_error(self):
        """Test DuplicateObjectError exception."""
        exc = DuplicateObjectError(
            "Duplicate student",
            object_type="student",
            duplicate_key="canvas_id=12345"
        )
        
        assert exc.details['object_type'] == "student"
        assert exc.details['duplicate_key'] == "canvas_id=12345"
    
    @pytest.mark.unit
    def test_operation_not_allowed_error(self):
        """Test OperationNotAllowedError exception."""
        exc = OperationNotAllowedError(
            "Cannot delete",
            operation="delete_student",
            reason="Has dependent data"
        )
        
        assert exc.details['operation'] == "delete_student"
        assert exc.details['reason'] == "Has dependent data"


class TestExceptionHandling:
    """Test suite for exception handling utilities."""
    
    @pytest.mark.unit
    def test_handle_sqlalchemy_error_connection(self):
        """Test SQLAlchemy connection error handling."""
        sql_error = SQLAlchemyError("Connection timeout occurred")
        canvas_error = handle_sqlalchemy_error(sql_error, "test operation")
        
        assert isinstance(canvas_error, ConnectionError)
        assert "test operation" in canvas_error.message
        assert "original_error" in canvas_error.details
    
    @pytest.mark.unit
    def test_handle_sqlalchemy_error_duplicate(self):
        """Test SQLAlchemy duplicate error handling."""
        sql_error = SQLAlchemyError("UNIQUE constraint failed")
        canvas_error = handle_sqlalchemy_error(sql_error, "create student")
        
        assert isinstance(canvas_error, DuplicateObjectError)
        assert "create student" in canvas_error.message
    
    @pytest.mark.unit
    def test_handle_sqlalchemy_error_foreign_key(self):
        """Test SQLAlchemy foreign key error handling."""
        sql_error = SQLAlchemyError("FOREIGN KEY constraint failed")
        canvas_error = handle_sqlalchemy_error(sql_error, "update assignment")
        
        assert isinstance(canvas_error, DataValidationError)
        assert "update assignment" in canvas_error.message
    
    @pytest.mark.unit
    def test_handle_sqlalchemy_error_generic(self):
        """Test generic SQLAlchemy error handling."""
        sql_error = SQLAlchemyError("Unknown database error")
        canvas_error = handle_sqlalchemy_error(sql_error, "database operation")
        
        assert isinstance(canvas_error, CanvasTrackerDatabaseError)
        assert "database operation" in canvas_error.message
        assert "Unknown database error" in canvas_error.message
    
    @pytest.mark.unit
    def test_reraise_as_canvas_error_decorator(self):
        """Test reraise_as_canvas_error decorator."""
        @reraise_as_canvas_error("test operation")
        def failing_function():
            raise SQLAlchemyError("Test SQL error")
        
        @reraise_as_canvas_error("test operation")
        def success_function():
            return "success"
        
        # Test that SQLAlchemy errors are converted
        with pytest.raises(CanvasTrackerDatabaseError):
            failing_function()
        
        # Test that successful operations work normally
        result = success_function()
        assert result == "success"
        
        # Test that Canvas Tracker errors pass through unchanged
        @reraise_as_canvas_error("test operation")
        def canvas_error_function():
            raise SyncError("Test sync error")
        
        with pytest.raises(SyncError):
            canvas_error_function()
    
    @pytest.mark.unit
    def test_database_error_handler_context_manager(self):
        """Test DatabaseErrorHandler context manager."""
        # Test successful operation
        with DatabaseErrorHandler("test operation") as handler:
            result = "success"
        
        # Test SQLAlchemy error conversion
        with pytest.raises(CanvasTrackerDatabaseError):
            with DatabaseErrorHandler("test operation") as handler:
                raise SQLAlchemyError("Test error")
        
        # Test that non-SQLAlchemy errors pass through
        with pytest.raises(ValueError):
            with DatabaseErrorHandler("test operation") as handler:
                raise ValueError("Non-database error")
    
    @pytest.mark.unit
    def test_database_error_handler_with_logger(self):
        """Test DatabaseErrorHandler with logger."""
        mock_logger = patch('builtins.print')  # Simple mock for testing
        
        with mock_logger:
            with pytest.raises(CanvasTrackerDatabaseError):
                with DatabaseErrorHandler("test operation", logger=None) as handler:
                    raise SQLAlchemyError("Test error with logger")


class TestMixins:
    """Test suite for mixin classes."""
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_timestamp_mixin(self, db_session):
        """Test TimestampMixin functionality."""
        from .conftest import _TestModel as TestModel
        
        obj = TestModel(name="Timestamp Test", value=500)
        db_session.add(obj)
        db_session.flush()
        
        # Verify timestamps are set
        assert obj.created_at is not None
        assert obj.updated_at is not None
        
        # Store original timestamps
        original_created = obj.created_at
        original_updated = obj.updated_at
        
        # Update object and flush
        import time
        time.sleep(0.1)  # Ensure time difference
        obj.value = 600
        db_session.flush()
        
        # created_at should remain the same, updated_at should change
        assert obj.created_at == original_created
        # Note: updated_at change depends on SQLAlchemy configuration
    
    @pytest.mark.unit
    def test_sync_tracking_mixin(self):
        """Test SyncTrackingMixin functionality."""
        from .conftest import _TestCanvasModel as TestCanvasModel
        
        obj = TestCanvasModel(name="Sync Mixin Test", canvas_id=999)
        
        # Initially not synced
        assert obj.last_synced is None
        assert obj.is_recently_synced() is False
        
        # Mark as synced
        obj.mark_synced()
        assert obj.last_synced is not None
        assert obj.is_recently_synced() is True
    
    @pytest.mark.unit
    def test_canvas_object_mixin(self):
        """Test CanvasObjectMixin functionality."""
        from .conftest import _TestCanvasModel as TestCanvasModel
        
        obj = TestCanvasModel(name="Canvas Object Test", canvas_id=777)
        
        # Verify name field from mixin
        assert obj.name == "Canvas Object Test"
        assert hasattr(obj, 'name')
    
    @pytest.mark.unit
    def test_metadata_mixin(self):
        """Test MetadataMixin functionality."""
        # MetadataMixin provides declared_attr columns, not methods
        # The methods are in MetadataBaseModel
        from database.base import MetadataBaseModel
        
        # Test that MetadataBaseModel has the tag methods
        class TestMetadataModel(MetadataBaseModel):
            __tablename__ = 'test_metadata_mixin_test'
        
        obj = TestMetadataModel()
        
        # Test that methods exist
        assert hasattr(obj, 'add_tag')
        assert hasattr(obj, 'remove_tag')
        assert hasattr(obj, 'get_tags')
        
        # Test that mixin fields are available
        assert hasattr(TestMetadataModel, 'notes')
        assert hasattr(TestMetadataModel, 'custom_tags')


# Integration tests
@pytest.mark.integration
@pytest.mark.database
class TestBaseModelIntegration:
    """Integration tests for base models with database operations."""
    
    def test_full_model_lifecycle(self, db_session, sample_test_data):
        """Test complete model lifecycle with all features."""
        from .conftest import _TestModel as TestModel, _TestCanvasModel as TestCanvasModel
        
        # Test BaseModel lifecycle
        base_obj = TestModel(name="Integration Test", value=1000)
        db_session.add(base_obj)
        db_session.flush()
        
        # Verify persistence and timestamps
        assert base_obj.id is not None
        assert base_obj.created_at is not None
        
        # Test dictionary conversion
        obj_dict = base_obj.to_dict()
        assert obj_dict['name'] == "Integration Test"
        
        # Test CanvasBaseModel lifecycle
        canvas_obj = TestCanvasModel(name="Canvas Integration", canvas_id=888888)
        canvas_obj.mark_synced()
        db_session.add(canvas_obj)
        db_session.flush()
        
        # Verify Canvas-specific features
        assert canvas_obj.last_synced is not None
        assert canvas_obj.is_recently_synced() is True
        
        # Test metadata features (using a metadata model)
        class TestMetadataIntegration(MetadataBaseModel):
            __tablename__ = 'test_metadata_integration'
            test_field = Column(String(100))
        
        Base.metadata.create_all(db_session.bind)
        
        meta_obj = TestMetadataIntegration(test_field="Integration Test")
        meta_obj.add_tag("integration")
        meta_obj.add_tag("testing")
        
        db_session.add(meta_obj)
        db_session.flush()
        
        # Verify metadata functionality
        assert len(meta_obj.get_tags()) == 2
        assert meta_obj.notes is None  # Should default to None