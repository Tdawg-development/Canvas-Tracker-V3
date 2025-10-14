"""
TypeScript Execution Interface

This module provides a Python subprocess interface to execute TypeScript Canvas interface
components from Python. It handles the critical bridge between Python database operations
and TypeScript Canvas API calls.

Key Features:
- Execute TypeScript CanvasDataConstructor via subprocess
- Environment validation (Node.js, npx, tsx)
- Temporary script creation and cleanup
- JSON result parsing and validation
- Comprehensive error handling and timeout management
- Windows PowerShell compatibility
"""

import json
import logging
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from .base.exceptions import OperationError


class TypeScriptExecutionError(OperationError):
    """Exception raised when TypeScript execution fails."""
    
    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        exit_code: Optional[int] = None,
        stdout: Optional[str] = None,
        stderr: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, operation_name="typescript_execution", **kwargs)
        self.command = command
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr


@dataclass
class ExecutionResult:
    """Container for TypeScript execution results."""
    success: bool
    data: Optional[Dict[str, Any]]
    execution_time: float
    command: str
    exit_code: int
    stdout: str
    stderr: str
    temp_files_cleaned: bool = False


class TypeScriptExecutor:
    """
    Python subprocess interface to execute TypeScript Canvas interface components.
    
    This class provides the critical bridge that allows Python code to execute
    TypeScript Canvas interface components via subprocess. It handles all the
    complexities of cross-language execution including environment validation,
    script creation, process management, and result parsing.
    
    Features:
    - Cross-platform subprocess execution (Windows PowerShell compatible)
    - Environment validation and dependency checking
    - Temporary script creation with automatic cleanup
    - JSON result parsing with validation
    - Timeout handling and process management
    - Comprehensive error reporting
    """

    def __init__(self, canvas_interface_path: str):
        """
        Initialize TypeScript executor.
        
        Args:
            canvas_interface_path: Path to canvas-interface directory
        """
        self.canvas_path = Path(canvas_interface_path)
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Track temporary files for cleanup
        self._temp_files: List[Path] = []
        
        self.logger.info(f"TypeScript Executor initialized with path: {self.canvas_path}")

    def validate_execution_environment(self) -> Dict[str, Any]:
        """
        Validate TypeScript execution environment prerequisites.
        
        Returns:
            Dictionary with validation results:
            - valid: bool - Whether environment is valid for execution
            - errors: List[str] - Critical errors that prevent execution
            - warnings: List[str] - Non-critical issues that should be noted
            - node_version: str - Detected Node.js version
            - tsx_available: bool - Whether tsx is available
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'node_version': None,
            'npx_available': False,
            'tsx_available': False
        }
        
        try:
            # Check Node.js availability and version
            try:
                result = subprocess.run(
                    ['node', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True  # Windows compatibility
                )
                if result.returncode == 0:
                    validation_result['node_version'] = result.stdout.strip()
                    # Check if version is 16+
                    version_num = result.stdout.strip().replace('v', '')
                    major_version = int(version_num.split('.')[0])
                    if major_version < 16:
                        validation_result['warnings'].append(f"Node.js version {version_num} detected. Version 16+ recommended.")
                else:
                    validation_result['errors'].append("Node.js not found or not accessible")
                    validation_result['valid'] = False
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
                validation_result['errors'].append(f"Node.js check failed: {str(e)}")
                validation_result['valid'] = False

            # Check npx availability
            try:
                result = subprocess.run(
                    ['npx', '--version'],
                    capture_output=True,
                    text=True,
                    timeout=10,
                    shell=True  # Windows compatibility
                )
                if result.returncode == 0:
                    validation_result['npx_available'] = True
                else:
                    validation_result['errors'].append("npx not found or not accessible")
                    validation_result['valid'] = False
            except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError) as e:
                validation_result['errors'].append(f"npx check failed: {str(e)}")
                validation_result['valid'] = False

            # Check tsx availability
            if validation_result['npx_available']:
                try:
                    result = subprocess.run(
                        ['npx', 'tsx', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=15,
                        shell=True,  # Windows compatibility
                        cwd=str(self.canvas_path)  # Execute from canvas-interface directory
                    )
                    if result.returncode == 0:
                        validation_result['tsx_available'] = True
                    else:
                        validation_result['errors'].append(f"tsx not available: {result.stderr}")
                        validation_result['valid'] = False
                except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                    validation_result['errors'].append(f"tsx check failed: {str(e)}")
                    validation_result['valid'] = False

            # Check canvas-interface directory structure
            if not self.canvas_path.exists():
                validation_result['errors'].append(f"Canvas interface path not found: {self.canvas_path}")
                validation_result['valid'] = False
            else:
                # Check for required files
                required_files = [
                    "staging/canvas-data-constructor.ts",
                    "staging/canvas-staging-data.ts",
                    "package.json"
                ]
                
                for file_path in required_files:
                    full_path = self.canvas_path / file_path
                    if not full_path.exists():
                        validation_result['warnings'].append(f"Required file not found: {file_path}")

                # Check if node_modules exists (dependencies installed)
                node_modules_path = self.canvas_path / "node_modules"
                if not node_modules_path.exists():
                    validation_result['warnings'].append("node_modules not found - dependencies may not be installed")

        except Exception as e:
            validation_result['errors'].append(f"Environment validation error: {str(e)}")
            validation_result['valid'] = False
        
        return validation_result

    async def execute_course_data_constructor(self, course_id: int) -> Dict[str, Any]:
        """
        Execute TypeScript CanvasDataConstructor and return JSON results.
        
        Args:
            course_id: Canvas course ID to process
            
        Returns:
            Dictionary with Canvas course data from TypeScript execution
            
        Raises:
            TypeScriptExecutionError: If execution fails
        """
        self.logger.info(f"Executing TypeScript CanvasDataConstructor for course {course_id}")
        
        # Create temporary execution script
        temp_script = self._create_course_execution_script(course_id)
        
        try:
            # Execute TypeScript via subprocess
            result = await self._execute_typescript_script(temp_script, timeout=300)  # 5-minute timeout
            
            if not result.success:
                raise TypeScriptExecutionError(
                    f"TypeScript execution failed for course {course_id}",
                    command=result.command,
                    exit_code=result.exit_code,
                    stdout=result.stdout,
                    stderr=result.stderr
                )
            
            self.logger.info(f"TypeScript execution completed in {result.execution_time:.2f}s")
            return result.data
            
        finally:
            # Always cleanup temporary files
            self._cleanup_temp_files()

    def execute_data_constructor_sync(self, course_id: int) -> Dict[str, Any]:
        """
        Synchronous version of execute_course_data_constructor.
        
        Args:
            course_id: Canvas course ID to process
            
        Returns:
            Dictionary with Canvas course data from TypeScript execution
        """
        import asyncio
        return asyncio.run(self.execute_course_data_constructor(course_id))

    def _create_course_execution_script(self, course_id: int) -> Path:
        """
        Create temporary TypeScript execution script for course data constructor.
        
        Args:
            course_id: Canvas course ID to process
            
        Returns:
            Path to temporary script file
        """
        # Create temporary file with .ts extension inside canvas-interface directory
        # This ensures relative imports work correctly
        temp_script = self.canvas_path / f"temp_execute_course_{course_id}.ts"
        
        # Generate execution script content
        script_content = f'''
/**
 * Temporary execution script for Canvas Data Constructor
 * Generated by TypeScript Executor for course {course_id}
 */

import {{ CanvasDataConstructor }} from './staging/canvas-data-constructor';

async function executeCanvasDataConstructor() {{
    try {{
        console.log('🚀 Starting Canvas Data Constructor execution...');
        
        const constructor = new CanvasDataConstructor();
        const courseData = await constructor.constructCourseData({course_id});
        
        // Convert to JSON-serializable format for Python consumption
        const result = {{
            success: true,
            course_id: {course_id},
            course: {{
                id: courseData.id,
                name: courseData.name,
                course_code: courseData.course_code,
                workflow_state: courseData.workflow_state,
                start_at: courseData.start_at,
                end_at: courseData.end_at,
                calendar: courseData.calendar
            }},
            students: courseData.students.map(student => ({{
                id: student.id,
                user_id: student.user_id,
                created_at: student.created_at,
                last_activity_at: student.last_activity_at,
                current_score: student.current_score,
                final_score: student.final_score,
                user: student.user,
                submitted_assignments: student.submitted_assignments || [],
                missing_assignments: student.missing_assignments || []
            }})),
            modules: courseData.modules.map(module => ({{
                id: module.id,
                name: module.name,
                position: module.position,
                published: module.published,
                assignments: module.assignments.map(assignment => ({{
                    id: assignment.id,
                    position: assignment.position,
                    published: assignment.published,
                    title: assignment.title,
                    type: assignment.type,
                    url: assignment.url,
                    content_details: assignment.content_details,
                    module_id: module.id,  // Add module_id for database relations
                    // Canvas API timestamp fields from enhancement
                    created_at: assignment.created_at,
                    updated_at: assignment.updated_at,
                    due_at: assignment.due_at,
                    lock_at: assignment.lock_at,
                    unlock_at: assignment.unlock_at,
                    workflow_state: assignment.workflow_state,
                    assignment_type: assignment.assignment_type
                }}))
            }})),
            metadata: {{
                execution_timestamp: new Date().toISOString(),
                total_students: courseData.students.length,
                total_modules: courseData.modules.length,
                total_assignments: courseData.getAllAssignments().length
            }}
        }};
        
        // Output JSON result for Python to parse
        console.log('\\n===CANVAS_BRIDGE_RESULT_START===');
        console.log(JSON.stringify(result, null, 2));
        console.log('===CANVAS_BRIDGE_RESULT_END===');
        
    }} catch (error) {{
        console.error('💥 Canvas Data Constructor execution failed:', error);
        
        // Output error in structured format
        const errorResult = {{
            success: false,
            course_id: {course_id},
            error: {{
                message: error.message || 'Unknown error',
                name: error.name || 'Error',
                stack: error.stack || 'No stack trace available'
            }},
            execution_timestamp: new Date().toISOString()
        }};
        
        console.log('\\n===CANVAS_BRIDGE_RESULT_START===');
        console.log(JSON.stringify(errorResult, null, 2));
        console.log('===CANVAS_BRIDGE_RESULT_END===');
        
        process.exit(1);
    }}
}}

// Execute the function
executeCanvasDataConstructor();
'''
        
        # Write script to temporary file
        with open(temp_script, 'w', encoding='utf-8') as f:
            f.write(script_content)
        
        # Track temporary file for cleanup
        self._temp_files.append(temp_script)
        
        self.logger.debug(f"Created temporary execution script: {temp_script}")
        return temp_script

    async def _execute_typescript_script(
        self, 
        script_path: Path, 
        timeout: int = 300
    ) -> ExecutionResult:
        """
        Execute TypeScript script via subprocess.
        
        Args:
            script_path: Path to TypeScript script to execute
            timeout: Execution timeout in seconds
            
        Returns:
            ExecutionResult with execution details and parsed data
        """
        command = ['npx', 'tsx', str(script_path)]
        command_str = ' '.join(command)
        
        start_time = datetime.now()
        
        try:
            # Execute subprocess with timeout
            process = subprocess.run(
                command,
                cwd=str(self.canvas_path),
                capture_output=True,
                text=True,
                timeout=timeout,
                shell=True,  # Windows compatibility
                encoding='utf-8'
            )
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # Parse result from stdout
            parsed_data = None
            if process.returncode == 0:
                parsed_data = self._parse_canvas_result(process.stdout)
            
            return ExecutionResult(
                success=process.returncode == 0,
                data=parsed_data,
                execution_time=execution_time,
                command=command_str,
                exit_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr
            )
            
        except subprocess.TimeoutExpired as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            error_msg = f"TypeScript execution timed out after {timeout}s"
            self.logger.error(error_msg)
            
            return ExecutionResult(
                success=False,
                data=None,
                execution_time=execution_time,
                command=command_str,
                exit_code=-1,
                stdout=str(e.stdout) if e.stdout else "",
                stderr=f"Timeout after {timeout}s: {str(e.stderr) if e.stderr else ''}"
            )
            
        except Exception as e:
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            error_msg = f"TypeScript execution error: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            
            return ExecutionResult(
                success=False,
                data=None,
                execution_time=execution_time,
                command=command_str,
                exit_code=-2,
                stdout="",
                stderr=error_msg
            )

    def _parse_canvas_result(self, stdout: str) -> Dict[str, Any]:
        """
        Parse Canvas result from TypeScript stdout.
        
        Args:
            stdout: Raw stdout from TypeScript execution
            
        Returns:
            Parsed Canvas data dictionary
            
        Raises:
            TypeScriptExecutionError: If parsing fails
        """
        try:
            # Look for result markers in stdout
            start_marker = "===CANVAS_BRIDGE_RESULT_START==="
            end_marker = "===CANVAS_BRIDGE_RESULT_END==="
            
            start_idx = stdout.find(start_marker)
            end_idx = stdout.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                raise TypeScriptExecutionError(
                    "Canvas result markers not found in TypeScript output",
                    stdout=stdout[:1000]  # Include first 1000 chars for debugging
                )
            
            # Extract JSON content between markers
            json_content = stdout[start_idx + len(start_marker):end_idx].strip()
            
            if not json_content:
                raise TypeScriptExecutionError(
                    "Empty JSON content in TypeScript output",
                    stdout=stdout[:1000]
                )
            
            # Parse JSON
            result = json.loads(json_content)
            
            # Validate result structure
            if not isinstance(result, dict):
                raise TypeScriptExecutionError(
                    f"Invalid result type: expected dict, got {type(result)}"
                )
            
            if not result.get('success', False):
                error_info = result.get('error', {})
                raise TypeScriptExecutionError(
                    f"TypeScript execution returned error: {error_info.get('message', 'Unknown error')}",
                    stdout=stdout[:1000]
                )
            
            self.logger.debug(f"Successfully parsed Canvas result: {len(json_content)} chars")
            return result
            
        except json.JSONDecodeError as e:
            raise TypeScriptExecutionError(
                f"Failed to parse JSON from TypeScript output: {str(e)}",
                stdout=stdout[:1000]
            )
        except Exception as e:
            raise TypeScriptExecutionError(
                f"Error parsing Canvas result: {str(e)}",
                stdout=stdout[:1000]
            )

    def _cleanup_temp_files(self) -> None:
        """Clean up temporary files created during execution."""
        cleaned_files = 0
        
        for temp_path in self._temp_files:
            try:
                if temp_path.exists():
                    if temp_path.is_file():
                        temp_path.unlink()
                        cleaned_files += 1
                    elif temp_path.is_dir():
                        shutil.rmtree(temp_path)
                        cleaned_files += 1
            except Exception as e:
                self.logger.warning(f"Failed to clean up temporary file {temp_path}: {e}")
        
        self._temp_files.clear()
        
        if cleaned_files > 0:
            self.logger.debug(f"Cleaned up {cleaned_files} temporary files")

    def get_executor_status(self) -> Dict[str, Any]:
        """
        Get current status of TypeScript executor.
        
        Returns:
            Dictionary with executor status information
        """
        try:
            env_validation = self.validate_execution_environment()
            
            return {
                'canvas_interface_path': str(self.canvas_path),
                'path_exists': self.canvas_path.exists(),
                'environment_validation': env_validation,
                'temp_files_count': len(self._temp_files),
                'temp_files': [str(p) for p in self._temp_files]
            }
        except Exception as e:
            return {
                'error': f"Failed to get executor status: {str(e)}",
                'canvas_interface_path': str(self.canvas_path),
                'path_exists': self.canvas_path.exists() if hasattr(self, 'canvas_path') else False
            }

    def __del__(self):
        """Cleanup temporary files on destruction."""
        try:
            self._cleanup_temp_files()
        except Exception:
            pass  # Ignore cleanup errors during destruction


# Convenience functions for direct execution
def execute_canvas_course_data(
    course_id: int, 
    canvas_interface_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to execute Canvas course data constructor.
    
    Args:
        course_id: Canvas course ID to process
        canvas_interface_path: Optional path to canvas-interface directory
        
    Returns:
        Dictionary with Canvas course data
    """
    if not canvas_interface_path:
        # Default to project root + canvas-interface
        canvas_interface_path = str(Path(__file__).parent.parent.parent / "canvas-interface")
    
    executor = TypeScriptExecutor(canvas_interface_path)
    return executor.execute_data_constructor_sync(course_id)


def validate_typescript_environment(
    canvas_interface_path: Optional[str] = None
) -> Dict[str, Any]:
    """
    Convenience function to validate TypeScript execution environment.
    
    Args:
        canvas_interface_path: Optional path to canvas-interface directory
        
    Returns:
        Dictionary with validation results
    """
    if not canvas_interface_path:
        # Default to project root + canvas-interface
        canvas_interface_path = str(Path(__file__).parent.parent.parent / "canvas-interface")
    
    executor = TypeScriptExecutor(canvas_interface_path)
    return executor.validate_execution_environment()