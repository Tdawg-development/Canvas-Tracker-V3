"""
Unit Tests for TypeScript Execution Interface.

Tests the Python subprocess interface that executes TypeScript Canvas interface
components from Python. These tests validate:

- Environment validation (Node.js, npx, tsx)
- Temporary script creation and cleanup
- Subprocess execution and timeout handling
- JSON result parsing and validation
- Error handling and recovery
- Cross-platform compatibility (Windows PowerShell)
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from database.operations.typescript_interface import (
    TypeScriptExecutor,
    TypeScriptExecutionError,
    ExecutionResult,
    execute_canvas_course_data,
    validate_typescript_environment
)


class TestTypeScriptExecutor:
    """Test TypeScriptExecutor core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary directory for testing
        self.temp_dir = Path(tempfile.mkdtemp())
        self.canvas_path = self.temp_dir / "canvas-interface"
        self.canvas_path.mkdir()
        
        # Create required directory structure
        staging_dir = self.canvas_path / "staging"
        staging_dir.mkdir()
        
        # Create mock TypeScript files
        (staging_dir / "canvas-data-constructor.ts").write_text("// Mock TypeScript file")
        (staging_dir / "canvas-staging-data.ts").write_text("// Mock TypeScript file")
        (self.canvas_path / "package.json").write_text('{"name": "canvas-interface"}')
        
        self.executor = TypeScriptExecutor(str(self.canvas_path))
    
    def teardown_method(self):
        """Clean up test fixtures."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)
    
    @pytest.mark.unit
    def test_typescript_executor_initialization(self):
        """Test TypeScriptExecutor initialization."""
        assert isinstance(self.executor, TypeScriptExecutor)
        assert self.executor.canvas_path == self.canvas_path
        assert hasattr(self.executor, 'logger')
        assert isinstance(self.executor._temp_files, list)
    
    # ==================== ENVIRONMENT VALIDATION TESTS ====================
    
    @pytest.mark.unit
    @patch('subprocess.run')
    def test_validate_execution_environment_success(self, mock_run):
        """Test successful environment validation."""
        # Mock successful subprocess calls
        mock_run.side_effect = [
            # node --version
            Mock(returncode=0, stdout="v18.17.0"),
            # npx --version  
            Mock(returncode=0, stdout="9.8.1"),
            # npx tsx --version
            Mock(returncode=0, stdout="tsx v4.20.6")
        ]
        
        result = self.executor.validate_execution_environment()
        
        assert result['valid'] is True
        assert result['node_version'] == "v18.17.0"
        assert result['npx_available'] is True
        assert result['tsx_available'] is True
        assert len(result['errors']) == 0
    
    @pytest.mark.unit
    @patch('subprocess.run')
    def test_validate_execution_environment_node_missing(self, mock_run):
        """Test environment validation with missing Node.js."""
        mock_run.side_effect = [
            # node --version fails
            Mock(returncode=1, stdout="", stderr="node: command not found"),
            # npx --version fails
            Mock(returncode=1, stdout="", stderr="npx: command not found")
        ]
        
        result = self.executor.validate_execution_environment()
        
        assert result['valid'] is False
        assert result['node_version'] is None
        assert result['npx_available'] is False
        assert result['tsx_available'] is False
        assert len(result['errors']) > 0
        assert any("Node.js not found" in error for error in result['errors'])
    
    @pytest.mark.unit
    @patch('subprocess.run')
    def test_validate_execution_environment_old_node_version(self, mock_run):
        """Test environment validation with old Node.js version."""
        mock_run.side_effect = [
            # Old Node.js version
            Mock(returncode=0, stdout="v14.20.0"),
            # npx available
            Mock(returncode=0, stdout="8.5.0"),
            # tsx available
            Mock(returncode=0, stdout="tsx v3.12.0")
        ]
        
        result = self.executor.validate_execution_environment()
        
        assert result['valid'] is True  # Still valid but with warning
        assert result['node_version'] == "v14.20.0"
        assert len(result['warnings']) > 0
        assert any("Version 16+ recommended" in warning for warning in result['warnings'])
    
    @pytest.mark.unit
    @patch('subprocess.run')
    def test_validate_execution_environment_tsx_missing(self, mock_run):
        """Test environment validation with missing tsx."""
        mock_run.side_effect = [
            # node available
            Mock(returncode=0, stdout="v18.17.0"),
            # npx available
            Mock(returncode=0, stdout="9.8.1"),
            # tsx not available
            Mock(returncode=1, stderr="tsx not found")
        ]
        
        result = self.executor.validate_execution_environment()
        
        assert result['valid'] is False
        assert result['tsx_available'] is False
        assert any("tsx not available" in error for error in result['errors'])
    
    @pytest.mark.unit
    def test_validate_execution_environment_missing_files(self):
        """Test environment validation with missing required files."""
        # Remove required files
        (self.canvas_path / "staging" / "canvas-data-constructor.ts").unlink()
        (self.canvas_path / "package.json").unlink()
        
        with patch('subprocess.run') as mock_run:
            # Mock successful subprocess calls
            mock_run.side_effect = [
                Mock(returncode=0, stdout="v18.17.0"),
                Mock(returncode=0, stdout="9.8.1"), 
                Mock(returncode=0, stdout="tsx v4.20.6")
            ]
            
            result = self.executor.validate_execution_environment()
        
        # Should still be valid (files are warnings, not errors)
        assert result['valid'] is True
        assert len(result['warnings']) > 0
        assert any("canvas-data-constructor.ts" in warning for warning in result['warnings'])
        assert any("package.json" in warning for warning in result['warnings'])
    
    @pytest.mark.unit
    @patch('subprocess.run', side_effect=Exception("Subprocess failed"))
    def test_validate_execution_environment_exception(self, mock_run):
        """Test environment validation with subprocess exception."""
        result = self.executor.validate_execution_environment()
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
        # Check for either the specific error or the general environment validation error
        error_messages = ' '.join(result['errors'])
        assert "Node.js check failed" in error_messages or "Environment validation error" in error_messages
    
    # ==================== SCRIPT CREATION TESTS ====================
    
    @pytest.mark.unit
    def test_create_course_execution_script(self):
        """Test creation of temporary execution script."""
        course_id = 12345
        
        script_path = self.executor._create_course_execution_script(course_id)
        
        # Verify script file was created
        assert script_path.exists()
        assert script_path.suffix == '.ts'
        assert f"execute_course_{course_id}.ts" in script_path.name
        
        # Verify script content
        content = script_path.read_text(encoding='utf-8')
        assert f"constructCourseData({course_id})" in content
        assert "CanvasDataConstructor" in content
        assert "===CANVAS_BRIDGE_RESULT_START===" in content
        assert "===CANVAS_BRIDGE_RESULT_END===" in content
        
        # Verify temp files are tracked
        assert script_path in self.executor._temp_files
        assert script_path.parent in self.executor._temp_files
    
    @pytest.mark.unit
    def test_create_multiple_execution_scripts(self):
        """Test creation of multiple execution scripts."""
        course_ids = [12345, 67890, 11111]
        script_paths = []
        
        for course_id in course_ids:
            script_path = self.executor._create_course_execution_script(course_id)
            script_paths.append(script_path)
            
        # Verify all scripts were created with unique names
        assert len(script_paths) == 3
        assert len(set(script_paths)) == 3  # All unique
        
        # Verify all are tracked for cleanup
        for script_path in script_paths:
            assert script_path in self.executor._temp_files
    
    # ==================== SCRIPT EXECUTION TESTS ====================
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_execute_typescript_script_success(self, mock_run):
        """Test successful TypeScript script execution."""
        # Mock successful Canvas data result
        mock_result_data = {
            "success": True,
            "course_id": 12345,
            "course": {"id": 12345, "name": "Test Course"},
            "students": [],
            "modules": []
        }
        
        # Mock stdout with Canvas bridge markers
        mock_stdout = f"""
Some console output...
===CANVAS_BRIDGE_RESULT_START===
{json.dumps(mock_result_data, indent=2)}
===CANVAS_BRIDGE_RESULT_END===
"""
        
        mock_run.return_value = Mock(
            returncode=0,
            stdout=mock_stdout,
            stderr=""
        )
        
        script_path = self.canvas_path / "test_script.ts"
        script_path.write_text("// Mock script")
        
        result = await self.executor._execute_typescript_script(script_path)
        
        assert result.success is True
        assert result.exit_code == 0
        assert result.data is not None
        assert result.data['success'] is True
        assert result.data['course_id'] == 12345
        assert isinstance(result.execution_time, float)
        
        # Verify subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args
        assert 'npx' in call_args[0][0]
        assert 'tsx' in call_args[0][0]
        assert str(script_path) in call_args[0][0]
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_execute_typescript_script_failure(self, mock_run):
        """Test TypeScript script execution failure."""
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="TypeScript compilation error"
        )
        
        script_path = self.canvas_path / "test_script.ts"
        script_path.write_text("// Mock script")
        
        result = await self.executor._execute_typescript_script(script_path)
        
        assert result.success is False
        assert result.exit_code == 1
        assert result.data is None
        assert "TypeScript compilation error" in result.stderr
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_execute_typescript_script_timeout(self, mock_run):
        """Test TypeScript script execution timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(['npx'], 10)
        
        script_path = self.canvas_path / "test_script.ts"
        script_path.write_text("// Mock script")
        
        result = await self.executor._execute_typescript_script(script_path, timeout=5)
        
        assert result.success is False
        assert result.exit_code == -1
        assert "Timeout after" in result.stderr
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run', side_effect=Exception("Subprocess exception"))
    async def test_execute_typescript_script_exception(self, mock_run):
        """Test TypeScript script execution with exception."""
        script_path = self.canvas_path / "test_script.ts"
        script_path.write_text("// Mock script")
        
        result = await self.executor._execute_typescript_script(script_path)
        
        assert result.success is False
        assert result.exit_code == -2
        assert "Subprocess exception" in result.stderr
    
    # ==================== JSON PARSING TESTS ====================
    
    @pytest.mark.unit
    def test_parse_canvas_result_success(self):
        """Test parsing successful Canvas result from stdout."""
        mock_data = {
            "success": True,
            "course_id": 12345,
            "course": {"id": 12345, "name": "Test Course"}
        }
        
        stdout = f"""
Console output line 1
Console output line 2
===CANVAS_BRIDGE_RESULT_START===
{json.dumps(mock_data, indent=2)}
===CANVAS_BRIDGE_RESULT_END===
More console output
"""
        
        result = self.executor._parse_canvas_result(stdout)
        
        assert result['success'] is True
        assert result['course_id'] == 12345
        assert result['course']['name'] == "Test Course"
    
    @pytest.mark.unit
    def test_parse_canvas_result_failure(self):
        """Test parsing failed Canvas result from stdout."""
        mock_data = {
            "success": False,
            "error": {"message": "Canvas API failed", "name": "Error"}
        }
        
        stdout = f"""
===CANVAS_BRIDGE_RESULT_START===
{json.dumps(mock_data)}
===CANVAS_BRIDGE_RESULT_END===
"""
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            self.executor._parse_canvas_result(stdout)
        
        assert "Canvas API failed" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_parse_canvas_result_missing_markers(self):
        """Test parsing Canvas result with missing markers."""
        stdout = "Just regular console output without markers"
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            self.executor._parse_canvas_result(stdout)
        
        assert "Canvas result markers not found" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_parse_canvas_result_empty_content(self):
        """Test parsing Canvas result with empty JSON content."""
        stdout = """
===CANVAS_BRIDGE_RESULT_START===

===CANVAS_BRIDGE_RESULT_END===
"""
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            self.executor._parse_canvas_result(stdout)
        
        assert "Empty JSON content" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_parse_canvas_result_invalid_json(self):
        """Test parsing Canvas result with invalid JSON."""
        stdout = """
===CANVAS_BRIDGE_RESULT_START===
{invalid json content}
===CANVAS_BRIDGE_RESULT_END===
"""
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            self.executor._parse_canvas_result(stdout)
        
        assert "Failed to parse JSON" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_parse_canvas_result_invalid_structure(self):
        """Test parsing Canvas result with invalid structure."""
        stdout = """
===CANVAS_BRIDGE_RESULT_START===
["not", "an", "object"]
===CANVAS_BRIDGE_RESULT_END===
"""
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            self.executor._parse_canvas_result(stdout)
        
        assert "Invalid result type" in str(exc_info.value)
    
    # ==================== CLEANUP TESTS ====================
    
    @pytest.mark.unit
    def test_cleanup_temp_files(self):
        """Test cleanup of temporary files."""
        # Create some temporary files
        temp_file1 = self.temp_dir / "temp1.ts"
        temp_file2 = self.temp_dir / "temp2.ts"
        temp_dir = self.temp_dir / "temp_subdir"
        
        temp_file1.write_text("temp content")
        temp_file2.write_text("temp content")
        temp_dir.mkdir()
        (temp_dir / "file_in_subdir.ts").write_text("content")
        
        # Add to temp files list
        self.executor._temp_files = [temp_file1, temp_file2, temp_dir]
        
        # Perform cleanup
        self.executor._cleanup_temp_files()
        
        # Verify files were deleted
        assert not temp_file1.exists()
        assert not temp_file2.exists()
        assert not temp_dir.exists()
        
        # Verify list was cleared
        assert len(self.executor._temp_files) == 0
    
    @pytest.mark.unit
    def test_cleanup_temp_files_error_recovery(self):
        """Test cleanup continues even if some files fail to delete."""
        # Create temp files
        temp_file1 = self.temp_dir / "temp1.ts"
        temp_file2 = self.temp_dir / "temp2.ts"
        
        temp_file1.write_text("temp content")
        temp_file2.write_text("temp content")
        
        self.executor._temp_files = [temp_file1, temp_file2]
        
        # Mock pathlib.Path.unlink to fail for first file
        def mock_unlink(self, missing_ok=False):
            if "temp1" in str(self):
                raise OSError("Permission denied")
            # For other files, actually delete them
            if self.exists():
                self._accessor.unlink(self)
        
        with patch('pathlib.Path.unlink', mock_unlink), \
             patch.object(self.executor.logger, 'warning') as mock_warn:
            self.executor._cleanup_temp_files()
        
        # Should have warned about the failed cleanup
        mock_warn.assert_called()
        
        # Should still have cleared the list
        assert len(self.executor._temp_files) == 0
    
    @pytest.mark.unit
    def test_destructor_cleanup(self):
        """Test that destructor cleans up temp files."""
        # Create a temporary file
        temp_file = self.temp_dir / "temp_destructor.ts"
        temp_file.write_text("temp content")
        self.executor._temp_files = [temp_file]
        
        with patch.object(self.executor, '_cleanup_temp_files') as mock_cleanup:
            # Call destructor
            self.executor.__del__()
            
            # Verify cleanup was called
            mock_cleanup.assert_called_once()
    
    # ==================== FULL EXECUTION TESTS ====================
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_execute_course_data_constructor_success(self, mock_run):
        """Test complete course data constructor execution."""
        course_id = 12345
        
        # Mock successful execution
        mock_result_data = {
            "success": True,
            "course_id": course_id,
            "course": {"id": course_id, "name": "Integration Test Course"},
            "students": [{"id": 1, "name": "Test Student"}],
            "modules": []
        }
        
        mock_stdout = f"""
===CANVAS_BRIDGE_RESULT_START===
{json.dumps(mock_result_data)}
===CANVAS_BRIDGE_RESULT_END===
"""
        
        mock_run.return_value = Mock(returncode=0, stdout=mock_stdout, stderr="")
        
        result = await self.executor.execute_course_data_constructor(course_id)
        
        assert result['success'] is True
        assert result['course_id'] == course_id
        assert result['course']['name'] == "Integration Test Course"
        assert len(result['students']) == 1
        
        # Verify temp files were cleaned up
        assert len(self.executor._temp_files) == 0
    
    @pytest.mark.unit
    @pytest.mark.asyncio
    @patch('subprocess.run')
    async def test_execute_course_data_constructor_failure(self, mock_run):
        """Test course data constructor execution failure."""
        course_id = 12345
        
        # Mock execution failure
        mock_run.return_value = Mock(
            returncode=1,
            stdout="",
            stderr="Canvas API authentication failed"
        )
        
        with pytest.raises(TypeScriptExecutionError) as exc_info:
            await self.executor.execute_course_data_constructor(course_id)
        
        assert f"course {course_id}" in str(exc_info.value)
        
        # Verify temp files were cleaned up even on failure
        assert len(self.executor._temp_files) == 0
    
    @pytest.mark.unit 
    def test_execute_data_constructor_sync(self):
        """Test synchronous wrapper for course data constructor."""
        course_id = 12345
        
        with patch.object(self.executor, 'execute_course_data_constructor') as mock_async:
            mock_async.return_value = {"success": True, "course_id": course_id}
            
            # Mock asyncio.run
            with patch('asyncio.run', return_value={"success": True, "course_id": course_id}):
                result = self.executor.execute_data_constructor_sync(course_id)
                
                assert result["success"] is True
                assert result["course_id"] == course_id
    
    # ==================== STATUS AND UTILITY TESTS ====================
    
    @pytest.mark.unit
    def test_get_executor_status(self):
        """Test getting executor status information."""
        # Add some temp files to track
        temp_file = self.temp_dir / "temp.ts"
        self.executor._temp_files = [temp_file]
        
        with patch.object(self.executor, 'validate_execution_environment') as mock_validate:
            mock_validate.return_value = {
                'valid': True,
                'node_version': 'v18.17.0',
                'errors': [],
                'warnings': []
            }
            
            status = self.executor.get_executor_status()
            
            assert status['canvas_interface_path'] == str(self.canvas_path)
            assert status['path_exists'] is True
            assert 'environment_validation' in status
            assert status['temp_files_count'] == 1
            assert str(temp_file) in status['temp_files']
    
    @pytest.mark.unit
    def test_get_executor_status_error(self):
        """Test getting executor status with error."""
        with patch.object(self.executor, 'validate_execution_environment', side_effect=Exception("Test error")):
            status = self.executor.get_executor_status()
            
            assert 'error' in status
            assert "Test error" in status['error']
            assert status['path_exists'] is True


class TestTypeScriptExecutorConvenienceFunctions:
    """Test standalone convenience functions."""
    
    @pytest.mark.unit
    def test_execute_canvas_course_data_function(self):
        """Test execute_canvas_course_data convenience function."""
        course_id = 12345
        
        with patch('database.operations.typescript_interface.TypeScriptExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_data_constructor_sync.return_value = {
                "success": True,
                "course_id": course_id
            }
            mock_executor_class.return_value = mock_executor
            
            result = execute_canvas_course_data(course_id)
            
            assert result["success"] is True
            assert result["course_id"] == course_id
            
            # Verify executor was created with default path
            mock_executor_class.assert_called_once()
            mock_executor.execute_data_constructor_sync.assert_called_once_with(course_id)
    
    @pytest.mark.unit
    def test_execute_canvas_course_data_function_custom_path(self):
        """Test execute_canvas_course_data with custom path."""
        course_id = 12345
        custom_path = "/custom/canvas-interface"
        
        with patch('database.operations.typescript_interface.TypeScriptExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.execute_data_constructor_sync.return_value = {"success": True}
            mock_executor_class.return_value = mock_executor
            
            result = execute_canvas_course_data(course_id, custom_path)
            
            # Verify executor was created with custom path
            mock_executor_class.assert_called_once_with(custom_path)
    
    @pytest.mark.unit
    def test_validate_typescript_environment_function(self):
        """Test validate_typescript_environment convenience function."""
        with patch('database.operations.typescript_interface.TypeScriptExecutor') as mock_executor_class:
            mock_executor = Mock()
            mock_executor.validate_execution_environment.return_value = {
                'valid': True,
                'errors': [],
                'warnings': []
            }
            mock_executor_class.return_value = mock_executor
            
            result = validate_typescript_environment()
            
            assert result['valid'] is True
            
            # Verify executor was created with default path
            mock_executor_class.assert_called_once()
            mock_executor.validate_execution_environment.assert_called_once()


class TestTypeScriptExecutionError:
    """Test TypeScriptExecutionError functionality."""
    
    @pytest.mark.unit
    def test_typescript_execution_error_basic(self):
        """Test basic TypeScriptExecutionError creation."""
        error = TypeScriptExecutionError("Test error message")
        
        assert "Test error message" in str(error)
        assert "Operation: typescript_execution" in str(error)
        assert error.operation_name == "typescript_execution"
        assert error.command is None
        assert error.exit_code is None
    
    @pytest.mark.unit
    def test_typescript_execution_error_complete(self):
        """Test TypeScriptExecutionError with all fields."""
        error = TypeScriptExecutionError(
            "Execution failed",
            command="npx tsx script.ts",
            exit_code=1,
            stdout="Some output",
            stderr="Error details"
        )
        
        assert "Execution failed" in str(error)
        assert error.command == "npx tsx script.ts"
        assert error.exit_code == 1
        assert error.stdout == "Some output"
        assert error.stderr == "Error details"


class TestExecutionResult:
    """Test ExecutionResult data class functionality."""
    
    @pytest.mark.unit
    def test_execution_result_creation(self):
        """Test ExecutionResult creation and attributes."""
        result = ExecutionResult(
            success=True,
            data={"test": "data"},
            execution_time=1.5,
            command="npx tsx test.ts",
            exit_code=0,
            stdout="Success output",
            stderr=""
        )
        
        assert result.success is True
        assert result.data == {"test": "data"}
        assert result.execution_time == 1.5
        assert result.command == "npx tsx test.ts"
        assert result.exit_code == 0
        assert result.stdout == "Success output"
        assert result.stderr == ""
        assert result.temp_files_cleaned is False  # Default value
    
    @pytest.mark.unit
    def test_execution_result_failure(self):
        """Test ExecutionResult for failed execution."""
        result = ExecutionResult(
            success=False,
            data=None,
            execution_time=0.8,
            command="npx tsx bad.ts",
            exit_code=1,
            stdout="",
            stderr="Compilation error",
            temp_files_cleaned=True
        )
        
        assert result.success is False
        assert result.data is None
        assert result.exit_code == 1
        assert "Compilation error" in result.stderr
        assert result.temp_files_cleaned is True


# ==================== INTEGRATION TEST MARKERS ====================

@pytest.mark.integration  
class TestTypeScriptExecutorIntegration:
    """Integration tests requiring external dependencies."""
    
    def test_real_environment_validation(self):
        """Test environment validation with real system."""
        # This test would validate against the real system environment
        # when integration testing is performed with actual Node.js/npx/tsx
        pass
    
    def test_real_typescript_execution(self):
        """Test actual TypeScript execution."""
        # This test would execute real TypeScript code
        # when integration testing is performed  
        pass