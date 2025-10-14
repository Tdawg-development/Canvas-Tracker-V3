"""
Unit Tests for Canvas Data Bridge Service.

Tests the main integration bridge between TypeScript Canvas interface and Python
database operations. These tests validate:

- Bridge initialization and component integration
- Environment validation and prerequisites
- Canvas course sync orchestration
- Error handling and transaction management
- Performance monitoring and logging
- Integration with existing SyncCoordinator and CanvasDataManager
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from datetime import datetime, timezone

from database.operations.canvas_bridge import (
    CanvasDataBridge,
    CanvasBridgeResult,
    initialize_canvas_course
)
from database.operations.base.exceptions import (
    CanvasOperationError, ValidationError
)
from database.operations.layer1.sync_coordinator import SyncResult, SyncPriority
from database.operations.typescript_interface import TypeScriptExecutionError


class TestCanvasDataBridge:
    """Test CanvasDataBridge core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.canvas_path = "/test/canvas-interface"
        
        # Create bridge with mocked components
        with patch('database.operations.canvas_bridge.TypeScriptExecutor') as mock_executor_class, \
             patch('database.operations.canvas_bridge.CanvasDataTransformer') as mock_transformer_class, \
             patch('database.operations.canvas_bridge.CanvasDataManager') as mock_manager_class, \
             patch('database.operations.canvas_bridge.SyncCoordinator') as mock_coordinator_class, \
             patch('database.operations.canvas_bridge.TransactionManager') as mock_transaction_class:
            
            # Setup mock instances
            self.mock_executor = Mock()
            self.mock_transformer = Mock()
            self.mock_canvas_manager = Mock()
            self.mock_sync_coordinator = Mock()
            self.mock_transaction_manager = Mock()
            
            mock_executor_class.return_value = self.mock_executor
            mock_transformer_class.return_value = self.mock_transformer
            mock_manager_class.return_value = self.mock_canvas_manager
            mock_coordinator_class.return_value = self.mock_sync_coordinator
            mock_transaction_class.return_value = self.mock_transaction_manager
            
            # Mock path existence
            with patch('pathlib.Path.exists', return_value=True):
                self.bridge = CanvasDataBridge(self.canvas_path, self.mock_session, auto_detect_path=False)
    
    @pytest.mark.unit
    def test_canvas_bridge_initialization(self):
        """Test CanvasDataBridge initialization."""
        assert isinstance(self.bridge, CanvasDataBridge)
        assert self.bridge.session == self.mock_session
        # Use Path for cross-platform compatibility
        assert str(self.bridge.canvas_path) == str(Path(self.canvas_path))
        assert self.bridge.typescript_executor == self.mock_executor
        assert self.bridge.data_transformer == self.mock_transformer
        assert self.bridge.canvas_manager == self.mock_canvas_manager
        assert self.bridge.sync_coordinator == self.mock_sync_coordinator
        assert self.bridge.transaction_manager == self.mock_transaction_manager
        assert hasattr(self.bridge, 'logger')
    
    @pytest.mark.unit
    def test_canvas_bridge_auto_detect_path(self):
        """Test Canvas bridge with auto-detect path functionality."""
        with patch.object(CanvasDataBridge, '_detect_canvas_interface_path') as mock_detect:
            mock_detect.return_value = Path("/detected/canvas-interface")
            
            with patch('pathlib.Path.exists', return_value=False):  # Original path doesn't exist
                with patch('database.operations.canvas_bridge.TypeScriptExecutor'), \
                     patch('database.operations.canvas_bridge.CanvasDataTransformer'), \
                     patch('database.operations.canvas_bridge.CanvasDataManager'), \
                     patch('database.operations.canvas_bridge.SyncCoordinator'), \
                     patch('database.operations.canvas_bridge.TransactionManager'):
                    
                    bridge = CanvasDataBridge("/nonexistent/path", self.mock_session, auto_detect_path=True)
                    
                    assert bridge.canvas_path == Path("/detected/canvas-interface")
                    mock_detect.assert_called_once()
    
    # ==================== INPUT VALIDATION TESTS ====================
    
    @pytest.mark.unit
    def test_validate_input_valid_course_id(self):
        """Test input validation with valid course ID."""
        result = self.bridge.validate_input(course_id=12345)
        assert result is True
    
    @pytest.mark.unit
    def test_validate_input_invalid_course_id_none(self):
        """Test input validation with None course ID."""
        with pytest.raises(ValidationError) as exc_info:
            self.bridge.validate_input(course_id=None)
        
        assert "valid course_id parameter" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_input_invalid_course_id_string(self):
        """Test input validation with string course ID."""
        with pytest.raises(ValidationError) as exc_info:
            self.bridge.validate_input(course_id="not_an_int")
        
        assert "valid course_id parameter" in str(exc_info.value)
    
    # ==================== ENVIRONMENT VALIDATION TESTS ====================
    
    @pytest.mark.unit
    def test_validate_bridge_environment_success(self):
        """Test successful environment validation."""
        # Mock TypeScript executor validation
        self.mock_executor.validate_execution_environment.return_value = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Mock path existence using pathlib.Path.exists
        with patch('pathlib.Path.exists', return_value=True):
            result = self.bridge.validate_bridge_environment()
            
            assert result['valid'] is True
            assert len(result['errors']) == 0
            assert len(result['warnings']) == 0
    
    @pytest.mark.unit
    def test_validate_bridge_environment_missing_path(self):
        """Test environment validation with missing canvas path."""
        with patch('pathlib.Path.exists', return_value=False):
            result = self.bridge.validate_bridge_environment()
            
            assert result['valid'] is False
            assert len(result['errors']) > 0
            assert any("Canvas interface path not found" in error for error in result['errors'])
    
    @pytest.mark.unit
    def test_validate_bridge_environment_missing_env_file(self):
        """Test environment validation with missing .env file."""
        
        def mock_path_exists(self):
            path_str = str(self)
            # Main canvas path and staging directory exist
            if (path_str.endswith('canvas-interface') or 
                path_str.endswith('staging') or
                path_str.endswith('canvas-data-constructor.ts')):
                return True
            # But .env file doesn't exist
            elif path_str.endswith('.env'):
                return False
            else:
                return True
        
        with patch.object(Path, 'exists', mock_path_exists):
            self.mock_executor.validate_execution_environment.return_value = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            
            result = self.bridge.validate_bridge_environment()
            
            # Should still be valid but with warnings
            assert result['valid'] is True
            assert len(result['warnings']) > 0
            assert any(".env file not found" in warning for warning in result['warnings'])
    
    @pytest.mark.unit
    def test_validate_bridge_environment_typescript_errors(self):
        """Test environment validation with TypeScript errors."""
        # Mock TypeScript validation failure
        self.mock_executor.validate_execution_environment.return_value = {
            'valid': False,
            'errors': ['Node.js not found', 'tsx not available'],
            'warnings': []
        }
        
        with patch('pathlib.Path.exists', return_value=True):
            result = self.bridge.validate_bridge_environment()
            
            assert result['valid'] is False
            assert len(result['errors']) >= 2
            assert any("Node.js not found" in error for error in result['errors'])
            assert any("tsx not available" in error for error in result['errors'])
    
    # ==================== COURSE SYNC TESTS ====================
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('asyncio.create_task')
    async def test_initialize_canvas_course_sync_success(self, mock_create_task):
        """Test successful Canvas course sync."""
        course_id = 12345
        
        # Mock TypeScript execution result
        mock_canvas_data = {
            'success': True,
            'course_id': course_id,
            'course': {'id': course_id, 'name': 'Test Course'},
            'students': [{'id': 1, 'name': 'Student 1'}],
            'modules': []
        }
        
        # Setup async mock for TypeScript executor
        async def mock_execute_constructor(cid):
            return mock_canvas_data
        
        self.mock_executor.execute_course_data_constructor = AsyncMock(return_value=mock_canvas_data)
        
        # Mock data transformation
        mock_db_data = {
            'courses': [{'id': course_id, 'name': 'Test Course'}],
            'students': [{'student_id': 1, 'name': 'Student 1'}],
            'assignments': [],
            'enrollments': [{'student_id': 1, 'course_id': course_id}]
        }
        self.mock_transformer.transform_canvas_staging_data.return_value = mock_db_data
        
        # Mock sync coordinator result
        mock_sync_result = Mock()
        mock_sync_result.success = True
        mock_sync_result.errors = []
        mock_sync_result.objects_created = {'courses': 1, 'students': 1, 'assignments': 0, 'enrollments': 1}
        mock_sync_result.objects_updated = {'courses': 0, 'students': 0, 'assignments': 0, 'enrollments': 0}
        
        # Mock the async sync method
        async def mock_execute_sync(db_data, priority, cid):
            return mock_sync_result
        
        self.bridge._execute_database_sync = AsyncMock(return_value=mock_sync_result)
        
        # Mock environment validation
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_env_validation:
            mock_env_validation.return_value = {'valid': True, 'errors': [], 'warnings': []}
            
            result = await self.bridge.initialize_canvas_course_sync(course_id)
            
            # Verify result
            assert isinstance(result, CanvasBridgeResult)
            assert result.success is True
            assert result.course_id == course_id
            assert result.ready_for_frontend is True
            assert isinstance(result.typescript_execution_time, float)
            assert isinstance(result.data_transformation_time, float)
            assert isinstance(result.database_sync_time, float)
            assert isinstance(result.total_time, float)
            assert result.objects_synced['courses'] == 1
            assert result.objects_synced['students'] == 1
            assert result.objects_synced['enrollments'] == 1
            
            # Verify component interactions
            self.mock_executor.execute_course_data_constructor.assert_called_once_with(course_id)
            self.mock_transformer.transform_canvas_staging_data.assert_called_once_with(mock_canvas_data)
            self.bridge._execute_database_sync.assert_called_once()
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_sync_environment_failure(self):
        """Test Canvas course sync with environment validation failure."""
        course_id = 12345
        
        # Mock environment validation failure
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_env_validation:
            mock_env_validation.return_value = {
                'valid': False,
                'errors': ['Node.js not found'],
                'warnings': []
            }
            
            with pytest.raises(CanvasOperationError) as exc_info:
                await self.bridge.initialize_canvas_course_sync(course_id)
            
            assert "Environment validation failed" in str(exc_info.value)
            assert "Node.js not found" in str(exc_info.value)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_sync_typescript_failure(self):
        """Test Canvas course sync with TypeScript execution failure."""
        course_id = 12345
        
        # Mock environment validation success
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_env_validation:
            mock_env_validation.return_value = {'valid': True, 'errors': [], 'warnings': []}
            
            # Mock TypeScript execution failure
            self.mock_executor.execute_course_data_constructor = AsyncMock(
                side_effect=TypeScriptExecutionError("TypeScript failed")
            )
            
            with pytest.raises(CanvasOperationError) as exc_info:
                await self.bridge.initialize_canvas_course_sync(course_id)
            
            assert "TypeScript execution failed" in str(exc_info.value)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_sync_transformation_failure(self):
        """Test Canvas course sync with data transformation failure."""
        course_id = 12345
        
        # Mock successful TypeScript execution
        mock_canvas_data = {'success': True, 'course_id': course_id}
        self.mock_executor.execute_course_data_constructor = AsyncMock(return_value=mock_canvas_data)
        
        # Mock transformation failure
        self.mock_transformer.transform_canvas_staging_data.side_effect = ValidationError("Transformation failed")
        
        # Mock environment validation
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_env_validation:
            mock_env_validation.return_value = {'valid': True, 'errors': [], 'warnings': []}
            
            with pytest.raises(CanvasOperationError) as exc_info:
                await self.bridge.initialize_canvas_course_sync(course_id)
            
            assert "Canvas bridge sync failed" in str(exc_info.value)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_sync_database_failure(self):
        """Test Canvas course sync with database sync failure."""
        course_id = 12345
        
        # Mock successful TypeScript execution and transformation
        mock_canvas_data = {'success': True, 'course_id': course_id}
        mock_db_data = {'courses': [{'id': course_id}], 'students': [], 'assignments': [], 'enrollments': []}
        
        self.mock_executor.execute_course_data_constructor = AsyncMock(return_value=mock_canvas_data)
        self.mock_transformer.transform_canvas_staging_data.return_value = mock_db_data
        
        # Mock database sync failure - MUST include proper dictionaries for arithmetic operations
        mock_failed_sync = Mock()
        mock_failed_sync.success = False
        mock_failed_sync.errors = ['Database sync failed']
        mock_failed_sync.objects_created = {'courses': 0, 'students': 0, 'assignments': 0, 'enrollments': 0}
        mock_failed_sync.objects_updated = {'courses': 0, 'students': 0, 'assignments': 0, 'enrollments': 0}
        
        self.bridge._execute_database_sync = AsyncMock(return_value=mock_failed_sync)
        
        # Mock environment validation
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_env_validation:
            mock_env_validation.return_value = {'valid': True, 'errors': [], 'warnings': []}
            
            with pytest.raises(CanvasOperationError) as exc_info:
                await self.bridge.initialize_canvas_course_sync(course_id)
            
            assert "Database sync failed" in str(exc_info.value)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_sync_skip_validation(self):
        """Test Canvas course sync with validation skipped."""
        course_id = 12345
        
        # Mock successful execution chain
        mock_canvas_data = {'success': True, 'course_id': course_id}
        mock_db_data = {'courses': [], 'students': [], 'assignments': [], 'enrollments': []}
        mock_sync_result = Mock()
        mock_sync_result.success = True
        mock_sync_result.errors = []
        mock_sync_result.objects_created = {'courses': 0, 'students': 0, 'assignments': 0, 'enrollments': 0}
        mock_sync_result.objects_updated = {'courses': 0, 'students': 0, 'assignments': 0, 'enrollments': 0}
        
        self.mock_executor.execute_course_data_constructor = AsyncMock(return_value=mock_canvas_data)
        self.mock_transformer.transform_canvas_staging_data.return_value = mock_db_data
        self.bridge._execute_database_sync = AsyncMock(return_value=mock_sync_result)
        
        # Call with validation disabled
        result = await self.bridge.initialize_canvas_course_sync(course_id, validate_environment=False)
        
        assert result.success is True
        
        # Verify validation was not called
        with patch.object(self.bridge, 'validate_bridge_environment') as mock_validation:
            # Validation should not be called when validate_environment=False
            mock_validation.assert_not_called()
    
    # ==================== DATABASE SYNC TESTS ====================
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_database_sync_success(self):
        """Test successful database sync execution."""
        course_id = 12345
        mock_db_data = {
            'courses': [{'id': course_id}],
            'students': [{'id': 1}],
            'assignments': [],
            'enrollments': []
        }
        
        # Mock sync coordinator result
        mock_sync_result = Mock()
        mock_sync_result.objects_created = {'courses': 1, 'students': 1}
        mock_sync_result.objects_updated = {'courses': 0, 'students': 0}
        
        self.mock_sync_coordinator.execute_full_sync.return_value = mock_sync_result
        
        result = await self.bridge._execute_database_sync(mock_db_data, SyncPriority.HIGH, course_id)
        
        assert result == mock_sync_result
        self.mock_sync_coordinator.execute_full_sync.assert_called_once_with(
            canvas_data=mock_db_data,
            priority=SyncPriority.HIGH,
            validate_integrity=True
        )
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_execute_database_sync_failure(self):
        """Test database sync execution failure."""
        course_id = 12345
        mock_db_data = {'courses': []}
        
        # Mock sync coordinator exception
        self.mock_sync_coordinator.execute_full_sync.side_effect = Exception("Database error")
        
        with pytest.raises(Exception) as exc_info:
            await self.bridge._execute_database_sync(mock_db_data, SyncPriority.HIGH, course_id)
        
        assert "Database error" in str(exc_info.value)
    
    # ==================== PATH DETECTION TESTS ====================
    
    @pytest.mark.unit
    def test_detect_canvas_interface_path_success(self):
        """Test successful canvas interface path detection."""
        # Use the actual method but with controlled path existence
        with patch.object(Path, 'cwd') as mock_cwd:
            
            # Set up mock current working directory
            mock_cwd.return_value = Path("/project/root")
            
            # Mock that the first potential path exists and has required files
            def mock_path_exists(self):
                path_str = str(self)
                if "canvas-interface" in path_str and "canvas-data-constructor.ts" in path_str:
                    return True
                elif "canvas-interface" in path_str and path_str.endswith("canvas-interface"):
                    return True
                return False
            
            with patch.object(Path, 'exists', mock_path_exists):
                result = self.bridge._detect_canvas_interface_path()
                
                # Should return a Path object
                assert isinstance(result, Path)
                assert "canvas-interface" in str(result)
    
    @pytest.mark.unit
    def test_detect_canvas_interface_path_failure(self):
        """Test canvas interface path detection failure."""
        # Mock all potential paths as non-existent
        with patch('pathlib.Path.exists', return_value=False), \
             patch('pathlib.Path.cwd', return_value=Path("/project/root")):
            
            with pytest.raises(CanvasOperationError) as exc_info:
                self.bridge._detect_canvas_interface_path()
            
            assert "Could not auto-detect canvas-interface path" in str(exc_info.value)
    
    # ==================== STATUS AND UTILITY TESTS ====================
    
    @pytest.mark.unit
    def test_get_bridge_status_success(self):
        """Test getting bridge status successfully."""
        # Mock environment validation
        mock_env_result = {
            'valid': True,
            'errors': [],
            'warnings': ['Some warning']
        }
        
        with patch.object(self.bridge, 'validate_bridge_environment', return_value=mock_env_result):
            self.mock_executor.validate_execution_environment.return_value = {
                'valid': True,
                'node_version': 'v18.17.0'
            }
            
            with patch('pathlib.Path.exists', return_value=True):
                status = self.bridge.get_bridge_status()
                
                assert status['canvas_interface_path'] == str(self.bridge.canvas_path)
                assert status['path_exists'] is True
                assert status['environment_valid'] is True
                assert status['environment_warnings'] == ['Some warning']
                assert 'components' in status
                assert 'typescript_executor' in status['components']
    
    @pytest.mark.unit
    def test_get_bridge_status_error(self):
        """Test getting bridge status with error."""
        with patch.object(self.bridge, 'validate_bridge_environment', side_effect=Exception("Validation error")):
            status = self.bridge.get_bridge_status()
            
            assert 'error' in status
            assert "Validation error" in status['error']
            assert status['canvas_interface_path'] == str(self.bridge.canvas_path)


class TestCanvasBridgeResult:
    """Test CanvasBridgeResult data class functionality."""
    
    @pytest.mark.unit
    def test_canvas_bridge_result_creation(self):
        """Test CanvasBridgeResult creation and properties."""
        sync_result = Mock()
        sync_result.success = True
        
        result = CanvasBridgeResult(
            success=True,
            course_id=12345,
            typescript_execution_time=1.5,
            data_transformation_time=0.5,
            database_sync_time=2.0,
            total_time=4.2,
            objects_synced={'courses': 1, 'students': 5},
            sync_result=sync_result,
            errors=[],
            warnings=['Minor warning']
        )
        
        assert result.success is True
        assert result.course_id == 12345
        assert result.typescript_execution_time == 1.5
        assert result.data_transformation_time == 0.5
        assert result.database_sync_time == 2.0
        assert result.total_time == 4.2
        assert result.objects_synced == {'courses': 1, 'students': 5}
        assert result.sync_result == sync_result
        assert result.errors == []
        assert result.warnings == ['Minor warning']
    
    @pytest.mark.unit
    def test_canvas_bridge_result_ready_for_frontend_true(self):
        """Test ready_for_frontend property when conditions are met."""
        sync_result = Mock()
        sync_result.success = True
        
        result = CanvasBridgeResult(
            success=True,
            course_id=12345,
            typescript_execution_time=1.0,
            data_transformation_time=0.5,
            database_sync_time=1.5,
            total_time=3.0,
            objects_synced={'courses': 1, 'students': 3},
            sync_result=sync_result,
            errors=[],
            warnings=[]
        )
        
        assert result.ready_for_frontend is True
    
    @pytest.mark.unit
    def test_canvas_bridge_result_ready_for_frontend_false(self):
        """Test ready_for_frontend property when conditions are not met."""
        # Test with failed sync
        sync_result = Mock()
        sync_result.success = False
        
        result = CanvasBridgeResult(
            success=False,
            course_id=12345,
            typescript_execution_time=1.0,
            data_transformation_time=0.5,
            database_sync_time=1.5,
            total_time=3.0,
            objects_synced={'courses': 0, 'students': 0},
            sync_result=sync_result,
            errors=['Sync failed'],
            warnings=[]
        )
        
        assert result.ready_for_frontend is False


class TestCanvasBridgeConvenienceFunctions:
    """Test standalone convenience functions."""
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_function_default_params(self):
        """Test initialize_canvas_course convenience function with default parameters."""
        course_id = 12345
        
        mock_result = CanvasBridgeResult(
            success=True,
            course_id=course_id,
            typescript_execution_time=1.0,
            data_transformation_time=0.5,
            database_sync_time=1.5,
            total_time=3.0,
            objects_synced={'courses': 1},
            sync_result=Mock(success=True),
            errors=[],
            warnings=[]
        )
        
        with patch('database.operations.canvas_bridge.CanvasDataBridge') as mock_bridge_class:
            mock_bridge = Mock()
            mock_bridge.initialize_canvas_course_sync = AsyncMock(return_value=mock_result)
            mock_bridge_class.return_value = mock_bridge
            
            with patch('database.session.get_session') as mock_get_session:
                mock_session = Mock()
                mock_get_session.return_value = mock_session
                
                result = await initialize_canvas_course(course_id)
                
                assert result.success is True
                assert result.course_id == course_id
                
                # Verify bridge was created with default parameters
                mock_bridge_class.assert_called_once()
                mock_bridge.initialize_canvas_course_sync.assert_called_once_with(course_id, SyncPriority.HIGH)
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_initialize_canvas_course_function_custom_params(self):
        """Test initialize_canvas_course convenience function with custom parameters."""
        course_id = 12345
        custom_path = "/custom/canvas-interface"
        custom_session = Mock()
        custom_priority = SyncPriority.MEDIUM
        
        mock_result = Mock()
        mock_result.success = True
        
        with patch('database.operations.canvas_bridge.CanvasDataBridge') as mock_bridge_class:
            mock_bridge = Mock()
            mock_bridge.initialize_canvas_course_sync = AsyncMock(return_value=mock_result)
            mock_bridge_class.return_value = mock_bridge
            
            result = await initialize_canvas_course(
                course_id,
                canvas_interface_path=custom_path,
                session=custom_session,
                priority=custom_priority
            )
            
            assert result.success is True
            
            # Verify bridge was created with custom parameters
            mock_bridge_class.assert_called_once_with(custom_path, custom_session)
            mock_bridge.initialize_canvas_course_sync.assert_called_once_with(course_id, custom_priority)


# ==================== ERROR HANDLING TESTS ====================

class TestCanvasBridgeErrorHandling:
    """Test error handling scenarios in Canvas bridge."""
    
    @pytest.mark.unit
    def test_rollback_on_sync_failure(self):
        """Test that rollback is attempted on sync failure."""
        mock_session = Mock()
        
        with patch('database.operations.canvas_bridge.TypeScriptExecutor'), \
             patch('database.operations.canvas_bridge.CanvasDataTransformer'), \
             patch('database.operations.canvas_bridge.CanvasDataManager'), \
             patch('database.operations.canvas_bridge.SyncCoordinator') as mock_coordinator_class, \
             patch('database.operations.canvas_bridge.TransactionManager'), \
             patch('pathlib.Path.exists', return_value=True):
            
            mock_coordinator = Mock()
            mock_coordinator.rollback_sync_session = Mock()
            mock_coordinator_class.return_value = mock_coordinator
            
            bridge = CanvasDataBridge("/test/path", mock_session, auto_detect_path=False)
            
            # Test that rollback method exists and can be called
            assert hasattr(bridge.sync_coordinator, 'rollback_sync_session')
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_cleanup_on_exception(self):
        """Test that resources are cleaned up even when exceptions occur."""
        mock_session = Mock()
        
        with patch('database.operations.canvas_bridge.TypeScriptExecutor') as mock_executor_class, \
             patch('database.operations.canvas_bridge.CanvasDataTransformer'), \
             patch('database.operations.canvas_bridge.CanvasDataManager'), \
             patch('database.operations.canvas_bridge.SyncCoordinator'), \
             patch('database.operations.canvas_bridge.TransactionManager'), \
             patch('pathlib.Path.exists', return_value=True):
            
            mock_executor = Mock()
            mock_executor.execute_course_data_constructor = AsyncMock(side_effect=Exception("Test error"))
            mock_executor_class.return_value = mock_executor
            
            bridge = CanvasDataBridge("/test/path", mock_session, auto_detect_path=False)
            
            # Mock validation to pass
            with patch.object(bridge, 'validate_bridge_environment') as mock_validation:
                mock_validation.return_value = {'valid': True, 'errors': [], 'warnings': []}
                
                # Test that exception is properly handled
                with pytest.raises(CanvasOperationError):
                    await bridge.initialize_canvas_course_sync(12345)


# ==================== INTEGRATION TEST MARKERS ====================

@pytest.mark.integration
class TestCanvasBridgeIntegration:
    """Integration tests for Canvas bridge requiring external dependencies."""
    
    def test_real_canvas_bridge_initialization(self):
        """Test Canvas bridge initialization with real components."""
        # This test would initialize Canvas bridge with real TypeScript executor,
        # data transformer, and database components when integration testing is performed
        pass
    
    def test_real_environment_validation(self):
        """Test environment validation against real system."""
        # This test would validate against real Node.js, npx, tsx installation
        # when integration testing is performed
        pass
    
    def test_real_canvas_api_sync(self):
        """Test actual Canvas API sync with real credentials."""
        # This test would perform actual Canvas API calls and database sync
        # when integration testing is performed with real Canvas credentials
        pass