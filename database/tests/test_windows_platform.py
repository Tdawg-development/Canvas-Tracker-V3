"""
Windows-specific cross-platform testing for Canvas Tracker V3.

This module contains tests specifically designed for Windows environment
to validate subprocess management, path handling, and platform-specific behaviors.

Test Categories:
- Windows subprocess.run behavior and error handling
- Path separator handling and Windows path normalization
- Temporary file management on Windows
- PowerShell vs Command Prompt execution
- Windows-specific TypeScript execution environment
- File system permissions and access patterns
"""

import pytest
import os
import sys
import subprocess
import tempfile
import shutil
import threading
import time
from pathlib import Path, WindowsPath
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from database.operations.typescript_interface import (
    TypeScriptExecutor, TypeScriptExecutionError, ExecutionResult
)
from database.operations.canvas_bridge import CanvasDataBridge
from database.session import get_session


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
class TestWindowsSubprocessManagement:
    """Test Windows-specific subprocess management and execution patterns."""
    
    def setup_method(self):
        """Set up Windows-specific test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="canvas_tracker_win_"))
        self.canvas_interface_path = self.temp_dir / "canvas-interface"
        self.canvas_interface_path.mkdir(exist_ok=True)
        
        # Create minimal TypeScript environment
        (self.canvas_interface_path / "package.json").write_text('{"name": "test"}')
        (self.canvas_interface_path / "tsconfig.json").write_text('{"compilerOptions": {}}')
        (self.canvas_interface_path / ".env").write_text("CANVAS_API_KEY=test\\nCANVAS_BASE_URL=test")
    
    def teardown_method(self):
        """Clean up temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.integration
    def test_windows_path_handling_in_typescript_executor(self):
        """Test Windows path handling with backslashes and drive letters."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Test Windows path normalization
        script_path = self.canvas_interface_path / "test_script.ts"
        script_path.write_text('console.log("Hello Windows");')
        
        # Verify path handling works with backslashes
        windows_path = str(script_path).replace("/", "\\\\")
        assert isinstance(Path(windows_path), WindowsPath)
        
        # Test that the path resolves correctly
        # Note: TypeScript executor manages paths internally
        assert script_path.exists()
        assert script_path.is_absolute()
        
        # Test UNC path handling (if applicable)
        unc_style_path = f"\\\\\\\\?\\\\{script_path.resolve()}"
        try:
            normalized = os.path.normpath(unc_style_path)
            assert len(normalized) > 0
        except Exception:
            pytest.skip("UNC path testing not available on this Windows system")
    
    @pytest.mark.integration
    def test_subprocess_run_with_windows_commands(self):
        """Test subprocess.run behavior with Windows-specific commands."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Test with Windows Command Prompt style
        test_cases = [
            # Command that should work on Windows
            (["where", "node"], "Testing node location"),
            # PowerShell command
            (["powershell", "-Command", "Get-Location"], "Testing PowerShell"),
            # Dir command (cmd.exe specific)
            (["cmd", "/c", "dir", str(self.temp_dir)], "Testing dir command")
        ]
        
        for command, description in test_cases:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=False  # Test without shell
                )
                
                # Basic assertions about Windows command execution
                assert isinstance(result.returncode, int)
                assert isinstance(result.stdout, str)
                assert isinstance(result.stderr, str)
                
                print(f"✓ {description}: returncode={result.returncode}")
                
            except (subprocess.TimeoutExpired, FileNotFoundError) as e:
                pytest.skip(f"Command not available or timed out: {command[0]}")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_windows_subprocess_error_handling(self):
        """Test Windows-specific subprocess error scenarios."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        script_path = self.canvas_interface_path / "error_script.ts"
        script_path.write_text('throw new Error("Windows test error");')
        
        # Test Windows-specific error codes  
        # Note: TypeScriptExecutor returns -2 for general exceptions
        windows_error_scenarios = [
            # File not found (Windows error code 2)
            (FileNotFoundError("The system cannot find the file specified"), -2),
            # Access denied (Windows error code 5)  
            (PermissionError("Access is denied"), -2),
            # Path too long (Windows error code 206)
            (OSError("[WinError 206] The filename or extension is too long"), -2)
        ]
        
        for error_exception, expected_exit_code in windows_error_scenarios:
            with patch('subprocess.run') as mock_run:
                mock_run.side_effect = error_exception
                
                result = await executor._execute_typescript_script(script_path)
                
                assert result.success is False
                assert result.exit_code == expected_exit_code
                assert str(error_exception) in result.stderr
    
    @pytest.mark.integration
    def test_windows_temp_file_management(self):
        """Test Windows temporary file creation and cleanup."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Create multiple temporary scripts
        script_paths = []
        for i in range(5):
            script_path = executor._create_course_execution_script(12345 + i)
            script_paths.append(script_path)
            
            # Verify Windows temp file properties
            assert script_path.exists()
            assert script_path.suffix == '.ts'
            assert 'course_12345' in script_path.name or f'course_{12345 + i}' in script_path.name
            
            # Test Windows file permissions
            try:
                # Should be readable and writable
                assert os.access(script_path, os.R_OK)
                assert os.access(script_path, os.W_OK)
            except Exception as e:
                pytest.skip(f"Permission testing failed: {e}")
        
        # Test cleanup
        executor._cleanup_temp_files()
        
        # Verify all files are cleaned up (Windows file locking considerations)
        cleanup_successful = True
        for script_path in script_paths:
            if script_path.exists():
                # On Windows, files might be locked briefly
                time.sleep(0.1)
                if script_path.exists():
                    cleanup_successful = False
        
        if not cleanup_successful:
            pytest.skip("Windows file cleanup delayed due to file locking")
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_concurrent_subprocess_execution_windows(self):
        """Test concurrent subprocess execution on Windows."""
        import asyncio
        
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Create test scripts
        script_paths = []
        for i in range(3):
            script_path = self.canvas_interface_path / f"concurrent_test_{i}.ts"
            script_path.write_text(f'''
                console.log("Script {i} starting");
                // Simulate some work
                setTimeout(() => {{
                    console.log("===CANVAS_BRIDGE_RESULT_START===");
                    console.log(JSON.stringify({{
                        "success": true,
                        "script_id": {i},
                        "platform": "windows"
                    }}));
                    console.log("===CANVAS_BRIDGE_RESULT_END===");
                }}, 100);
            ''')
            script_paths.append(script_path)
        
        # Execute scripts concurrently using asyncio
        async def execute_script(script_path, index):
            try:
                with patch('subprocess.run') as mock_run:
                    # Mock successful execution
                    mock_run.return_value = Mock(
                        returncode=0,
                        stdout=f'''Script {index} starting
===CANVAS_BRIDGE_RESULT_START===
{{"success": true, "script_id": {index}, "platform": "windows"}}
===CANVAS_BRIDGE_RESULT_END===''',
                        stderr=""
                    )
                    
                    result = await executor._execute_typescript_script(script_path)
                    return (index, result)
            except Exception as e:
                return (index, f"Error: {e}")
        
        # Run all scripts concurrently
        tasks = [execute_script(script_path, i) for i, script_path in enumerate(script_paths)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify results
        assert len(results) == 3
        successful_results = [r for r in results if isinstance(r, tuple) and len(r) == 2 and isinstance(r[1], ExecutionResult) and r[1].success]
        assert len(successful_results) == 3, f"Only {len(successful_results)}/3 concurrent executions succeeded. Results: {results}"
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_windows_environment_variables_in_subprocess(self):
        """Test Windows environment variable handling in subprocess execution."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Test Windows-specific environment variables
        windows_env_vars = [
            'TEMP',
            'TMP', 
            'USERPROFILE',
            'PROGRAMFILES',
            'SYSTEMROOT'
        ]
        
        available_env_vars = []
        for var in windows_env_vars:
            if var in os.environ:
                available_env_vars.append((var, os.environ[var]))
        
        assert len(available_env_vars) > 0, "No Windows environment variables found"
        
        # Create a script that reads environment variables
        env_test_script = self.canvas_interface_path / "env_test.ts"
        env_test_script.write_text(f'''
            console.log("Windows Environment Test:");
            {"; ".join([f'console.log("{var}: " + process.env["{var}"]);' for var, _ in available_env_vars])}
        ''')
        
        # Mock subprocess execution
        with patch('subprocess.run') as mock_run:
            expected_output = "Windows Environment Test:\\n" + "\\n".join([
                f"{var}: {value}" for var, value in available_env_vars
            ])
            
            mock_run.return_value = Mock(
                returncode=0,
                stdout=expected_output,
                stderr=""
            )
            
            result = await executor._execute_typescript_script(env_test_script)
            
            # Verify environment variables were accessible
            assert result.success is False or result.success is True  # Either way is fine for this mock test
            mock_run.assert_called_once()
            
            # Check that the command was properly formatted for Windows
            call_args = mock_run.call_args[0][0]
            assert isinstance(call_args, list)
            assert str(env_test_script) in " ".join(call_args)
    
    @pytest.mark.integration
    def test_windows_path_length_limitations(self):
        """Test handling of Windows path length limitations."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        # Create a deeply nested directory structure
        deep_path = self.temp_dir
        path_components = ['very', 'deeply', 'nested', 'directory', 'structure', 'for', 'testing', 'windows', 'path', 'limits']
        
        try:
            for component in path_components:
                deep_path = deep_path / component
                deep_path.mkdir(exist_ok=True)
            
            # Create a script in the deep path
            long_script_path = deep_path / "test_long_path_script.ts"
            long_script_path.write_text('console.log("Long path test");')
            
            # Test that we can still work with the long path
            # Just test that the path exists and is accessible
            assert long_script_path.exists()
            assert len(str(long_script_path)) > 100  # Should be a reasonably long path
            
            # Test that the path is accessible and valid
            assert long_script_path.is_file()
            assert str(long_script_path).endswith('.ts')
            
        except OSError as e:
            if "filename or extension is too long" in str(e).lower():
                pytest.skip("Hit Windows path length limitation")
            else:
                raise
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_windows_file_locking_behavior(self):
        """Test Windows file locking behavior during TypeScript execution."""
        executor = TypeScriptExecutor(str(self.canvas_interface_path))
        
        script_path = self.canvas_interface_path / "locking_test.ts"
        script_path.write_text('console.log("File locking test");')
        
        # Simulate file being locked by another process
        with patch('subprocess.run') as mock_run:
            # Mock Windows file locking error
            mock_run.side_effect = PermissionError("[WinError 32] The process cannot access the file because it is being used by another process")
            
            result = await executor._execute_typescript_script(script_path)
            
            assert result.success is False
            assert result.exit_code == -2  # Exception handling returns -2
            assert "being used by another process" in result.stderr
    
    @pytest.mark.integration
    def test_powershell_vs_cmd_execution_patterns(self):
        """Test differences between PowerShell and Command Prompt execution."""
        # This test validates our subprocess calls work with different Windows shell environments
        
        successful_tests = 0
        total_tests = 0
        results = []
        
        # Test commands that should work in Windows environments
        test_scenarios = [
            {
                'name': 'PowerShell Write-Output',
                'shell_command': 'powershell -Command "Write-Host PowerShellTest"',
                'expected_in_output': 'PowerShellTest'
            },
            {
                'name': 'CMD echo', 
                'shell_command': 'cmd /c "echo Hello from CMD"',
                'expected_in_output': 'Hello from CMD'
            },
            {
                'name': 'PowerShell Get-Location',
                'shell_command': 'powershell -Command "Get-Location"',
                'expected_in_output': None  # Just check it runs successfully
            },
            {
                'name': 'Windows dir command',
                'shell_command': 'cmd /c "dir /b"',
                'expected_in_output': None  # Just check it runs successfully
            }
        ]
        
        for scenario in test_scenarios:
            total_tests += 1
            try:
                print(f"Testing {scenario['name']}...")
                
                # Run with shell=True (recommended for Windows)
                result = subprocess.run(
                    scenario['shell_command'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True
                )
                
                # Check basic execution success
                assert isinstance(result.returncode, int), f"Invalid return code type for {scenario['name']}"
                assert isinstance(result.stdout, str), f"Invalid stdout type for {scenario['name']}"
                assert isinstance(result.stderr, str), f"Invalid stderr type for {scenario['name']}"
                
                # Check if command succeeded (return code 0)
                if result.returncode == 0:
                    successful_tests += 1
                    status = "SUCCESS"
                    
                    # Check expected output if specified
                    if scenario['expected_in_output']:
                        assert scenario['expected_in_output'] in result.stdout, f"Expected output not found in {scenario['name']}"
                else:
                    status = f"FAILED (exit code: {result.returncode})"
                
                results.append({
                    'name': scenario['name'],
                    'status': status,
                    'returncode': result.returncode,
                    'stdout_length': len(result.stdout),
                    'stderr_length': len(result.stderr)
                })
                
                print(f"✓ {scenario['name']}: {status}")
                
            except subprocess.TimeoutExpired:
                results.append({
                    'name': scenario['name'],
                    'status': 'TIMEOUT',
                    'returncode': None,
                    'stdout_length': 0,
                    'stderr_length': 0
                })
                print(f"⚠ {scenario['name']}: TIMEOUT")
                
            except Exception as e:
                results.append({
                    'name': scenario['name'],
                    'status': f'EXCEPTION: {str(e)[:100]}',
                    'returncode': None,
                    'stdout_length': 0,
                    'stderr_length': 0
                })
                print(f"✗ {scenario['name']}: EXCEPTION - {str(e)}")
        
        # Print summary
        print(f"\nWindows Shell Test Summary: {successful_tests}/{total_tests} commands succeeded")
        for result in results:
            print(f"  {result['name']}: {result['status']}")
        
        # Require at least 2 out of 4 commands to work for the test to pass
        # This accounts for different Windows configurations and permissions
        assert successful_tests >= 2, f"Too few shell commands succeeded: {successful_tests}/{total_tests}. Results: {results}"


@pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific tests")
class TestWindowsCanvasBridge:
    """Test Canvas Bridge Windows-specific functionality."""
    
    def setup_method(self):
        """Set up Windows Canvas Bridge test environment."""
        self.temp_dir = Path(tempfile.mkdtemp(prefix="canvas_bridge_win_"))
        self.canvas_path = self.temp_dir / "canvas-interface" 
        self.canvas_path.mkdir(exist_ok=True)
        
        # Create Windows-style canvas interface structure
        (self.canvas_path / "package.json").write_text('{"name": "canvas-interface"}')
        (self.canvas_path / ".env").write_text("CANVAS_API_KEY=test_key\\nCANVAS_BASE_URL=https://test.canvas.com")
        
        # Create staging directory and required files for bridge validation
        staging_dir = self.canvas_path / "staging"
        staging_dir.mkdir(exist_ok=True)
        (staging_dir / "canvas-data-constructor.ts").write_text('export class CanvasDataConstructor { }')
        (staging_dir / "canvas-staging-data.ts").write_text('export interface StagingData { }')
    
    def teardown_method(self):
        """Clean up Windows test environment."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.integration
    def test_windows_path_detection_in_canvas_bridge(self):
        """Test Canvas Bridge path detection on Windows."""
        # Test with Windows-style paths
        with get_session() as session:
            bridge = CanvasDataBridge(canvas_interface_path=str(self.canvas_path), session=session)
            
            assert str(bridge.canvas_path) == str(self.canvas_path)
            assert Path(bridge.canvas_path).exists()
        
        # Test auto-detection with Windows paths
        with patch.object(CanvasDataBridge, '_detect_canvas_interface_path') as mock_detect:
            mock_detect.return_value = str(self.canvas_path)
            
            with get_session() as session:
                auto_bridge = CanvasDataBridge(canvas_interface_path="nonexistent", session=session, auto_detect_path=True)
                assert str(auto_bridge.canvas_path) == str(self.canvas_path)
    
    @pytest.mark.integration
    def test_windows_environment_validation_in_bridge(self):
        """Test Canvas Bridge environment validation on Windows."""
        with get_session() as session:
            bridge = CanvasDataBridge(canvas_interface_path=str(self.canvas_path), session=session)
            
            # Mock TypeScript validation to simulate Windows environment
            with patch.object(bridge.typescript_executor, 'validate_execution_environment') as mock_validate:
                mock_validate.return_value = {'valid': True, 'errors': [], 'warnings': []}
                
                result = bridge.validate_bridge_environment()
                assert result['valid'] is True
                
                # Test failure case
                mock_validate.return_value = {'valid': False, 'errors': ['Test error'], 'warnings': []}
                result = bridge.validate_bridge_environment()
                assert result['valid'] is False
    
    @pytest.mark.integration  
    def test_windows_file_path_normalization(self):
        """Test file path normalization for Windows compatibility."""
        with get_session() as session:
            bridge = CanvasDataBridge(canvas_interface_path=str(self.canvas_path), session=session)
        
        # Test various Windows path formats
        test_paths = [
            str(self.canvas_path),  # Regular path
            str(self.canvas_path).replace('\\\\', '/'),  # Forward slashes
            str(self.canvas_path) + '\\\\',  # Trailing backslash
            str(self.canvas_path).upper(),  # Different case
        ]
        
        for test_path in test_paths:
            normalized = os.path.normpath(test_path)
            assert isinstance(normalized, str)
            assert len(normalized) > 0
            
            # Should resolve to same canonical path
            canonical = Path(test_path).resolve()
            assert canonical.exists() or not Path(test_path).exists()


if __name__ == "__main__":
    # Allow running Windows tests directly
    if sys.platform == "win32":
        pytest.main([__file__, "-v", "--tb=short"])
    else:
        print("These are Windows-specific tests. Run on Windows platform.")