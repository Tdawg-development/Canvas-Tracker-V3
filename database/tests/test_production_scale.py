"""
Production-scale data testing for Canvas Tracker V3.

This module contains tests that simulate realistic Canvas course data volumes
to validate performance, memory usage, and scalability under production conditions.

Test Categories:
- Large course data synchronization (100+ students, 50+ assignments)
- Multi-course batch processing
- Memory usage and resource management
- Database performance under load
- Query optimization validation
"""

import pytest
import time
import psutil
import os
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any
from unittest.mock import Mock, patch

from database.config import get_config
from database.session import get_session, DatabaseManager
from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
from database.models.layer2_historical import AssignmentScore, GradeHistory, CourseSnapshot
from database.operations.layer1.canvas_ops import CanvasDataManager
from database.operations.layer1.relationship_manager import RelationshipManager
from database.operations.layer1.sync_coordinator import SyncCoordinator, SyncStrategy
from database.operations.data_transformers import CanvasDataTransformer


class TestProductionScaleData:
    """Test production-scale data operations with realistic Canvas course sizes."""
    
    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test fixtures with real database session."""
        self.db_session = db_session
        self.canvas_manager = CanvasDataManager(db_session)
        self.relationship_manager = RelationshipManager(db_session)
        self.sync_coordinator = SyncCoordinator(db_session)
        self.transformer = CanvasDataTransformer()
        
        # Track memory usage
        self.process = psutil.Process(os.getpid())
        self.initial_memory = self.process.memory_info().rss / 1024 / 1024  # MB
    
    def _generate_large_course_data(self, 
                                   course_id: int = 12345,
                                   num_students: int = 150,
                                   num_assignments: int = 75) -> Dict[str, Any]:
        """Generate realistic large course data for testing."""
        return {
            'success': True,
            'course_id': course_id,
            'course': {
                'id': course_id,
                'name': f'Large Production Course {course_id}',
                'course_code': f'PROD{course_id}',
                'term': 'Fall 2024',
                'enrollment_count': num_students,
                'created_at': '2024-08-15T08:00:00Z',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'workflow_state': 'available',
                'calendar_ics': f'https://canvas.example.com/feeds/calendars/course_{course_id}.ics'
            },
            'students': self._generate_student_data(num_students),
            'modules': self._generate_module_assignments(num_assignments)
        }
    
    def _generate_student_data(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic student enrollment data."""
        students = []
        for i in range(count):
            student_id = 10000 + i
            students.append({
                'id': student_id,  # Enrollment ID
                'user_id': 20000 + i,
                'user': {
                    'id': 20000 + i,
                    'name': f'Student {i:03d}',
                    'login_id': f'student{i:03d}@university.edu'
                },
                'enrollment_state': 'active',
                'role': 'StudentEnrollment',
                'created_at': '2024-08-20T10:00:00Z',
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'last_activity_at': (datetime.now(timezone.utc) - timedelta(days=i % 7)).isoformat(),
                'current_score': max(60, 95 - (i % 35)),  # Realistic grade distribution
                'final_score': max(65, 98 - (i % 30))
            })
        return students
    
    def _generate_module_assignments(self, count: int) -> List[Dict[str, Any]]:
        """Generate realistic assignment data across multiple modules."""
        modules = []
        assignments_per_module = count // 5  # 5 modules
        
        module_names = [
            'Getting Started', 'Fundamentals', 'Advanced Topics', 
            'Projects', 'Final Assessments'
        ]
        
        assignment_types = ['Assignment', 'Quiz', 'Discussion', 'Project']
        
        for module_idx in range(5):
            module_id = 1000 + module_idx
            assignments = []
            
            for assign_idx in range(assignments_per_module):
                assignment_id = module_id * 100 + assign_idx
                assignment_type = assignment_types[assign_idx % len(assignment_types)]
                
                assignments.append({
                    'id': assignment_id,
                    'title': f'{assignment_type} {assign_idx + 1}: {module_names[module_idx]} Topic',
                    'type': assignment_type,
                    'position': assign_idx + 1,
                    'url': f'https://canvas.example.com/courses/12345/assignments/{assignment_id}',
                    'published': True,
                    'content_details': {
                        'points_possible': 10 if assignment_type == 'Quiz' else 25 if assignment_type == 'Discussion' else 100
                    }
                })
            
            modules.append({
                'id': module_id,
                'name': module_names[module_idx],
                'position': module_idx + 1,
                'items': assignments
            })
        
        return modules
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_large_course_synchronization_performance(self):
        """Test synchronizing a large course with 150 students and 75 assignments."""
        # Generate large course data
        large_course_data = self._generate_large_course_data(
            course_id=99001,
            num_students=150,
            num_assignments=75
        )
        
        # Measure synchronization time
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        # Transform and sync the data
        transformed_data = self.transformer.transform_canvas_staging_data(large_course_data)
        
        # Sync course
        course = self.canvas_manager.sync_course(transformed_data['course'])
        assert course.id == 99001
        assert course.name.startswith('Large Production Course')
        
        # Batch sync students
        student_results = self.canvas_manager.batch_sync_students(
            transformed_data['students']
        )
        assert len(student_results) == 150
        
        # Batch sync assignments
        assignment_results = self.canvas_manager.batch_sync_assignments(
            transformed_data['assignments']
        )
        assert len(assignment_results) == 75
        
        # Create enrollment relationships
        for student_data in transformed_data['students']:
            self.relationship_manager.create_enrollment_relationship(
                student_id=student_data['student_id'],
                course_id=99001,
                enrollment_date=datetime.now(timezone.utc),
                enrollment_status='active'
            )
        
        self.db_session.commit()
        
        # Measure results
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        sync_duration = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Performance assertions
        assert sync_duration < 30.0, f"Large course sync took {sync_duration:.2f}s (should be < 30s)"
        assert memory_usage < 100, f"Memory usage increased by {memory_usage:.1f}MB (should be < 100MB)"
        
        # Verify data integrity
        course_count = self.db_session.query(CanvasCourse).filter(CanvasCourse.id == 99001).count()
        student_count = self.db_session.query(CanvasStudent).count()
        assignment_count = self.db_session.query(CanvasAssignment).filter(CanvasAssignment.course_id == 99001).count()
        enrollment_count = self.db_session.query(CanvasEnrollment).filter(CanvasEnrollment.course_id == 99001).count()
        
        assert course_count == 1
        assert student_count >= 150
        assert assignment_count == 75
        assert enrollment_count == 150
        
        print(f"✓ Large course sync completed in {sync_duration:.2f}s using {memory_usage:.1f}MB additional memory")
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_multi_course_batch_processing(self):
        """Test processing multiple large courses in batch."""
        course_ids = [99010, 99020, 99030, 99040, 99050]
        total_students = 0
        total_assignments = 0
        
        start_time = time.time()
        start_memory = self.process.memory_info().rss / 1024 / 1024
        
        for course_id in course_ids:
            # Generate varied course sizes
            num_students = 80 + (course_id % 50)  # 80-130 students per course
            num_assignments = 40 + (course_id % 20)  # 40-60 assignments per course
            
            course_data = self._generate_large_course_data(
                course_id=course_id,
                num_students=num_students,
                num_assignments=num_assignments
            )
            
            # Transform and sync
            transformed_data = self.transformer.transform_canvas_staging_data(course_data)
            
            # Use SyncCoordinator for batch processing
            sync_result = self.sync_coordinator.execute_full_sync(transformed_data)
            
            assert sync_result.success, f"Sync failed for course {course_id}"
            total_students += num_students
            total_assignments += num_assignments
        
        self.db_session.commit()
        
        end_time = time.time()
        end_memory = self.process.memory_info().rss / 1024 / 1024
        total_duration = end_time - start_time
        memory_usage = end_memory - start_memory
        
        # Performance assertions for batch processing
        assert total_duration < 120.0, f"Multi-course batch took {total_duration:.2f}s (should be < 120s)"
        assert memory_usage < 250, f"Memory usage increased by {memory_usage:.1f}MB (should be < 250MB)"
        
        # Verify all data was processed
        processed_courses = self.db_session.query(CanvasCourse).filter(
            CanvasCourse.id.in_(course_ids)
        ).count()
        processed_assignments = self.db_session.query(CanvasAssignment).filter(
            CanvasAssignment.course_id.in_(course_ids)
        ).count()
        
        assert processed_courses == 5
        assert processed_assignments == total_assignments
        
        print(f"✓ Multi-course batch processed {total_students} students and {total_assignments} assignments")
        print(f"  Completed in {total_duration:.2f}s using {memory_usage:.1f}MB additional memory")
    
    @pytest.mark.integration
    @pytest.mark.performance
    def test_query_performance_with_large_dataset(self):
        """Test query performance with large dataset."""
        # First ensure we have a large dataset
        course_data = self._generate_large_course_data(
            course_id=99100,
            num_students=200,
            num_assignments=100
        )
        
        transformed_data = self.transformer.transform_canvas_staging_data(course_data)
        sync_result = self.sync_coordinator.execute_full_sync(transformed_data)
        self.db_session.commit()
        
        # Test various query patterns with timing
        query_tests = []
        
        # Test 1: Get all students in course
        start_time = time.time()
        students = self.relationship_manager.get_course_enrollments(
            course_id=99100,
            active_only=True,
            include_students=True
        )
        query_tests.append(('Course enrollments with students', time.time() - start_time, len(students)))
        
        # Test 2: Get all assignments for course
        start_time = time.time()
        assignments = self.relationship_manager.get_course_assignments(
            course_id=99100,
            include_scores=False
        )
        query_tests.append(('Course assignments', time.time() - start_time, len(assignments)))
        
        # Test 3: Get student assignments for multiple students
        start_time = time.time()
        for i in range(10):  # Test first 10 students
            student_assignments = self.relationship_manager.get_student_assignments_in_course(
                student_id=10000 + i,
                course_id=99100,
                include_scores=False
            )
        query_tests.append(('Student assignments (10 students)', time.time() - start_time, 10))
        
        # Test 4: Complex query with joins
        start_time = time.time()
        complex_query = self.db_session.query(CanvasStudent).join(
            CanvasEnrollment
        ).filter(
            CanvasEnrollment.course_id == 99100,
            CanvasStudent.current_score > 80
        ).all()
        query_tests.append(('Complex join query', time.time() - start_time, len(complex_query)))
        
        # Assert all queries complete within reasonable time
        for query_name, duration, result_count in query_tests:
            assert duration < 5.0, f"{query_name} took {duration:.3f}s (should be < 5s)"
            assert result_count > 0, f"{query_name} returned no results"
            print(f"✓ {query_name}: {duration:.3f}s, {result_count} results")
    
    @pytest.mark.integration
    def test_memory_usage_tracking(self):
        """Test memory usage remains reasonable during large data operations."""
        initial_memory = self.process.memory_info().rss / 1024 / 1024
        memory_measurements = [initial_memory]
        
        # Process 3 medium-sized courses sequentially
        for i in range(3):
            course_data = self._generate_large_course_data(
                course_id=99200 + i,
                num_students=100,
                num_assignments=50
            )
            
            transformed_data = self.transformer.transform_canvas_staging_data(course_data)
            sync_result = self.sync_coordinator.execute_full_sync(transformed_data)
            self.db_session.commit()
            
            current_memory = self.process.memory_info().rss / 1024 / 1024
            memory_measurements.append(current_memory)
            
            # Memory should not grow excessively between courses
            memory_growth = current_memory - memory_measurements[-2]
            assert memory_growth < 75, f"Memory grew by {memory_growth:.1f}MB between courses (should be < 75MB)"
        
        # Total memory growth should be reasonable
        total_growth = memory_measurements[-1] - memory_measurements[0]
        assert total_growth < 200, f"Total memory growth {total_growth:.1f}MB (should be < 200MB)"
        
        print(f"✓ Memory usage: {initial_memory:.1f}MB → {memory_measurements[-1]:.1f}MB ({total_growth:.1f}MB increase)")
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_database_scalability_stress(self):
        """Test database performance under stress with concurrent operations."""
        import threading
        import queue
        
        # Create multiple courses concurrently
        course_queue = queue.Queue()
        results = []
        
        def process_course(course_id_start):
            """Process a course in a separate thread."""
            try:
                # Create separate session for this thread
                with get_session() as session:
                    thread_transformer = CanvasDataTransformer()
                    thread_coordinator = SyncCoordinator(session)
                    
                    course_data = self._generate_large_course_data(
                        course_id=course_id_start,
                        num_students=50,
                        num_assignments=25
                    )
                    
                    transformed_data = thread_transformer.transform_canvas_staging_data(course_data)
                    sync_result = thread_coordinator.execute_full_sync(transformed_data)
                    session.commit()
                    
                    results.append((course_id_start, sync_result.success, sync_result.duration))
            except Exception as e:
                results.append((course_id_start, False, str(e)))
        
        # Launch 5 concurrent course processing threads
        threads = []
        start_time = time.time()
        
        for i in range(5):
            course_id = 99300 + (i * 10)
            thread = threading.Thread(target=process_course, args=(course_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        total_time = time.time() - start_time
        
        # Verify all operations completed successfully
        successful_syncs = [r for r in results if r[1] is True]
        assert len(successful_syncs) == 5, f"Only {len(successful_syncs)}/5 concurrent syncs succeeded"
        assert total_time < 60.0, f"Concurrent processing took {total_time:.2f}s (should be < 60s)"
        
        print(f"✓ Concurrent processing: 5 courses in {total_time:.2f}s")
        for course_id, success, duration in results:
            if success:
                print(f"  Course {course_id}: {duration:.2f}s")
            else:
                print(f"  Course {course_id}: FAILED - {duration}")
    
    def teardown_method(self):
        """Clean up after tests and report memory usage."""
        final_memory = self.process.memory_info().rss / 1024 / 1024
        memory_change = final_memory - self.initial_memory
        
        # Clean up test data - handle missing tables gracefully
        try:
            test_course_ids = list(range(99001, 99310))
            
            # Try to clean up enrollments
            try:
                self.db_session.query(CanvasEnrollment).filter(
                    CanvasEnrollment.course_id.in_(test_course_ids)
                ).delete(synchronize_session=False)
            except Exception:
                pass  # Table might not exist
            
            # Try to clean up assignments
            try:
                self.db_session.query(CanvasAssignment).filter(
                    CanvasAssignment.course_id.in_(test_course_ids)
                ).delete(synchronize_session=False)
            except Exception:
                pass  # Table might not exist
            
            # Try to clean up courses
            try:
                self.db_session.query(CanvasCourse).filter(
                    CanvasCourse.id.in_(test_course_ids)
                ).delete(synchronize_session=False)
            except Exception:
                pass  # Table might not exist
            
            # Try to clean up students created during tests
            try:
                self.db_session.query(CanvasStudent).filter(
                    CanvasStudent.student_id >= 10000
                ).delete(synchronize_session=False)
            except Exception:
                pass  # Table might not exist
            
            self.db_session.commit()
            
        except Exception:
            pass  # Best effort cleanup
        
        if abs(memory_change) > 5:  # Only report significant memory changes
            print(f"Memory change: {memory_change:+.1f}MB")
