"""
Multi-Course Canvas API Pipeline Test

Tests the Canvas API -> TypeScript -> Scalable Transformers pipeline with:
- Single course processing
- Multiple specific courses processing  
- All available courses processing (optional)
- Configuration impact across different course datasets

To use multi-course functionality:
1. Add real Canvas course IDs to TEST_COURSES["ADDITIONAL_COURSES"]
2. Course IDs can be found in Canvas URLs: /courses/{COURSE_ID}
3. Ensure you have access to all courses you want to test

Example:
    TEST_COURSES = {
        "JDU_COURSE": 7982015,
        "ADDITIONAL_COURSES": [1234567, 2345678, 3456789]
    }
"""

import pytest
import json
import subprocess
import tempfile
import os
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from unittest.mock import patch

from database.operations.transformers import (
    get_global_registry,
    TransformationContext,
    EntityType,
    TransformerRegistry,
    CourseTransformer,
    StudentTransformer,
    ConfigurationValidator
)


# Test Configuration
CANVAS_INTERFACE_PATH = Path("C:/Users/tyler/Documents/Canvas-Tracker-V3/canvas-interface")

# Course IDs for testing different scenarios
# To test multi-course functionality, add real Canvas course IDs to ADDITIONAL_COURSES
# You can find course IDs in Canvas URLs: https://your-canvas.instructure.com/courses/{COURSE_ID}
TEST_COURSES = {
    "JDU_COURSE": 7982015,      # Your existing JDU course
    "ADDITIONAL_COURSES": [],    # Add real Canvas course IDs here for multi-course testing
                                # Example: [7982016, 7982017, 7982018]
}

# Test configurations for different processing scenarios
PROCESSING_CONFIGURATIONS = {
    "LIGHTWEIGHT": {
        "entities": {"courses": True, "students": True, "enrollments": True, "assignments": False, "modules": False},
        "fields": {
            "courses": {"extended_info": False, "public_info": True, "settings": False},
            "students": {"basicInfo": True, "scores": True, "analytics": False, "enrollmentDetails": False}
        }
    },
    "ANALYTICS_FOCUSED": {
        "entities": {"courses": True, "students": True, "enrollments": True, "assignments": True, "modules": False},
        "fields": {
            "courses": {"extended_info": True, "public_info": True, "settings": True},
            "students": {"basicInfo": True, "scores": True, "analytics": True, "enrollmentDetails": True}
        }
    },
    "FULL_PROCESSING": {
        "entities": {"courses": True, "students": True, "enrollments": True, "assignments": True, "modules": True},
        "fields": {
            "courses": {"extended_info": True, "public_info": True, "settings": True},
            "students": {"basicInfo": True, "scores": True, "analytics": True, "enrollmentDetails": True}
        }
    }
}


class TestMultiCourseCanvasPipeline:
    """
    Multi-course integration test that validates Canvas API processing
    with single courses, multiple courses, and bulk processing scenarios.
    """
    
    def setup_method(self):
        """Set up test components and validate Canvas environment."""
        # Initialize transformer components
        self.registry = get_global_registry()
        self.validator = ConfigurationValidator(self.registry)
        
        # Validate Canvas interface path exists
        if not CANVAS_INTERFACE_PATH.exists():
            pytest.skip("Canvas interface path not found. Ensure canvas-interface directory exists.")
        
        # Check for .env file (Canvas credentials)
        env_file = CANVAS_INTERFACE_PATH / ".env"
        if not env_file.exists():
            pytest.skip("Canvas .env file not found. Canvas API credentials required for integration test.")
    
    def _execute_canvas_api_call(self, course_ids: List[int], bulk_mode: bool = False) -> Dict[str, Any]:
        """
        Execute Canvas API calls for one or more courses.
        
        Args:
            course_ids: List of course IDs to process
            bulk_mode: If True, use bulk processing; if False, process individually
            
        Returns:
            Canvas data with course information
        """
        print(f"\nMaking Canvas API calls for {'bulk' if bulk_mode else 'individual'} processing...")
        print(f"   Course IDs: {course_ids}")
        
        start_time = datetime.now()
        
        try:
            # Get environment setup
            env = os.environ.copy()
            node_path = r"C:\Program Files\nodejs"
            if 'PATH' in env:
                env['PATH'] = node_path + os.pathsep + env['PATH']
            else:
                env['PATH'] = node_path
            
            # Use npx ts-node to run the script
            npx_exe = os.path.join(node_path, "npx.cmd")
            
            if bulk_mode:
                # For bulk mode, we'll need to modify the TypeScript to handle multiple courses
                # For now, we'll simulate by calling individually and combining results
                print(f"   Bulk mode simulation: processing {len(course_ids)} courses individually")
                combined_results = {
                    "success": True,
                    "courses": [],
                    "total_students": 0,
                    "total_modules": 0,
                    "total_assignments": 0,
                    "api_execution_time": 0,
                    "course_processing_times": {}
                }
                
                for course_id in course_ids:
                    course_result = self._execute_single_course_api(course_id, env, npx_exe)
                    if course_result.get('success'):
                        # Add course data
                        combined_results["courses"].append({
                            "course_data": course_result.get('course'),
                            "students": course_result.get('students', []),
                            "modules": course_result.get('modules', []),
                            "course_id": course_id
                        })
                        
                        # Aggregate metrics
                        combined_results["total_students"] += len(course_result.get('students', []))
                        combined_results["total_modules"] += len(course_result.get('modules', []))
                        combined_results["api_execution_time"] += course_result.get('api_execution_time', 0)
                        combined_results["course_processing_times"][course_id] = course_result.get('api_execution_time', 0)
                
                return combined_results
                
            else:
                # Single course mode
                if len(course_ids) != 1:
                    raise ValueError("Single course mode requires exactly one course ID")
                
                return self._execute_single_course_api(course_ids[0], env, npx_exe)
                
        except Exception as e:
            print(f"   Canvas API execution failed: {str(e)}")
            raise Exception(f"Failed to execute Canvas API calls: {str(e)}")
    
    def _execute_single_course_api(self, course_id: int, env: dict, npx_exe: str) -> Dict[str, Any]:
        """Execute Canvas API call for a single course."""
        cmd = [npx_exe, "ts-node", "real_canvas_api_test.ts"]
        
        # Use file output to avoid subprocess buffering issues
        output_file = CANVAS_INTERFACE_PATH.parent / f"canvas_api_output_{course_id}.txt"
        
        # Remove existing output file
        if output_file.exists():
            output_file.unlink()
        
        print(f"     Executing for course {course_id}...")
        
        result = subprocess.run(
            " ".join([f'"{c}"' for c in cmd]) + f" > {output_file} 2>&1",
            cwd=str(CANVAS_INTERFACE_PATH.parent),
            shell=True,
            timeout=120,
            env=env
        )
        
        if result.returncode != 0:
            if output_file.exists():
                error_output = output_file.read_text(encoding='utf-8')[:500]
                print(f"     Course {course_id} failed: {error_output}...")
            raise Exception(f"Course {course_id} API call failed with code {result.returncode}")
        
        # Parse results
        if not output_file.exists():
            raise Exception(f"Course {course_id} output file not created")
        
        combined_output = output_file.read_text(encoding='utf-8')
        start_marker = "===CANVAS_API_RESULT_START==="
        end_marker = "===CANVAS_API_RESULT_END==="
        
        start_idx = combined_output.find(start_marker)
        end_idx = combined_output.find(end_marker)
        
        if start_idx == -1 or end_idx == -1:
            raise Exception(f"Canvas API result markers not found for course {course_id}")
        
        json_content = combined_output[start_idx + len(start_marker):end_idx].strip()
        canvas_data = json.loads(json_content)
        
        if not canvas_data.get('success', False):
            error_msg = canvas_data.get('error', {}).get('message', 'Unknown error')
            raise Exception(f"Course {course_id} Canvas API returned error: {error_msg}")
        
        print(f"     Course {course_id} completed in {canvas_data.get('api_execution_time', 0):.1f}ms")
        return canvas_data
    
    def _transform_multi_course_data(self, multi_course_data: Dict[str, Any], configuration: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform multi-course Canvas data using the registry system.
        
        Args:
            multi_course_data: Canvas data for multiple courses
            configuration: Transformation configuration
            
        Returns:
            Transformed data organized by entity type
        """
        registry = get_global_registry()
        all_results = {
            "courses": [],
            "students": [],
            "assignments": [], 
            "enrollments": [],
            "processing_summary": {
                "total_courses": 0,
                "successful_courses": 0,
                "total_entities": 0
            }
        }
        
        if "courses" in multi_course_data:
            # Bulk mode data structure
            course_list = multi_course_data["courses"]
        else:
            # Single course mode - wrap in list
            course_list = [{
                "course_data": multi_course_data.get('course'),
                "students": multi_course_data.get('students', []),
                "modules": multi_course_data.get('modules', []),
                "course_id": multi_course_data.get('course', {}).get('id')
            }]
        
        for course_info in course_list:
            course_data = course_info["course_data"]
            students_data = course_info["students"]
            modules_data = course_info["modules"]
            course_id = course_info["course_id"]
            
            if not course_data or not course_id:
                continue
            
            # Prepare registry format data for this course
            registry_format_data = {
                'courses': [course_data],
                'students': students_data,
                'modules': modules_data
            }
            
            # Extract assignments from modules
            assignments_data = []
            for module_data in modules_data:
                module_id = module_data.get('id')
                for item in module_data.get('items', []):
                    item_with_context = item.copy()
                    item_with_context['course_id'] = course_id
                    item_with_context['module_id'] = module_id
                    assignments_data.append(item_with_context)
            registry_format_data['assignments'] = assignments_data
            
            # Extract enrollments from students
            enrollments_data = []
            for student_data in students_data:
                enrollment_data = student_data.copy()
                enrollment_data['course_id'] = course_id
                enrollments_data.append(enrollment_data)
            registry_format_data['enrollments'] = enrollments_data
            
            # Transform this course's data
            try:
                registry_results = registry.transform_entities(
                    canvas_data=registry_format_data,
                    configuration=configuration,
                    course_id=course_id
                )
                
                # Aggregate results
                for entity_type, result in registry_results.items():
                    if result.success and result.transformed_data:
                        all_results[entity_type].extend(result.transformed_data)
                
                all_results["processing_summary"]["successful_courses"] += 1
                
            except Exception as e:
                print(f"   ⚠️  Failed to transform course {course_id}: {str(e)}")
        
        # Update processing summary
        all_results["processing_summary"]["total_courses"] = len(course_list)
        all_results["processing_summary"]["total_entities"] = sum(
            len(entities) for entities in all_results.values() 
            if isinstance(entities, list)
        )
        
        return all_results
    
    @pytest.mark.integration
    @pytest.mark.canvas_api
    def test_single_course_processing(self):
        """Test single course processing with different configurations."""
        print("\n" + "="*100)
        print("SINGLE COURSE PROCESSING TEST")
        print("="*100)
        
        course_id = TEST_COURSES["JDU_COURSE"]
        
        print(f"\nTesting Single Course Processing (Course {course_id})")
        print("-" * 60)
        
        # Execute Canvas API for single course
        canvas_data = self._execute_canvas_api_call([course_id], bulk_mode=False)
        
        print(f"Canvas API completed!")
        print(f"   Course: {canvas_data['course']['name']}")
        print(f"   Students: {len(canvas_data['students'])}")
        print(f"   Modules: {len(canvas_data['modules'])}")
        print(f"   API Time: {canvas_data.get('api_execution_time', 0):.1f}ms")
        
        # Test different configurations
        print(f"\nConfiguration Impact Analysis:")
        print("-" * 40)
        
        for config_name, config in PROCESSING_CONFIGURATIONS.items():
            print(f"\n   {config_name} Configuration:")
            
            # Validate configuration
            validation = self.validator.validate_configuration(config)
            print(f"      Valid: {validation.valid}")
            print(f"      Performance: {validation.performance_estimate['performance_category']}")
            
            # Transform data
            start_time = datetime.now()
            results = self._transform_multi_course_data(canvas_data, config)
            transform_time = (datetime.now() - start_time).total_seconds() * 1000
            
            print(f"      Transform time: {transform_time:.1f}ms")
            print(f"      Results:")
            for entity_type in ["courses", "students", "assignments", "enrollments"]:
                count = len(results.get(entity_type, []))
                status = "[+]" if count > 0 else "[-]"
                print(f"         {status} {entity_type}: {count} records")
            
            # Show field details for students
            if results.get('students'):
                student = results['students'][0]
                field_count = len(student)
                print(f"      Student fields: {field_count} total")
        
        print(f"\nSingle Course Processing Test Completed!")
    
    @pytest.mark.integration
    @pytest.mark.canvas_api
    @pytest.mark.parametrize("bulk_mode", [False, True])
    def test_multi_course_processing(self, bulk_mode: bool):
        """Test processing multiple courses individually or in bulk."""
        if len(TEST_COURSES["ADDITIONAL_COURSES"]) == 0:
            pytest.skip("No additional course IDs configured for multi-course testing")
        
        mode_name = "BULK" if bulk_mode else "INDIVIDUAL"
        print(f"\n" + "="*100)
        print(f"MULTI-COURSE {mode_name} PROCESSING TEST")
        print("="*100)
        
        # Use main course + additional courses
        course_ids = [TEST_COURSES["JDU_COURSE"]] + TEST_COURSES["ADDITIONAL_COURSES"]
        
        print(f"\nTesting {mode_name.title()} Processing")
        print(f"   Course IDs: {course_ids}")
        print(f"   Total Courses: {len(course_ids)}")
        print("-" * 60)
        
        # Execute Canvas API calls
        start_time = datetime.now()
        multi_course_data = self._execute_canvas_api_call(course_ids, bulk_mode=bulk_mode)
        api_time = (datetime.now() - start_time).total_seconds() * 1000
        
        print(f"\nCanvas API Processing Completed!")
        print(f"   ⏱️  Total API Time: {api_time:.1f}ms")
        
        if bulk_mode and "course_processing_times" in multi_course_data:
            print(f"   Per-course timing:")
            for course_id, time_ms in multi_course_data["course_processing_times"].items():
                print(f"      Course {course_id}: {time_ms:.1f}ms")
        
        print(f"   Aggregate Metrics:")
        print(f"      Total Courses: {len(multi_course_data.get('courses', [course_ids]))}")
        print(f"      👥 Total Students: {multi_course_data.get('total_students', len(multi_course_data.get('students', [])))}")
        print(f"      📝 Total Modules: {multi_course_data.get('total_modules', len(multi_course_data.get('modules', [])))}")
        
        # Test with lightweight configuration for multi-course
        config = PROCESSING_CONFIGURATIONS["LIGHTWEIGHT"]
        
        print(f"\nMulti-Course Transformation (LIGHTWEIGHT config):")
        print("-" * 50)
        
        transform_start = datetime.now()
        results = self._transform_multi_course_data(multi_course_data, config)
        transform_time = (datetime.now() - transform_start).total_seconds() * 1000
        
        print(f"   Transform time: {transform_time:.1f}ms")
        print(f"   Transformation Results:")
        for entity_type in ["courses", "students", "assignments", "enrollments"]:
            count = len(results.get(entity_type, []))
            status = "[+]" if count > 0 else "[-]"
            print(f"      {status} {entity_type}: {count} records")
        
        # Show processing summary
        summary = results.get("processing_summary", {})
        print(f"   Processing Summary:")
        print(f"      Courses processed: {summary.get('successful_courses', 0)}/{summary.get('total_courses', 0)}")
        print(f"      Total entities: {summary.get('total_entities', 0)}")
        
        # Performance analysis
        total_entities = sum(len(results[et]) for et in ["courses", "students", "assignments", "enrollments"])
        if total_entities > 0:
            entities_per_ms = total_entities / max(transform_time, 1)
            print(f"   Performance: {entities_per_ms:.2f} entities/ms")
        
        print(f"\nMulti-Course {mode_name.title()} Processing Test Completed!")
    
    def _execute_bulk_canvas_api(self, max_courses: Optional[int] = None, config_name: str = "LIGHTWEIGHT") -> Dict[str, Any]:
        """
        Execute bulk Canvas API processing using the bulk API manager.
        
        Args:
            max_courses: Maximum number of courses to process (None for all)
            config_name: Configuration name from PROCESSING_CONFIGURATIONS
            
        Returns:
            Bulk processing results with all course data
        """
        print(f"\nExecuting bulk Canvas API processing...")
        print(f"   Max courses: {max_courses or 'All available'}")
        print(f"   Configuration: {config_name}")
        
        try:
            # Get environment setup
            env = os.environ.copy()
            node_path = r"C:\Program Files\nodejs"
            if 'PATH' in env:
                env['PATH'] = node_path + os.pathsep + env['PATH']
            else:
                env['PATH'] = node_path
            
            # Build command with arguments
            npx_exe = os.path.join(node_path, "npx.cmd")
            cmd = [npx_exe, "ts-node", "bulk_canvas_api_test.ts"]
            
            # Add command line arguments
            if max_courses:
                cmd.append(f"--max-courses={max_courses}")
            
            # Create timestamped output file in results directory
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_dir = Path(__file__).parent / "results"
            results_dir.mkdir(exist_ok=True)
            output_file = results_dir / f"bulk_canvas_raw_data_{timestamp}.txt"
            
            # Remove existing output file
            if output_file.exists():
                output_file.unlink()
            
            print(f"   Executing bulk Canvas API workflow...")
            print(f"   Command: {' '.join(cmd)}")
            print(f"   Raw data output: {output_file}")
            
            start_time = datetime.now()
            
            result = subprocess.run(
                " ".join([f'"{c}"' for c in cmd]) + f" > {output_file} 2>&1",
                cwd=str(CANVAS_INTERFACE_PATH.parent),
                shell=True,
                timeout=300,  # 5 minutes for bulk processing
                env=env
            )
            
            api_time = (datetime.now() - start_time).total_seconds() * 1000
            
            if result.returncode != 0:
                if output_file.exists():
                    error_output = output_file.read_text(encoding='utf-8')[-1000:]  # Last 1000 chars
                    print(f"   Bulk processing failed: ...{error_output}")
                raise Exception(f"Bulk Canvas API processing failed with code {result.returncode}")
            
            # Parse results
            if not output_file.exists():
                raise Exception("Bulk Canvas API output file not created")
            
            combined_output = output_file.read_text(encoding='utf-8')
            start_marker = "===BULK_CANVAS_API_RESULT_START==="
            end_marker = "===BULK_CANVAS_API_RESULT_END==="
            
            start_idx = combined_output.find(start_marker)
            end_idx = combined_output.find(end_marker)
            
            if start_idx == -1 or end_idx == -1:
                raise Exception("Bulk Canvas API result markers not found")
            
            json_content = combined_output[start_idx + len(start_marker):end_idx].strip()
            bulk_data = json.loads(json_content)
            
            if not bulk_data.get('success', False):
                error_msg = bulk_data.get('error', {}).get('message', 'Unknown error')
                raise Exception(f"Bulk Canvas API returned error: {error_msg}")
            
            print(f"   Bulk processing completed in {api_time:.1f}ms")
            
            # Extract metrics
            workflow_result = bulk_data.get('workflow_result', {})
            metadata = bulk_data.get('metadata', {})
            
            print(f"   Results:")
            print(f"      Courses discovered: {workflow_result.get('coursesDiscovered', 0)}")
            print(f"      Courses processed: {workflow_result.get('coursesProcessed', 0)}")
            print(f"      Total students: {workflow_result.get('totalStudents', 0)}")
            print(f"      Total assignments: {workflow_result.get('totalAssignments', 0)}")
            print(f"      Total enrollments: {workflow_result.get('totalEnrollments', 0)}")
            print(f"      API calls: {workflow_result.get('totalApiCalls', 0)}")
            print(f"   Detailed raw data saved to: {output_file}")
            
            return bulk_data
            
        except Exception as e:
            print(f"   Bulk Canvas API processing failed: {str(e)}")
            raise Exception(f"Failed to execute bulk Canvas API processing: {str(e)}")
    
    @pytest.mark.integration
    @pytest.mark.canvas_api
    @pytest.mark.slow
    def test_all_available_courses(self):
        """
        Test processing ALL available courses using the bulk API infrastructure.
        This leverages the existing bulk API manager for efficient processing.
        """
        print("\n" + "="*100)
        print("ALL AVAILABLE COURSES PROCESSING TEST")
        print("="*100)
        print("WARNING: This will process ALL courses in your Canvas instance!")
        
        # Check if we're running from master test suite (which already prompted)
        import os
        if os.environ.get('CANVAS_MASTER_TEST_CONFIRMED') == 'true':
            print("\nRunning bulk test (confirmed by master test suite)")
        else:
            # Only prompt if not running from master test suite
            response = input("\nDo you want to continue with ALL courses? [y/N]: ")
            if response.lower() != 'y':
                pytest.skip("All-courses test cancelled by user")
        
        print(f"\nStarting All-Courses Processing")
        print("-" * 50)
        
        # Execute bulk processing with lightweight configuration
        start_time = datetime.now()
        bulk_results = self._execute_bulk_canvas_api(max_courses=None, config_name="LIGHTWEIGHT")
        total_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Extract data for analysis
        workflow_result = bulk_results.get('workflow_result', {})
        bulk_data = bulk_results.get('data', {})
        metadata = bulk_results.get('metadata', {})
        
        print(f"\nAll-Courses Processing Completed!")
        print("=" * 40)
        print(f"   Total Processing Time: {total_time:.1f}ms")
        print(f"   Success Rate: {workflow_result.get('coursesProcessed', 0)}/{workflow_result.get('coursesDiscovered', 0)} courses")
        
        # Validate data using our transformer system
        print(f"\nValidating Bulk Data with Transformer System:")
        print("-" * 50)
        
        config = PROCESSING_CONFIGURATIONS["LIGHTWEIGHT"]
        
        # Transform bulk data using our registry (just for validation)
        registry = get_global_registry()
        
        # Convert bulk data to our registry format for validation
        validation_data = {
            'courses': bulk_data.get('courses', []),
            'students': bulk_data.get('students', []),
            'assignments': bulk_data.get('assignments', []),
            'enrollments': bulk_data.get('enrollments', [])
        }
        
        print(f"   Data Summary:")
        for entity_type, data in validation_data.items():
            count = len(data)
            status = "[+]" if count > 0 else "[-]"
            print(f"      {status} {entity_type}: {count} records")
        
        # Performance analysis
        total_entities = sum(len(data) for data in validation_data.values())
        courses_processed = workflow_result.get('coursesProcessed', 0)
        
        if courses_processed > 0:
            entities_per_course = total_entities / courses_processed
            processing_rate = total_entities / max(total_time, 1) * 1000  # entities per second
            
            print(f"\nPerformance Analysis:")
            print(f"   Entities per course: {entities_per_course:.1f}")
            print(f"   Processing rate: {processing_rate:.1f} entities/second")
            print(f"   API efficiency: {total_entities / workflow_result.get('totalApiCalls', 1):.1f} entities/API call")
        
        # Show bulk summary if available
        bulk_summary = metadata.get('bulk_summary', {})
        if bulk_summary:
            print(f"\nBulk Processing Summary:")
            print(f"   Course data sets: {bulk_summary.get('courseDataSetsInitialized', 0)}")
            print(f"   Construction time: {bulk_summary.get('constructionTime', 0)}ms")
        
        print(f"\nAll-Courses Test Completed Successfully!")


if __name__ == "__main__":
    # Allow running specific tests directly
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "single":
            pytest.main(["-v", "-s", "test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_single_course_processing"])
        elif sys.argv[1] == "multi":
            pytest.main(["-v", "-s", "test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_multi_course_processing"])
    else:
        pytest.main(["-v", "-s", __file__])