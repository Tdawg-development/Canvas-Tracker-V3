"""
Comprehensive Test Suite for Canvas-Database Integration Layer

Tests for the new integration components to ensure they work correctly
and maintain proper architectural boundaries:
- canvas_bridge.py
- data_transformers.py  
- typescript_interface.py
"""

import pytest
import json
import tempfile
import subprocess
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, Any, List

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

# Import components that actually exist
try:
    from database.operations.canvas_bridge import CanvasDataBridge, CanvasBridgeResult
except ImportError:
    CanvasDataBridge = None
    CanvasBridgeResult = None

try:
    from database.operations.data_transformers import CanvasDataTransformer
except ImportError:
    CanvasDataTransformer = None

try:
    from database.operations.typescript_interface import TypeScriptExecutor, TypeScriptExecutionError
except ImportError:
    TypeScriptExecutor = None
    TypeScriptExecutionError = Exception

from database.base import Base
from database.config import DatabaseConfig
from database.session import DatabaseManager

# Test fixtures and sample data
@pytest.fixture
def db_session():
    """Create an in-memory test database session."""
    config = DatabaseConfig('test')
    db_manager = DatabaseManager(config)
    
    # Create all tables
    Base.metadata.create_all(db_manager.engine)
    
    with db_manager.session_scope() as session:
        yield session
    
    # Cleanup
    Base.metadata.drop_all(db_manager.engine)
    db_manager.close()


@pytest.fixture
def sample_canvas_course_data():
    """Sample Canvas course data for testing."""
    return {
        "id": 7982015,
        "name": "CS 101: Introduction to Computer Science",
        "course_code": "CS101-F23",
        "workflow_state": "available",
        "calendar": {
            "ics": "https://canvas.example.edu/feeds/calendars/course_abc123.ics"
        },
        "created_at": "2023-08-15T10:00:00Z",
        "updated_at": "2023-10-14T15:30:00Z",
        "students": [
            {
                "id": 12345,
                "user_id": 12345,
                "name": "Alice Johnson",
                "login_id": "alice.johnson@university.edu",
                "current_score": 85,
                "final_score": 90,
                "enrollment_state": "active",
                "created_at": "2023-08-20T09:00:00Z",
                "updated_at": "2023-10-14T14:00:00Z",
                "user": {
                    "id": 12345,
                    "name": "Alice Johnson",
                    "login_id": "alice.johnson@university.edu"
                }
            }
        ],
        "modules": [
            {
                "id": 1001,
                "name": "Week 1: Programming Fundamentals",
                "position": 1,
                "published": True,
                "workflow_state": "available",
                "created_at": "2023-08-15T11:00:00Z",
                "updated_at": "2023-08-16T12:00:00Z",
                "items": [
                    {
                        "id": 2001,
                        "title": "Assignment 1: Hello World",
                        "type": "Assignment",
                        "position": 1,
                        "published": True,
                        "url": "https://canvas.example.edu/api/v1/courses/7982015/assignments/3001",
                        "content_details": {
                            "points_possible": 10
                        },
                        "created_at": "2023-08-15T12:00:00Z",
                        "updated_at": "2023-08-15T13:00:00Z"
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_typescript_executor():
    """Mock TypeScript executor for testing."""
    mock = Mock(spec=TypeScriptExecutor)
    return mock


@pytest.fixture
def mock_data_transformer():
    """Mock data transformer for testing."""
    mock = Mock(spec=CanvasDataTransformer)
    return mock


# ==================== TYPESCRIPT INTERFACE TESTS ====================

@pytest.mark.skipif(TypeScriptExecutor is None, reason="TypeScriptExecutor not available")
class TestTypeScriptExecutor:
    """Test TypeScript execution and interface components."""
    
    def test_typescript_executor_initialization(self, tmp_path):
        """Test TypeScript executor initialization."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        executor = TypeScriptExecutor(str(canvas_path))
        
        assert executor.canvas_interface_path == canvas_path
        assert executor.timeout == 300  # Default timeout
        assert executor.retry_attempts == 3  # Default retries
    
    def test_typescript_executor_path_validation(self):
        """Test path validation for TypeScript executor."""
        with pytest.raises(FileNotFoundError):
            TypeScriptExecutor("/nonexistent/path")
    
    @patch('subprocess.run')
    def test_execute_course_data_constructor_success(self, mock_subprocess, tmp_path, sample_canvas_course_data):
        """Test successful TypeScript execution."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Mock successful subprocess execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sample_canvas_course_data)
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        executor = TypeScriptExecutor(str(canvas_path))
        result = executor.execute_course_data_constructor(7982015)
        
        assert result == sample_canvas_course_data
        mock_subprocess.assert_called_once()
    
    @patch('subprocess.run')
    def test_execute_course_data_constructor_failure(self, mock_subprocess, tmp_path):
        """Test TypeScript execution failure handling."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Mock failed subprocess execution
        mock_result = Mock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "TypeScript compilation error"
        mock_subprocess.return_value = mock_result
        
        executor = TypeScriptExecutor(str(canvas_path))
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            executor.execute_course_data_constructor(7982015)
        
        assert "TypeScript compilation error" in str(exc_info.value)
    
    @patch('subprocess.run')
    def test_execute_with_retry_logic(self, mock_subprocess, tmp_path):
        """Test retry logic for failed executions."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Mock subprocess that fails twice then succeeds
        mock_results = [
            Mock(returncode=1, stdout="", stderr="Network error"),
            Mock(returncode=1, stdout="", stderr="Network error"),
            Mock(returncode=0, stdout='{"success": true}', stderr="")
        ]
        mock_subprocess.side_effect = mock_results
        
        executor = TypeScriptExecutor(str(canvas_path), retry_attempts=3)
        result = executor.execute_course_data_constructor(7982015)
        
        assert result == {"success": True}
        assert mock_subprocess.call_count == 3


# ==================== DATA TRANSFORMER TESTS ====================

@pytest.mark.skipif(CanvasDataTransformer is None, reason="CanvasDataTransformer not available")
class TestCanvasDataTransformer:
    """Test data transformation components."""
    
    def test_transformer_initialization(self):
        """Test data transformer initialization."""
        transformer = CanvasDataTransformer()
        
        assert transformer is not None
        assert hasattr(transformer, 'transform_canvas_staging_data')
    
    def test_transform_canvas_staging_data_structure(self, sample_canvas_course_data):
        """Test basic data structure transformation."""
        transformer = CanvasDataTransformer()
        
        result = transformer.transform_canvas_staging_data(sample_canvas_course_data)
        
        # Check that result has required database structure
        assert 'course' in result
        assert 'students' in result
        assert 'assignments' in result
        assert 'enrollments' in result
        
        # Verify course data transformation
        course_data = result['course']
        assert course_data['id'] == 7982015
        assert course_data['name'] == "CS 101: Introduction to Computer Science"
        assert 'created_at' in course_data
        assert 'updated_at' in course_data
    
    def test_transform_timestamp_handling(self, sample_canvas_course_data):
        """Test proper timestamp transformation."""
        transformer = CanvasDataTransformer()
        
        result = transformer.transform_canvas_staging_data(sample_canvas_course_data)
        
        # Check timestamp formats are preserved
        course_data = result['course']
        assert isinstance(course_data['created_at'], (str, datetime))
        assert isinstance(course_data['updated_at'], (str, datetime))
    
    def test_transform_student_data(self, sample_canvas_course_data):
        """Test student data transformation."""
        transformer = CanvasDataTransformer()
        
        result = transformer.transform_canvas_staging_data(sample_canvas_course_data)
        
        students = result['students']
        assert len(students) == 1
        
        student = students[0]
        assert student['student_id'] == 12345
        assert student['name'] == "Alice Johnson"
        assert student['current_score'] == 85
        assert student['final_score'] == 90
        assert student['enrollment_state'] == "active"
    
    def test_transform_assignment_data(self, sample_canvas_course_data):
        """Test assignment data transformation."""
        transformer = CanvasDataTransformer()
        
        result = transformer.transform_canvas_staging_data(sample_canvas_course_data)
        
        assignments = result['assignments']
        assert len(assignments) > 0
        
        assignment = assignments[0]
        assert 'id' in assignment
        assert 'name' in assignment
        assert 'points_possible' in assignment
        assert 'course_id' in assignment
    
    def test_transform_error_handling(self):
        """Test error handling for invalid data."""
        transformer = CanvasDataTransformer()
        
        # Test with invalid data structure
        invalid_data = {"invalid": "structure"}
        
        with pytest.raises(Exception):  # Should raise appropriate exception
            transformer.transform_canvas_staging_data(invalid_data)


# ==================== CANVAS BRIDGE TESTS ====================

@pytest.mark.skipif(CanvasDataBridge is None, reason="CanvasDataBridge not available")
class TestCanvasDataBridge:
    """Test Canvas-Database integration bridge."""
    
    def test_bridge_initialization(self, tmp_path, db_session):
        """Test Canvas bridge initialization."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        assert bridge.canvas_path == canvas_path
        assert bridge.session == db_session
        assert hasattr(bridge, 'typescript_executor')
        assert hasattr(bridge, 'data_transformer')
    
    def test_validate_input(self, tmp_path, db_session):
        """Test input validation."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        # Valid course ID should pass
        assert bridge.validate_input(course_id=7982015) == True
        
        # Invalid course ID should fail
        with pytest.raises(Exception):  # Should raise ValidationError
            bridge.validate_input(course_id=None)
    
    @patch.object(CanvasDataBridge, '_detect_canvas_interface_path')
    def test_auto_detect_path(self, mock_detect, db_session):
        """Test automatic path detection."""
        mock_detect.return_value = Path("/detected/path")
        
        bridge = CanvasDataBridge("/nonexistent", db_session, auto_detect_path=True)
        
        mock_detect.assert_called_once()
        assert bridge.canvas_path == Path("/detected/path")
    
    @patch.object(CanvasDataTransformer, 'transform_canvas_staging_data')
    @patch.object(TypeScriptExecutor, 'execute_course_data_constructor')
    def test_initialize_canvas_course_sync_success(
        self, 
        mock_ts_executor, 
        mock_transformer,
        tmp_path,
        db_session,
        sample_canvas_course_data
    ):
        """Test successful course sync initialization."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Setup mocks
        mock_ts_executor.return_value = sample_canvas_course_data
        mock_transformer.return_value = {
            'course': sample_canvas_course_data,
            'students': [],
            'assignments': [],
            'enrollments': []
        }
        
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        # Execute the sync
        result = bridge.initialize_canvas_course_sync(7982015)
        
        # Verify result structure
        assert isinstance(result, CanvasBridgeResult)
        assert result.course_id == 7982015
        assert result.typescript_execution_time is not None
        assert result.data_transformation_time is not None
        
        # Verify mocks were called
        mock_ts_executor.assert_called_once_with(7982015)
        mock_transformer.assert_called_once()
    
    def test_bridge_result_properties(self):
        """Test CanvasBridgeResult properties and methods."""
        result = CanvasBridgeResult(
            success=True,
            course_id=7982015,
            typescript_execution_time=1.5,
            data_transformation_time=0.3,
            database_sync_time=2.1,
            total_time=3.9,
            objects_synced={'courses': 1, 'students': 25, 'assignments': 15},
            sync_result=None,
            errors=[],
            warnings=[]
        )
        
        assert result.ready_for_frontend == True  # Has courses synced
        assert result.success == True
        assert result.course_id == 7982015


# ==================== INTEGRATION TESTS ====================

class TestIntegrationLayerIntegration:
    """Test integration between all components."""
    
    @patch('subprocess.run')
    def test_full_integration_flow(
        self, 
        mock_subprocess,
        tmp_path,
        db_session,
        sample_canvas_course_data
    ):
        """Test complete integration flow from TypeScript to database."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Mock successful TypeScript execution
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(sample_canvas_course_data)
        mock_result.stderr = ""
        mock_subprocess.return_value = mock_result
        
        # Create bridge and execute sync
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        result = bridge.initialize_canvas_course_sync(7982015)
        
        # Verify end-to-end success
        assert isinstance(result, CanvasBridgeResult)
        assert result.course_id == 7982015
        assert len(result.errors) == 0
    
    def test_architectural_boundary_compliance(self, tmp_path, db_session):
        """Test that components respect architectural boundaries."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Create components
        executor = TypeScriptExecutor(str(canvas_path))
        transformer = CanvasDataTransformer()
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        # Verify no direct file system operations in production components
        # (This is a design test - components should not have fs operations)
        
        # TypeScript executor should only execute subprocess, not write files
        assert not hasattr(executor, 'writeFile')
        assert not hasattr(executor, 'writeFileSync')
        
        # Data transformer should be pure data transformation
        assert not hasattr(transformer, 'writeFile')
        assert not hasattr(transformer, 'fs')
        
        # Bridge should coordinate but not do direct file I/O
        assert not hasattr(bridge, 'writeFile')
    
    def test_error_propagation_and_handling(self, tmp_path, db_session):
        """Test error handling across integration components."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        # Test with invalid course ID - should handle gracefully
        with patch.object(bridge.typescript_executor, 'execute_course_data_constructor') as mock_executor:
            mock_executor.side_effect = TypeScriptExecutionError("Canvas API error")
            
            result = bridge.initialize_canvas_course_sync(7982015)
            
            assert result.success == False
            assert len(result.errors) > 0
            assert "Canvas API error" in result.errors[0]
    
    def test_transaction_safety(self, tmp_path, db_session):
        """Test that database operations are transaction-safe."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        bridge = CanvasDataBridge(str(canvas_path), db_session)
        
        # Verify bridge has transaction manager
        assert hasattr(bridge, 'transaction_manager')
        assert bridge.transaction_manager is not None
        
        # This would require more complex setup to fully test transactions,
        # but we can verify the components are present
        assert hasattr(bridge, 'session')


# ==================== PERFORMANCE AND SCALABILITY TESTS ====================

class TestIntegrationLayerPerformance:
    """Test performance characteristics of integration layer."""
    
    def test_typescript_execution_timeout(self, tmp_path):
        """Test TypeScript execution timeout handling."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # Create executor with short timeout
        executor = TypeScriptExecutor(str(canvas_path), timeout=1)
        
        with patch('subprocess.run') as mock_subprocess:
            # Mock subprocess that hangs
            mock_subprocess.side_effect = subprocess.TimeoutExpired("node", 1)
            
            with pytest.raises(TypeScriptExecutionError) as exc_info:
                executor.execute_course_data_constructor(7982015)
            
            assert "timeout" in str(exc_info.value).lower()
    
    def test_large_dataset_handling(self, sample_canvas_course_data):
        """Test handling of large datasets."""
        transformer = CanvasDataTransformer()
        
        # Create large dataset
        large_data = sample_canvas_course_data.copy()
        large_data['students'] = [sample_canvas_course_data['students'][0].copy() for _ in range(1000)]
        
        # Should handle without errors
        result = transformer.transform_canvas_staging_data(large_data)
        assert len(result['students']) == 1000
    
    def test_concurrent_operations(self, tmp_path, db_session):
        """Test concurrent integration operations."""
        canvas_path = tmp_path / "canvas-interface"
        canvas_path.mkdir()
        
        # This would require threading/async testing setup
        # For now, verify components can be created independently
        bridge1 = CanvasDataBridge(str(canvas_path), db_session)
        bridge2 = CanvasDataBridge(str(canvas_path), db_session)
        
        assert bridge1 != bridge2
        assert bridge1.canvas_path == bridge2.canvas_path


# ==================== CONFIGURATION AND SETUP TESTS ====================

if __name__ == '__main__':
    """Run tests with pytest."""
    pytest.main([__file__, '-v', '--tb=short'])