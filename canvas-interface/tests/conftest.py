"""
Canvas Interface Test Configuration

Extends the database pytest infrastructure to support testing TypeScript 
canvas business logic through Python integration points.
"""

import pytest
import subprocess
import json
import tempfile
import os
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from unittest.mock import Mock, patch

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import database test fixtures to maintain consistency
from database.tests.conftest import (
    test_db_config, 
    db_manager, 
    db_session,
    sample_test_data,
    mock_canvas_api_response
)

# Re-export database fixtures for canvas-interface tests that need them
__all__ = ['test_db_config', 'db_manager', 'db_session', 'sample_test_data', 'mock_canvas_api_response']


class CanvasBusinessLogicTester:
    """
    Python wrapper for testing TypeScript canvas business logic.
    
    Provides a pytest-friendly interface to canvas-interface components
    while maintaining the excellent testing patterns from the database layer.
    """
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.canvas_interface_path = self.project_root / 'canvas-interface'
    
    def _get_npx_command(self) -> str:
        """Get the npx command - simplified for shell execution."""
        return 'npx'
        
    def run_typescript_test_function(self, module_path: str, function_name: str, args: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Execute a TypeScript function and return its result for testing.
        
        Args:
            module_path: Path to TypeScript module (e.g., "staging/canvas-data-constructor")
            function_name: Name of function to test
            args: Arguments to pass to the function
            
        Returns:
            Dict containing function result or error information
        """
        if args is None:
            args = {}
            
        # Create test runner script
        test_script = f"""
import {{ {function_name} }} from './{module_path}';

async function runTest() {{
    try {{
        const result = await {function_name}({json.dumps(args) if args else ''});
        console.log(JSON.stringify({{ success: true, result: result }}));
    }} catch (error) {{
        console.log(JSON.stringify({{ 
            success: false, 
            error: error.message,
            stack: error.stack 
        }}));
    }}
}}

runTest();
        """
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, dir=self.canvas_interface_path) as f:
            f.write(test_script)
            temp_file = f.name
            
        try:
            # Execute with tsx - use full path on Windows
            npx_cmd = self._get_npx_command()
            result = subprocess.run(
                [npx_cmd, 'tsx', temp_file],
                cwd=self.canvas_interface_path,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True  # Use shell on Windows to resolve PATH
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"TypeScript execution failed: {result.stderr}",
                    "stdout": result.stdout
                }
                
            # Parse JSON response
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": f"Invalid JSON response: {result.stdout}",
                    "raw_output": result.stdout
                }
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file)
            except (FileNotFoundError, PermissionError):
                pass  # Ignore cleanup errors
    
    def test_canvas_data_model_method(self, class_name: str, method_name: str, 
                                    test_data: Dict[str, Any], expected_result: Any = None) -> Dict[str, Any]:
        """
        Test methods on Canvas staging data models.
        
        Args:
            class_name: Name of the Canvas staging class
            method_name: Method to test
            test_data: Data to create the object with
            expected_result: Expected result (for assertions)
            
        Returns:
            Test execution result
        """
        test_script = f"""
import {{ {class_name} }} from './staging/canvas-staging-data';

const testData = {json.dumps(test_data)};
const obj = new {class_name}(testData);

try {{
    const result = obj.{method_name}();
    console.log(JSON.stringify({{ 
        success: true, 
        result: result,
        class_name: "{class_name}",
        method_name: "{method_name}"
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message,
        class_name: "{class_name}",
        method_name: "{method_name}"
    }}));
}}
        """
        
        return self._execute_test_script(test_script)
    
    def _execute_test_script(self, script_content: str) -> Dict[str, Any]:
        """Execute a test script and return parsed results."""
        # Split imports from the rest of the script
        lines = script_content.strip().split('\n')
        import_lines = []
        code_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('export '):
                import_lines.append(line)
            else:
                code_lines.append(line)
        
        # Reconstruct with imports at top level and rest in async function
        imports_section = '\n'.join(import_lines)
        code_section = '\n'.join(code_lines)
        
        wrapped_script = f"""{imports_section}

(async () => {{
{code_section}
}})().catch(error => {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message,
        stack: error.stack 
    }}));
}});
        """
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.ts', delete=False, dir=self.canvas_interface_path) as f:
            f.write(wrapped_script)
            temp_file = f.name
            
        try:
            npx_cmd = self._get_npx_command()
            result = subprocess.run(
                [npx_cmd, 'tsx', temp_file],
                cwd=self.canvas_interface_path,
                capture_output=True,
                text=True,
                timeout=30,
                shell=True  # Use shell on Windows to resolve PATH
            )
            
            if result.returncode != 0:
                return {
                    "success": False,
                    "error": f"Execution failed: {result.stderr}",
                    "stdout": result.stdout
                }
                
            try:
                return json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": f"Invalid JSON: {result.stdout}",
                    "raw_output": result.stdout
                }
                
        finally:
            try:
                os.unlink(temp_file)
            except (FileNotFoundError, PermissionError):
                pass


@pytest.fixture(scope="session")
def canvas_business_logic_tester():
    """
    Fixture providing the canvas business logic testing interface.
    
    Allows pytest to test TypeScript canvas business logic while maintaining
    the excellent testing patterns from the database layer.
    """
    return CanvasBusinessLogicTester(project_root)


@pytest.fixture(scope="function")
def enhanced_mock_canvas_api_response():
    """Comprehensive Canvas API response fixtures for realistic testing."""
    return {
        'courses': [
            {
                'id': 7982015,
                'name': 'Web Development Bootcamp',
                'course_code': 'WEB-DEV-2024',
                'workflow_state': 'available',
                'start_at': '2024-01-15T08:00:00Z',
                'end_at': '2024-05-15T17:00:00Z',
                'total_points': 1000,
                'calendar': {'ics': None}
            }
        ],
        'students': [
            {
                'id': 111929282,
                'name': 'John Smith', 
                'login_id': 'john.smith@university.edu',
                'current_score': 85.5,
                'final_score': 85.5,
                'last_activity_at': '2024-10-10T14:30:00Z',
                'enrollment_state': 'active'
            },
            {
                'id': 111929283,
                'name': 'Jane Doe',
                'login_id': 'jane.doe@university.edu', 
                'current_score': 78.0,
                'final_score': 89.0,  # Gap indicates missing assignments
                'last_activity_at': '2024-10-12T09:15:00Z',
                'enrollment_state': 'active'
            },
            {
                'id': 111929284,
                'name': 'Bob Johnson',
                'login_id': 'bob.johnson@university.edu',
                'current_score': 65.0,
                'final_score': 65.0,
                'last_activity_at': '2024-10-05T16:45:00Z',  # Less recent activity
                'enrollment_state': 'active'
            }
        ],
        'modules': [
            {
                'id': 12345,
                'name': 'HTML Fundamentals',
                'position': 1,
                'published': True,
                'items': [
                    {
                        'id': 67890,
                        'title': 'HTML Structure Assignment',
                        'type': 'Assignment',
                        'content_id': 445566
                    },
                    {
                        'id': 67891, 
                        'title': 'HTML Forms Quiz',
                        'type': 'Quiz',
                        'content_id': 445567
                    }
                ]
            },
            {
                'id': 12346,
                'name': 'CSS Styling',
                'position': 2,
                'published': True,
                'items': [
                    {
                        'id': 67892,
                        'title': 'CSS Layout Project',
                        'type': 'Assignment', 
                        'content_id': 445568
                    }
                ]
            },
            {
                'id': 12347,
                'name': 'JavaScript Basics',
                'position': 3,
                'published': False,  # Unpublished module for testing
                'items': []
            }
        ],
        'assignments': [
            {
                'id': 445566,
                'course_id': 7982015,
                'module_id': 12345,
                'name': 'HTML Structure Assignment',
                'type': 'assignment',
                'points_possible': 100,
                'published': True,
                'due_at': '2024-02-15T23:59:00Z'
            },
            {
                'id': 445567,
                'course_id': 7982015,
                'module_id': 12345,
                'name': 'HTML Forms Quiz',
                'type': 'quiz',
                'points_possible': 50,
                'published': True,
                'due_at': '2024-02-20T23:59:00Z'
            },
            {
                'id': 445568,
                'course_id': 7982015,
                'module_id': 12346,
                'name': 'CSS Layout Project',
                'type': 'assignment',
                'points_possible': 150,
                'published': True,
                'due_at': '2024-03-10T23:59:00Z'
            }
        ],
        'enrollments': [
            {
                'user_id': 111929282,
                'course_id': 7982015,
                'enrollment_state': 'active',
                'grades': {'current_score': 85.5, 'final_score': 85.5},
                'user': {'id': 111929282, 'name': 'John Smith', 'login_id': 'john.smith@university.edu'}
            },
            {
                'user_id': 111929283,
                'course_id': 7982015,
                'enrollment_state': 'active',
                'grades': {'current_score': 78.0, 'final_score': 89.0},
                'user': {'id': 111929283, 'name': 'Jane Doe', 'login_id': 'jane.doe@university.edu'}
            },
            {
                'user_id': 111929284,
                'course_id': 7982015,
                'enrollment_state': 'active',
                'grades': {'current_score': 65.0, 'final_score': 65.0},
                'user': {'id': 111929284, 'name': 'Bob Johnson', 'login_id': 'bob.johnson@university.edu'}
            }
        ],
        # Error scenarios for testing
        'error_scenarios': {
            'api_timeout': {'error': 'Request timeout', 'status_code': 408},
            'rate_limit': {'error': 'Rate limit exceeded', 'status_code': 429},
            'not_found': {'error': 'Course not found', 'status_code': 404},
            'unauthorized': {'error': 'Unauthorized', 'status_code': 401},
            'server_error': {'error': 'Internal server error', 'status_code': 500}
        }
    }

@pytest.fixture
def enhanced_mock_canvas_api_response():
    """
    Enhanced Canvas API response fixtures for comprehensive testing.
    
    Extends the database layer's mock_canvas_api_response with more realistic
    and comprehensive test data for canvas business logic testing.
    """
    return {
        'courses': [
            {
                'id': 7982015,
                'name': 'Web Development Bootcamp',
                'course_code': 'WEB-101',
                'total_students': 25,
                'total_points': 1000,
                'start_at': '2024-09-01T00:00:00Z',
                'end_at': '2024-12-15T23:59:59Z',
                'calendar_ics': 'https://canvas.example.com/calendar.ics'
            },
            {
                'id': 7982016,
                'name': 'Advanced JavaScript',
                'course_code': 'JS-201',
                'total_students': 18,
                'total_points': 1200,
                'start_at': '2024-09-01T00:00:00Z',
                'end_at': '2024-12-15T23:59:59Z'
            }
        ],
        'students': [
            {
                'id': 111929282,
                'user_id': 111929282,
                'created_at': '2024-09-01T00:00:00Z',
                'last_activity_at': '2024-10-14T10:30:00Z',
                'grades': {
                    'current_score': 85,
                    'final_score': 90
                },
                'user': {
                    'id': 111929282,
                    'name': 'John Smith',
                    'sortable_name': 'Smith, John',
                    'login_id': 'john.smith@example.com'
                }
            },
            {
                'id': 111929283,
                'user_id': 111929283,
                'created_at': '2024-09-01T00:00:00Z',
                'last_activity_at': '2024-10-13T15:45:00Z',
                'grades': {
                    'current_score': 78,
                    'final_score': 78  # No missing assignments
                },
                'user': {
                    'id': 111929283,
                    'name': 'Jane Doe',
                    'sortable_name': 'Doe, Jane',
                    'login_id': 'jane.doe@example.com'
                }
            },
            {
                'id': 111929284,
                'user_id': 111929284,
                'created_at': '2024-09-01T00:00:00Z',
                'last_activity_at': '2024-10-10T09:20:00Z',
                'grades': {
                    'current_score': 65,
                    'final_score': 82  # Has missing assignments
                },
                'user': {
                    'id': 111929284,
                    'name': 'Bob Johnson',
                    'sortable_name': 'Johnson, Bob',
                    'login_id': 'bob.johnson@example.com'
                }
            }
        ],
        'modules': [
            {
                'id': 301,
                'name': 'HTML Fundamentals',
                'position': 1,
                'published': True,
                'items_count': 5,
                'items': [
                    {
                        'id': 2001,
                        'position': 3,
                        'published': True,
                        'title': 'HTML Structure Assignment',
                        'type': 'Assignment',
                        'url': 'https://canvas.example.com/courses/7982015/assignments/2001',
                        'content_details': {
                            'points_possible': 100
                        }
                    },
                    {
                        'id': 2002,
                        'position': 5,
                        'published': True,
                        'title': 'HTML Forms Quiz',
                        'type': 'Quiz',
                        'url': 'https://canvas.example.com/courses/7982015/quizzes/2002',
                        'content_details': {
                            'points_possible': 50
                        }
                    }
                ]
            },
            {
                'id': 302,
                'name': 'CSS Styling',
                'position': 2,
                'published': True,
                'items_count': 7,
                'items': [
                    {
                        'id': 2003,
                        'position': 4,
                        'published': True,
                        'title': 'CSS Layout Project',
                        'type': 'Assignment',
                        'url': 'https://canvas.example.com/courses/7982015/assignments/2003',
                        'content_details': {
                            'points_possible': 150
                        }
                    }
                ]
            },
            {
                'id': 303,
                'name': 'JavaScript Basics',
                'position': 3,
                'published': False,  # Unpublished module
                'items_count': 8,
                'items': []
            }
        ],
        'assignments': [
            {
                'id': 2001,
                'course_id': 7982015,
                'module_id': 301,
                'name': 'HTML Structure Assignment',
                'type': 'assignment',
                'points_possible': 100,
                'published': True,
                'due_at': '2024-09-15T23:59:59Z',
                'module_position': 3
            },
            {
                'id': 2002,
                'course_id': 7982015,
                'module_id': 301,
                'name': 'HTML Forms Quiz',
                'type': 'quiz',
                'points_possible': 50,
                'published': True,
                'due_at': '2024-09-20T23:59:59Z',
                'module_position': 5
            },
            {
                'id': 2003,
                'course_id': 7982015,
                'module_id': 302,
                'name': 'CSS Layout Project',
                'type': 'assignment',
                'points_possible': 150,
                'published': True,
                'due_at': '2024-10-01T23:59:59Z',
                'module_position': 4
            }
        ],
        'enrollments': [
            {
                'student_id': 111929282,
                'course_id': 7982015,
                'enrollment_status': 'active',
                'enrollment_date': '2024-09-01T00:00:00Z'
            },
            {
                'student_id': 111929283,
                'course_id': 7982015,
                'enrollment_status': 'active',
                'enrollment_date': '2024-09-01T00:00:00Z'
            },
            {
                'student_id': 111929284,
                'course_id': 7982015,
                'enrollment_status': 'active',
                'enrollment_date': '2024-09-01T00:00:00Z'
            }
        ]
    }


@pytest.fixture(scope="function")
def mock_canvas_api_client():
    """
    Mock Canvas API client that returns predictable responses.
    
    This can be patched in tests to avoid actual API calls while testing
    canvas business logic that depends on API responses.
    """
    mock_client = Mock()
    
    # Configure mock responses
    mock_client.get_courses.return_value = {
        'success': True,
        'data': [{'id': 7982015, 'name': 'Test Course'}]
    }
    
    mock_client.get_course_students.return_value = {
        'success': True,
        'students': [{'id': 111929282, 'name': 'Test Student', 'current_score': 85}]
    }
    
    mock_client.get_course_assignments.return_value = {
        'success': True,
        'assignments': [{'id': 2001, 'name': 'Test Assignment', 'points_possible': 100}]
    }
    
    return mock_client


# Test helper functions that integrate with pytest patterns
def assert_canvas_business_logic_result(result: Dict[str, Any], expected_type: type = None, 
                                      expected_properties: List[str] = None):
    """
    Assert helper for canvas business logic test results.
    
    Follows pytest assertion patterns while handling TypeScript execution results.
    
    Args:
        result: Result from canvas_business_logic_tester
        expected_type: Expected type of the result (for validation)
        expected_properties: List of properties that should be present (at least one must be present)
    """
    assert result['success'], f"Canvas business logic test failed: {result.get('error', 'Unknown error')}"
    
    if expected_properties:
        actual_result = result['result']
        # Check if at least one expected property is present (for alternative scenarios)
        found_properties = [prop for prop in expected_properties if prop in actual_result]
        assert len(found_properties) > 0, f"Expected at least one of {expected_properties} not found in result: {actual_result}"
    
    # Additional type checking could be added here
    return result['result']


def create_mock_canvas_student_data(student_id: int = 111929282, 
                                   current_score: int = 85, 
                                   final_score: int = 90) -> Dict[str, Any]:
    """
    Create mock Canvas student data for testing.
    
    Follows the same pattern as database test data fixtures but for Canvas objects.
    Matches the structure expected by CanvasStudentStaging TypeScript class.
    """
    return {
        'id': student_id,
        'user_id': student_id,
        'created_at': '2024-09-01T00:00:00Z',
        'last_activity_at': '2024-10-14T10:30:00Z',
        'grades': {
            'current_score': current_score,
            'final_score': final_score
        },
        'user': {
            'id': student_id,
            'name': f'Test Student {student_id}',
            'sortable_name': f'Student {student_id}, Test',
            'login_id': f'student{student_id}@example.com'
        }
    }


def create_mock_canvas_course_data(course_id: int = 7982015, 
                                  total_students: int = 25) -> Dict[str, Any]:
    """
    Create mock Canvas course data for testing.
    """
    return {
        'id': course_id,
        'name': f'Test Course {course_id}',
        'course_code': f'TEST-{course_id}',
        'total_students': total_students,
        'total_points': 1000,
        'start_at': '2024-09-01T00:00:00Z',
        'end_at': '2024-12-15T23:59:59Z'
    }


# Pytest markers for canvas interface tests (extending database markers)
def pytest_configure(config):
    """Configure custom pytest markers for canvas interface testing."""
    config.addinivalue_line(
        "markers", "canvas_unit: Unit tests for canvas business logic"
    )
    config.addinivalue_line(
        "markers", "canvas_integration: Integration tests with canvas API"
    )
    config.addinivalue_line(
        "markers", "canvas_data_transformation: Tests for Canvas data transformation logic"
    )
    config.addinivalue_line(
        "markers", "canvas_mock: Tests that use mocked Canvas API responses"
    )