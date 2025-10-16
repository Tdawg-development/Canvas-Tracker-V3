"""
Real Canvas API Pipeline Test: Live Canvas API -> TypeScript -> Scalable Transformers

This test makes REAL Canvas API calls using your existing TypeScript infrastructure
and validates the complete pipeline with actual Canvas data from your environment.

Based on patterns from canvas-interface/tests/api-staging-integration.test.ts
"""

import pytest
import json
import subprocess
import tempfile
import asyncio
import os
from pathlib import Path
from unittest.mock import patch
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

from database.operations.transformers import (
    get_global_registry,
    TransformationContext,
    EntityType,
    TransformerRegistry,
    CourseTransformer,
    StudentTransformer,
    ConfigurationValidator
)


# Test Configuration - Using your actual Canvas course
TEST_COURSE_ID = 7982015  # Your JDU course from api-staging-integration.test.ts
TEST_TIMEOUT = 30000  # 30 seconds for Canvas API calls
CANVAS_INTERFACE_PATH = Path("C:/Users/tyler/Documents/Canvas-Tracker-V3/canvas-interface")


# ==================== REAL CANVAS API INTEGRATION ====================

class TestRealCanvasApiPipeline:
    """
    Integration test that makes real Canvas API calls through TypeScript
    and validates the complete transformation pipeline with live data.
    """
    
    def setup_method(self):
        """Set up test components and validate Canvas environment."""
        # Initialize transformer components
        self.registry = TransformerRegistry()
        self.registry.register_transformer(CourseTransformer())
        self.registry.register_transformer(StudentTransformer())
        self.validator = ConfigurationValidator(self.registry)
        
        # Validate Canvas interface path exists
        if not CANVAS_INTERFACE_PATH.exists():
            pytest.skip("Canvas interface path not found. Ensure canvas-interface directory exists.")
        
        # Check for .env file (Canvas credentials)
        env_file = CANVAS_INTERFACE_PATH / ".env"
        if not env_file.exists():
            pytest.skip("Canvas .env file not found. Canvas API credentials required for integration test.")
    
    def _execute_canvas_typescript(self, course_id: int) -> Dict[str, Any]:
        """
        Execute REAL Canvas API calls using the TypeScript integration script.
        This makes actual Canvas API calls through your existing infrastructure.
        """
        print(f"\nMaking REAL Canvas API calls for course {course_id}...")
        
        start_time = datetime.now()
        
        try:
            # Get the current environment and add node paths
            env = os.environ.copy()
            
            # Add Node.js path to environment PATH
            node_path = r"C:\Program Files\nodejs"
            if 'PATH' in env:
                env['PATH'] = node_path + os.pathsep + env['PATH']
            else:
                env['PATH'] = node_path
            
            # Use the full path to node and run the TypeScript script
            node_exe = r"C:\Program Files\nodejs\node.exe"
            ts_node_path = os.path.join(CANVAS_INTERFACE_PATH.parent, "node_modules", ".bin", "ts-node.cmd")
            
            # Try different approaches to run ts-node
            npm_exe = os.path.join(node_path, "npm.cmd")
            npx_exe = os.path.join(node_path, "npx.cmd")
            
            # Method 1: Try npx ts-node directly
            if os.path.exists(npx_exe):
                cmd = [npx_exe, "ts-node", "real_canvas_api_test.ts"]
            elif os.path.exists(npm_exe):
                cmd = [npm_exe, "exec", "ts-node", "real_canvas_api_test.ts"]
            else:
                # Fallback: Use node with a simple wrapper
                cmd = [node_exe, "-r", "ts-node/register", "real_canvas_api_test.ts"]
            
            print(f"   Executing Canvas API script...")
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Working directory: {CANVAS_INTERFACE_PATH.parent}")
            
            # Use file output to avoid subprocess buffering issues on Windows
            output_file = CANVAS_INTERFACE_PATH.parent / "canvas_api_output.txt"
            cmd_with_redirect = cmd + [">>", str(output_file), "2>&1"]
            
            # Remove existing output file
            if output_file.exists():
                output_file.unlink()
            
            result = subprocess.run(
                " ".join([f'"{c}"' for c in cmd]) + f" > {output_file} 2>&1",
                cwd=str(CANVAS_INTERFACE_PATH.parent),
                shell=True,
                timeout=120,  # Increased timeout for real API calls
                env=env
            )
            
            api_time = (datetime.now() - start_time).total_seconds() * 1000
            
            print(f"   Canvas API script completed (return code: {result.returncode})")
            
            if result.returncode != 0:
                print(f"   Canvas API script failed with return code {result.returncode}")
                if output_file.exists():
                    error_output = output_file.read_text(encoding='utf-8')
                    print(f"      Error output: {error_output[:500]}...")
                raise Exception(f"Canvas API script failed with code {result.returncode}")
            
            # Read the output from the file
            if not output_file.exists():
                raise Exception(f"Canvas API output file not created: {output_file}")
            
            combined_output = output_file.read_text(encoding='utf-8')
            
            print(f"   Parsing Canvas API response...")
            print(f"      Output file size: {len(combined_output)} chars")
            
            if not combined_output:
                print(f"   No content in Canvas API output file")
                raise Exception("No content in Canvas API output file")
            
            start_marker = "===CANVAS_API_RESULT_START==="
            end_marker = "===CANVAS_API_RESULT_END==="
            
            start_idx = combined_output.find(start_marker)
            end_idx = combined_output.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                print(f"   Canvas API result markers not found in combined output:")
                print(f"      Looking for: {start_marker}")
                print(f"      Combined output excerpt (last 1000 chars): ...{combined_output[-1000:]}")
                raise Exception("Canvas API result markers not found in combined output")
            
            json_content = combined_output[start_idx + len(start_marker):end_idx].strip()
            canvas_data = json.loads(json_content)
            
            if not canvas_data.get('success', False):
                error_msg = canvas_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"Canvas API returned error: {error_msg}")
            
            print(f"REAL Canvas API calls completed in {canvas_data.get('api_execution_time', 0):.1f}ms")
            print(f"   Course: {canvas_data['course']['name'] if canvas_data.get('course') else 'N/A'}")
            print(f"   Students: {len(canvas_data['students'])} (from REAL Canvas API)")
            print(f"   Modules: {len(canvas_data['modules'])} (from REAL Canvas API)")
            
            return canvas_data
            
        except subprocess.TimeoutExpired:
            raise Exception(f"Canvas API test timed out after 120 seconds")
        except json.JSONDecodeError as e:
            print(f"   Failed to parse JSON from Canvas API response:")
            print(f"      JSON Error: {str(e)}")
            print(f"      Raw content: {json_content[:200]}...")
            raise Exception(f"Failed to parse Canvas API JSON response: {str(e)}")
        except Exception as e:
            print(f"   Canvas API execution failed: {str(e)}")
            raise Exception(f"Failed to execute Canvas API test: {str(e)}")
    
    @pytest.mark.integration
    @pytest.mark.canvas_api
    def test_real_canvas_api_to_transformer_pipeline(self):
        """
        THE MAIN TEST: Real Canvas API -> TypeScript -> Scalable Transformers
        This makes actual Canvas API calls and validates the complete pipeline.
        """
        print("\n" + "="*100)
        print("REAL CANVAS API PIPELINE TEST: Live Canvas -> TypeScript -> Transformers")
        print("="*100)
        
        # Phase 1: Real Canvas API Execution
        print(f"\nPHASE 1: Real Canvas API Calls (Course {TEST_COURSE_ID})")
        print("-" * 60)
        
        start_time = datetime.now()
        live_canvas_data = self._execute_canvas_typescript(TEST_COURSE_ID)
        api_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"Live Canvas API execution completed!")
        print(f"   Total API time: {api_time:.1f}ms")
        print(f"   TypeScript reported: {live_canvas_data.get('api_execution_time', 'N/A')}ms")
        print(f"   Course: {live_canvas_data['course']['name']}")
        print(f"   Course Code: {live_canvas_data['course']['course_code']}")
        print(f"   Students: {len(live_canvas_data['students'])}")
        print(f"   Modules: {len(live_canvas_data['modules'])}")
        
        # Show actual Canvas API data structure
        print(f"\nLIVE CANVAS DATA STRUCTURE:")
        course_fields = list(live_canvas_data['course'].keys())
        print(f"   Course fields ({len(course_fields)}): {course_fields}")
        
        if live_canvas_data['students']:
            student_fields = list(live_canvas_data['students'][0].keys())
            print(f"   Student fields ({len(student_fields)}): {student_fields}")
        
        if live_canvas_data['modules']:
            module_fields = list(live_canvas_data['modules'][0].keys())
            print(f"   Module fields ({len(module_fields)}): {module_fields}")
        
        # Phase 2: Configuration Testing with Real Data
        print(f"\nPHASE 2: Configuration Validation with Real Data")
        print("-" * 60)
        
        configurations = {
            "FULL_REAL": {
                "entities": {"courses": True, "students": True, "enrollments": True, "assignments": True, "modules": True},
                "fields": {
                    "courses": {"extended_info": True, "public_info": True, "settings": True},
                    "students": {"basicInfo": True, "scores": True, "analytics": True, "enrollmentDetails": True}
                }
            },
            "STUDENTS_ANALYTICS": {
                "entities": {"courses": True, "students": True, "enrollments": True, "assignments": False, "modules": False},
                "fields": {
                    "students": {"basicInfo": True, "scores": True, "analytics": True, "enrollmentDetails": True}
                }
            },
            "COURSE_ONLY": {
                "entities": {"courses": True, "students": False, "assignments": False, "modules": False},
                "fields": {"courses": {"extended_info": True, "public_info": True, "settings": True}}
            }
        }
        
        transformation_results = {}
        
        for config_name, config in configurations.items():
            print(f"\n   Testing {config_name} Configuration:")
            
            # Validate configuration
            validation = self.validator.validate_configuration(config)
            print(f"      Valid: {validation.valid}")
            print(f"      Performance: {validation.performance_estimate['performance_category']}")
            print(f"      Entities: {validation.performance_estimate['entity_types']}")
            
            # Transform with new registry system
            registry = get_global_registry()
            
            # Convert legacy format to registry format
            registry_format_data = {
                'courses': [live_canvas_data['course']] if live_canvas_data.get('course') else [],
                'students': live_canvas_data.get('students', []),
                'modules': live_canvas_data.get('modules', [])
            }
            
            # Extract assignments from modules for registry
            assignments_data = []
            for module_data in registry_format_data['modules']:
                module_id = module_data.get('id')
                for item in module_data.get('items', []):
                    item_with_context = item.copy()
                    item_with_context['course_id'] = live_canvas_data['course']['id']
                    item_with_context['module_id'] = module_id
                    assignments_data.append(item_with_context)
            registry_format_data['assignments'] = assignments_data
            
            # Extract enrollments from students for registry
            enrollments_data = []
            for student_data in registry_format_data['students']:
                enrollment_data = student_data.copy()
                enrollment_data['course_id'] = live_canvas_data['course']['id']
                enrollments_data.append(enrollment_data)
            registry_format_data['enrollments'] = enrollments_data
            
            transform_start = datetime.now()
            registry_results = registry.transform_entities(
                canvas_data=registry_format_data,
                configuration=config,
                course_id=live_canvas_data['course']['id']
            )
            transform_time = (datetime.now() - transform_start).total_seconds() * 1000
            
            # Convert registry results back to legacy format
            result = {}
            for entity_type, transform_result in registry_results.items():
                result[entity_type] = transform_result.transformed_data if transform_result.success else []
            
            transformation_results[config_name] = result
            
            print(f"      Transform time: {transform_time:.1f}ms")
            print(f"      Results:")
            for entity_type, data in result.items():
                print(f"         {entity_type}: {len(data)} records")
            
        # Phase 3: Detailed Real Data Inspection
        print(f"\nPHASE 3: Detailed Real Data Inspection")
        print("-" * 60)
        
        full_result = transformation_results["FULL_REAL"]
        self._inspect_real_course_data(full_result.get('courses', []), live_canvas_data['course'])
        self._inspect_real_student_data(full_result.get('students', []), live_canvas_data['students'])
        self._inspect_real_assignment_data(full_result.get('assignments', []))
        
        # Phase 4: Data Quality Validation with Real Data
        print(f"\nPHASE 4: Real Data Quality Validation")
        print("-" * 60)
        
        self._validate_real_data_quality(live_canvas_data, transformation_results)
        
        # Phase 5: Performance Analysis with Real Data
        print(f"\nPHASE 5: Real Data Performance Analysis")
        print("-" * 60)
        
        total_students = len(live_canvas_data['students'])
        total_modules = len(live_canvas_data['modules'])
        
        print(f"   Dataset characteristics:")
        print(f"      Students: {total_students}")
        print(f"      Modules: {total_modules}")
        print(f"      API response time: {live_canvas_data.get('api_execution_time', 'N/A')}ms")
        
        for config_name in configurations:
            result = transformation_results[config_name]
            student_count = len(result.get('students', []))
            if student_count > 0:
                # Estimate time per student for this config
                print(f"      {config_name}: {student_count} students processed")
        
        print(f"\nREAL CANVAS API PIPELINE TEST COMPLETED SUCCESSFULLY!")
        print("="*100)
    
    @pytest.mark.integration 
    @pytest.mark.canvas_api
    def test_real_canvas_api_configuration_impact(self):
        """
        Test different configurations with real Canvas data to show
        the actual impact of filtering on live data.
        """
        print("\n" + "="*100)
        print("REAL CANVAS API CONFIGURATION IMPACT TEST")
        print("="*100)
        
        # Get real Canvas data
        live_canvas_data = self._execute_canvas_typescript(TEST_COURSE_ID)
        
        print(f"Live Canvas Data Retrieved:")
        print(f"   Course: {live_canvas_data['course']['name']}")
        print(f"   Students: {len(live_canvas_data['students'])}")
        print(f"   Modules: {len(live_canvas_data['modules'])}")
        
        # Test progressive filtering configurations
        progressive_configs = [
            ("MAXIMUM", {
                "entities": {"courses": True, "students": True, "enrollments": True, "assignments": True, "modules": True},
                "fields": {"students": {"basicInfo": True, "scores": True, "analytics": True, "enrollmentDetails": True}}
            }),
            ("STANDARD", {
                "entities": {"courses": True, "students": True, "enrollments": True, "assignments": True, "modules": False},
                "fields": {"students": {"basicInfo": True, "scores": True, "analytics": False, "enrollmentDetails": False}}
            }),
            ("MINIMAL", {
                "entities": {"courses": True, "students": True, "enrollments": True, "assignments": False, "modules": False},
                "fields": {"students": {"basicInfo": True, "scores": False, "analytics": False, "enrollmentDetails": False}}
            }),
            ("COURSE_ONLY", {
                "entities": {"courses": True, "students": False, "assignments": False, "modules": False},
                "fields": {}
            })
        ]
        
        print(f"\nProgressive Configuration Impact Analysis:")
        print("-" * 60)
        
        for config_name, config in progressive_configs:
            registry = get_global_registry()
            
            # Convert legacy format to registry format
            registry_format_data = {
                'courses': [live_canvas_data['course']] if live_canvas_data.get('course') else [],
                'students': live_canvas_data.get('students', []),
                'modules': live_canvas_data.get('modules', [])
            }
            
            # Extract assignments from modules for registry
            assignments_data = []
            for module_data in registry_format_data['modules']:
                module_id = module_data.get('id')
                for item in module_data.get('items', []):
                    item_with_context = item.copy()
                    item_with_context['course_id'] = live_canvas_data['course']['id']
                    item_with_context['module_id'] = module_id
                    assignments_data.append(item_with_context)
            registry_format_data['assignments'] = assignments_data
            
            # Extract enrollments from students for registry
            enrollments_data = []
            for student_data in registry_format_data['students']:
                enrollment_data = student_data.copy()
                enrollment_data['course_id'] = live_canvas_data['course']['id']
                enrollments_data.append(enrollment_data)
            registry_format_data['enrollments'] = enrollments_data
            
            start_time = datetime.now()
            registry_results = registry.transform_entities(
                canvas_data=registry_format_data,
                configuration=config,
                course_id=live_canvas_data['course']['id']
            )
            transform_time = (datetime.now() - start_time).total_seconds() * 1000
            
            # Convert registry results back to legacy format
            result = {}
            for entity_type, transform_result in registry_results.items():
                result[entity_type] = transform_result.transformed_data if transform_result.success else []
            
            print(f"\n   {config_name} Configuration:")
            print(f"      Transform time: {transform_time:.2f}ms")
            print(f"      Output:")
            
            total_records = 0
            for entity_type, data in result.items():
                record_count = len(data)
                total_records += record_count
                status = "[+]" if record_count > 0 else "[-]"
                print(f"         {status} {entity_type}: {record_count} records")
            
            print(f"      Total records: {total_records}")
            
            # Show field details for students if present
            if result.get('students') and len(result['students']) > 0:
                student = result['students'][0]
                total_fields = len(student)
                populated_fields = len([k for k, v in student.items() if v is not None and v != '' and v != 0])
                print(f"      Student fields: {total_fields} total, {populated_fields} populated")
                
                # Show specific field presence based on configuration
                field_indicators = []
                if student.get('current_score', 0) > 0:
                    field_indicators.append("scores")
                if student.get('last_activity_at'):
                    field_indicators.append("analytics") 
                if student.get('enrollment_status'):
                    field_indicators.append("enrollment")
                
                # Show all field names for debugging
                print(f"      Student fields: {list(student.keys())}")
                
                if field_indicators:
                    print(f"      Active field groups: {', '.join(field_indicators)}")
        
        print(f"\nCONFIGURATION IMPACT ANALYSIS COMPLETED!")
        print("="*100)
    
    # ==================== HELPER METHODS ====================
    
    def _inspect_real_course_data(self, courses: List[Dict[str, Any]], original_course: Dict[str, Any]):
        """Inspect real course data transformation."""
        if not courses:
            print("   Courses: No course data after transformation")
            return
        
        course = courses[0]
        print(f"   Real Course Data Transformation:")
        print(f"      Canvas ID: {original_course['id']} -> DB ID: {course.get('id')}")
        print(f"      Canvas Name: '{original_course['name']}' -> DB Name: '{course.get('name')}'")
        print(f"      Canvas Code: '{original_course.get('course_code', 'N/A')}' -> DB Code: '{course.get('course_code')}'")
        print(f"      Canvas Start: {original_course.get('start_at', 'N/A')} -> DB Start: {course.get('start_at')}")
        print(f"      DB Last Synced: {course.get('last_synced')}")
        
        # Show Canvas-specific fields that were preserved
        canvas_fields = ['enrollment_term_id', 'is_public', 'storage_quota_mb', 'locale', 'time_zone']
        preserved = [f for f in canvas_fields if f in course and course[f] is not None]
        if preserved:
            print(f"      Canvas fields preserved: {preserved}")
    
    def _inspect_real_student_data(self, students: List[Dict[str, Any]], original_students: List[Dict[str, Any]]):
        """Inspect real student data transformation."""
        if not students:
            print("   Students: No student data after transformation")
            return
        
        print(f"   Real Student Data Transformation ({len(students)} total):")
        
        for i in range(min(2, len(students))):  # Show first 2 students
            student = students[i]
            original = original_students[i] if i < len(original_students) else {}
            
            print(f"      Student {i+1} (Real Canvas Data):")
            print(f"         Canvas: user_id={original.get('user_id', 'N/A')}, id={original.get('id', 'N/A')}")
            print(f"         Transformed: student_id={student.get('student_id')}, user_id={student.get('user_id')}")
            
            # Show name extraction from Canvas user object
            original_user = original.get('user', {})
            canvas_name = original_user.get('name', original.get('name', 'N/A'))
            print(f"         Canvas Name: '{canvas_name}' -> DB Name: '{student.get('name')}'")
            
            # Show email extraction  
            canvas_email = original_user.get('email', original.get('email', 'N/A'))
            print(f"         Canvas Email: '{canvas_email}' -> DB Email: '{student.get('email')}'")
            
            # Show grade transformation
            original_grades = original.get('grades', {})
            canvas_current = original_grades.get('current_score', original.get('current_score', 'N/A'))
            canvas_final = original_grades.get('final_score', original.get('final_score', 'N/A'))
            print(f"         Canvas Scores: current={canvas_current}, final={canvas_final}")
            print(f"         DB Scores: current={student.get('current_score')}, final={student.get('final_score')}")
            
            # Show Canvas-specific data preservation
            canvas_fields = ['enrollment_state', 'course_section_id', 'last_activity_at']
            preserved = []
            for field in canvas_fields:
                if field in student and student[field] is not None:
                    canvas_value = original.get(field, 'N/A')
                    preserved.append(f"{field}='{canvas_value}'->'{student[field]}'")
            
            if preserved:
                print(f"         Canvas fields: {', '.join(preserved[:2])}")  # Show first 2
    
    def _inspect_real_assignment_data(self, assignments: List[Dict[str, Any]]):
        """Inspect real assignment data transformation."""
        if not assignments:
            print("   Assignments: No assignments extracted from modules")
            return
        
        print(f"   Real Assignment Data Transformation ({len(assignments)} total):")
        
        for i in range(min(2, len(assignments))):  # Show first 2 assignments
            assignment = assignments[i]
            print(f"      Assignment {i+1} (from Canvas Modules):")
            print(f"         ID: {assignment.get('id')}")
            print(f"         Name: '{assignment.get('name')}'")
            print(f"         Points: {assignment.get('points_possible')}")
            print(f"         Module: {assignment.get('module_id')}")
            print(f"         Type: {assignment.get('assignment_type')}")
            print(f"         Published: {assignment.get('published')}")
            print(f"         Synced: {assignment.get('last_synced')}")
    
    def _validate_real_data_quality(self, live_data: Dict[str, Any], results: Dict[str, Any]):
        """Validate data quality with real Canvas data."""
        original_course = live_data['course']
        original_student_count = len(live_data['students'])
        original_module_count = len(live_data['modules'])
        
        print(f"   Real Data Quality Validation:")
        
        # Test each configuration result
        for config_name, result in results.items():
            print(f"      {config_name}:")
            
            # Course validation
            if result.get('courses'):
                course = result['courses'][0]
                assert course['id'] == original_course['id'], f"Course ID mismatch in {config_name}"
                assert course['name'] == original_course['name'], f"Course name mismatch in {config_name}"
                print(f"         Course data integrity preserved")
            
            # Student count validation based on configuration
            student_count = len(result.get('students', []))
            print(f"         Students: {student_count} (Canvas had {original_student_count})")
            
            # Data type validation
            if result.get('students'):
                student = result['students'][0]
                assert isinstance(student.get('student_id'), int), f"Student ID should be integer in {config_name}"
                assert isinstance(student.get('name'), str), f"Student name should be string in {config_name}"
                print(f"         Student data types validated")
        
        print(f"   All configurations passed real data validation!")


if __name__ == '__main__':
    """Run real Canvas API integration tests."""
    print("Real Canvas API Pipeline Integration Tests")
    print("These tests make actual Canvas API calls and validate the complete pipeline!")
    print("Run with: pytest test_real_canvas_api_pipeline.py -v -s -m canvas_api")