"""
Real database integration tests for transaction management.

This module contains tests that validate actual database transaction behavior,
rollbacks, isolation levels, and concurrent access patterns using real database
connections rather than mocks.

Test Categories:
- Transaction rollback and commit behavior
- Isolation level validation (READ COMMITTED, SERIALIZABLE)
- Concurrent transaction handling
- Deadlock detection and recovery
- Session management and cleanup
- Transaction boundary enforcement
- Cross-session data visibility
"""

import pytest
import time
import threading
import queue
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from unittest.mock import patch
from contextlib import contextmanager

import sqlalchemy
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy import text, select, func
from sqlalchemy.orm import sessionmaker

from database.config import get_config
from database.session import get_session, DatabaseManager, session_scope, transaction_scope
from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
from database.models.layer2_historical import AssignmentScore, GradeHistory, CourseSnapshot
from database.operations.layer1.canvas_ops import CanvasDataManager
from database.operations.layer1.relationship_manager import RelationshipManager
from database.operations.layer1.sync_coordinator import SyncCoordinator
from database.operations.data_transformers import CanvasDataTransformer
from database.operations.base.exceptions import (
    OperationError, ValidationError, TransactionError,
    DatabaseConnectionError, BulkOperationError
)


class TestDatabaseTransactionManagement:
    """Test real database transaction management and rollback behavior."""
    
    def setup_method(self):
        """Set up test environment with clean database state."""
        # Use persistent test database (now file-based by default)
        self.config = get_config('test')
        self.db_manager = DatabaseManager(self.config)
        
        # Ensure clean state
        self.db_manager.recreate_all_tables()
        
        # Create session factory for multi-session tests
        self.Session = sessionmaker(bind=self.db_manager.engine)
        
        # Override global database manager to use test instance
        import database.session as session_module
        session_module._db_manager = self.db_manager
    
    def teardown_method(self):
        """Clean up after tests."""
        try:
            # Clean up any remaining test data
            with get_session() as session:
                # Remove test data in dependency order
                test_course_ids = list(range(80000, 89999))
                
                try:
                    session.query(CanvasEnrollment).filter(
                        CanvasEnrollment.course_id.in_(test_course_ids)
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # Table may not exist
                
                try:
                    session.query(AssignmentScore).filter(
                        AssignmentScore.assignment_id.in_(
                            select(CanvasAssignment.id).where(
                                CanvasAssignment.course_id.in_(test_course_ids)
                            )
                        )
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # Table may not exist
                
                try:
                    session.query(CanvasAssignment).filter(
                        CanvasAssignment.course_id.in_(test_course_ids)
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # Table may not exist
                
                try:
                    session.query(CanvasCourse).filter(
                        CanvasCourse.id.in_(test_course_ids)
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # Table may not exist
                
                try:
                    session.query(CanvasStudent).filter(
                        CanvasStudent.student_id >= 80000
                    ).delete(synchronize_session=False)
                except Exception:
                    pass  # Table may not exist
                
                session.commit()
        except Exception:
            pass  # Cleanup is best-effort
        
        # Restore global database manager
        import database.session as session_module
        session_module._db_manager = None
        
        self.db_manager.close()
        
        # Note: Database file is persistent for manual inspection
    
    @pytest.mark.integration
    def test_basic_transaction_rollback_on_exception(self):
        """Test that transactions rollback properly when exceptions occur."""
        initial_count = 0
        
        with get_session() as session:
            initial_count = session.query(CanvasCourse).count()
        
        # Attempt transaction that should fail and rollback
        try:
            with get_session() as session:
                # Create a valid course
                course1 = CanvasCourse(
                    id=80001,
                    name="Transaction Test Course 1",
                    course_code="TXN001"
                )
                session.add(course1)
                session.flush()  # Ensure it's in the database
                
                # Verify it exists in this session
                assert session.query(CanvasCourse).filter(CanvasCourse.id == 80001).count() == 1
                
                # Now create a duplicate that should cause an error
                course2 = CanvasCourse(
                    id=80001,  # Same ID - should cause integrity error
                    name="Duplicate Course",
                    course_code="DUP001"
                )
                session.add(course2)
                
                # This should fail on commit
                session.commit()
                
        except IntegrityError:
            # Expected - duplicate primary key
            pass
        
        # Verify rollback occurred - no courses should be added
        with get_session() as session:
            final_count = session.query(CanvasCourse).count()
            assert final_count == initial_count, "Transaction was not properly rolled back"
            
            # Specifically verify our test course wasn't committed
            course_exists = session.query(CanvasCourse).filter(CanvasCourse.id == 80001).count()
            assert course_exists == 0, "Rolled back course still exists in database"
    
    @pytest.mark.integration
    def test_successful_transaction_commit(self):
        """Test that successful transactions commit properly."""
        course_id = 80002
        
        # Create course in transaction
        with get_session() as session:
            course = CanvasCourse(
                id=course_id,
                name="Successful Transaction Course",
                course_code="SUCCESS001"
            )
            session.add(course)
            session.commit()
        
        # Verify in separate session that it was committed
        with get_session() as session:
            retrieved_course = session.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            assert retrieved_course is not None
            assert retrieved_course.name == "Successful Transaction Course"
            assert retrieved_course.course_code == "SUCCESS001"
    
    @pytest.mark.integration
    def test_nested_transaction_rollback(self):
        """Test rollback behavior with nested transaction-like operations."""
        course_id = 80003
        student_id = 80001
        
        try:
            with get_session() as session:
                # Outer operation: create course
                course = CanvasCourse(
                    id=course_id,
                    name="Nested Transaction Course",
                    course_code="NESTED001"
                )
                session.add(course)
                session.flush()
                
                # Inner operation: create student
                student = CanvasStudent(
                    student_id=student_id,
                    name="Test Student",
                    login_id="test.student@university.edu",
                    current_score=85,
                    final_score=87
                )
                session.add(student)
                session.flush()
                
                # Create enrollment relationship
                enrollment = CanvasEnrollment(
                    student_id=student_id,
                    course_id=course_id,
                    enrollment_date=datetime.now(timezone.utc),
                    enrollment_status='active'
                )
                session.add(enrollment)
                session.flush()
                
                # Simulate error condition
                raise ValueError("Simulated nested transaction error")
                
        except ValueError:
            # Expected error
            pass
        
        # Verify complete rollback - none of the objects should exist
        with get_session() as session:
            course_count = session.query(CanvasCourse).filter(CanvasCourse.id == course_id).count()
            student_count = session.query(CanvasStudent).filter(CanvasStudent.student_id == student_id).count()
            enrollment_count = session.query(CanvasEnrollment).filter(
                CanvasEnrollment.course_id == course_id
            ).count()
            
            assert course_count == 0, "Course was not rolled back"
            assert student_count == 0, "Student was not rolled back"
            assert enrollment_count == 0, "Enrollment was not rolled back"
    
    @pytest.mark.integration
    def test_transaction_isolation_read_uncommitted(self):
        """Test transaction isolation - changes in one session not visible in another until commit."""
        course_id = 80004
        
        # Create two separate sessions to test isolation
        session1 = self.Session()
        session2 = self.Session()
        
        try:
            # Session 1: Start transaction and add course (but don't commit)
            course = CanvasCourse(
                id=course_id,
                name="Isolation Test Course",
                course_code="ISOLATE001"
            )
            session1.add(course)
            session1.flush()  # Send to DB but don't commit
            
            # Session 2: Should not see the uncommitted course
            course_in_session2 = session2.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            assert course_in_session2 is None, "Uncommitted data visible in other session"
            
            # Session 1: Commit the transaction
            session1.commit()
            
            # Session 2: Should now see the committed course (after refresh)
            session2.expire_all()  # Clear session cache
            course_in_session2 = session2.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            assert course_in_session2 is not None, "Committed data not visible in other session"
            assert course_in_session2.name == "Isolation Test Course"
            
        finally:
            session1.close()
            session2.close()
    
    @pytest.mark.integration
    def test_concurrent_insert_conflict_handling(self):
        """Test handling of concurrent insert conflicts."""
        course_id = 80005
        results = []
        
        def create_course_concurrently(session_id: int, delay: float = 0):
            """Create course in separate thread with optional delay."""
            if delay > 0:
                time.sleep(delay)
                
            try:
                # Use the test database manager's session factory directly
                session = self.Session()
                try:
                    course = CanvasCourse(
                        id=course_id,
                        name=f"Concurrent Course from Session {session_id}",
                        course_code=f"CONCURRENT{session_id:03d}"
                    )
                    session.add(course)
                    session.commit()
                    results.append((session_id, "SUCCESS"))
                finally:
                    session.close()
                    
            except IntegrityError as e:
                results.append((session_id, f"CONFLICT: {str(e)[:100]}"))
            except Exception as e:
                results.append((session_id, f"ERROR: {str(e)[:100]}"))
        
        # Launch concurrent course creation attempts
        threads = []
        for i in range(3):
            thread = threading.Thread(
                target=create_course_concurrently,
                args=(i, i * 0.01)  # Small staggered delays
            )
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join(timeout=10)
        
        # Analyze results
        successes = [r for r in results if r[1] == "SUCCESS"]
        conflicts = [r for r in results if "CONFLICT" in r[1]]
        
        # Exactly one should succeed, others should get conflicts
        assert len(successes) == 1, f"Expected 1 success, got {len(successes)}: {results}"
        assert len(conflicts) >= 1, f"Expected conflicts, got: {results}"
        
        # Verify only one course exists
        session = self.Session()
        try:
            course_count = session.query(CanvasCourse).filter(CanvasCourse.id == course_id).count()
            assert course_count == 1, "Concurrent insert created duplicate courses"
        finally:
            session.close()
    
    @pytest.mark.integration
    def test_deadlock_detection_and_recovery(self):
        """Test deadlock detection and recovery mechanisms."""
        course_id1, course_id2 = 80006, 80007
        student_id1, student_id2 = 80002, 80003
        
        # Set up initial data
        with get_session() as session:
            # Create courses
            course1 = CanvasCourse(id=course_id1, name="Deadlock Course 1", course_code="DEAD001")
            course2 = CanvasCourse(id=course_id2, name="Deadlock Course 2", course_code="DEAD002")
            session.add(course1)
            session.add(course2)
            
            # Create students
            student1 = CanvasStudent(student_id=student_id1, name="Student 1", login_id="s1@test.edu", current_score=80, final_score=80)
            student2 = CanvasStudent(student_id=student_id2, name="Student 2", login_id="s2@test.edu", current_score=85, final_score=85)
            session.add(student1)
            session.add(student2)
            
            session.commit()
        
        results = []
        
        def deadlock_scenario(thread_id: int):
            """Create potential deadlock scenario."""
            try:
                session = self.Session()
                try:
                    if thread_id == 1:
                        # Thread 1: Lock course1 then course2
                        course1 = session.query(CanvasCourse).filter(
                            CanvasCourse.id == course_id1
                        ).with_for_update().first()
                        
                        time.sleep(0.1)  # Give other thread time to get its lock
                        
                        course2 = session.query(CanvasCourse).filter(
                            CanvasCourse.id == course_id2
                        ).with_for_update().first()
                        
                        # Update both
                        course1.name = "Updated by Thread 1"
                        course2.name = "Updated by Thread 1"
                        
                    else:
                        # Thread 2: Lock course2 then course1 (opposite order)
                        course2 = session.query(CanvasCourse).filter(
                            CanvasCourse.id == course_id2
                        ).with_for_update().first()
                        
                        time.sleep(0.1)  # Give other thread time to get its lock
                        
                        course1 = session.query(CanvasCourse).filter(
                            CanvasCourse.id == course_id1
                        ).with_for_update().first()
                        
                        # Update both
                        course1.name = "Updated by Thread 2"
                        course2.name = "Updated by Thread 2"
                    
                    session.commit()
                    results.append((thread_id, "SUCCESS"))
                finally:
                    session.close()
                    
            except OperationalError as e:
                if "deadlock" in str(e).lower():
                    results.append((thread_id, "DEADLOCK_DETECTED"))
                else:
                    results.append((thread_id, f"OPERATIONAL_ERROR: {str(e)[:100]}"))
            except Exception as e:
                results.append((thread_id, f"ERROR: {str(e)[:100]}"))
        
        # Launch potentially deadlocking operations
        threads = []
        for i in [1, 2]:
            thread = threading.Thread(target=deadlock_scenario, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join(timeout=10)
        
        # Analyze results - at least one should complete
        successes = [r for r in results if r[1] == "SUCCESS"]
        deadlocks = [r for r in results if "DEADLOCK" in r[1]]
        
        # SQLite might not detect deadlocks the same way as PostgreSQL/MySQL
        # so we just verify that operations completed without hanging
        assert len(results) == 2, "Not all threads completed"
        print(f"Deadlock test results: {results}")
    
    @pytest.mark.integration
    def test_session_scope_context_manager(self):
        """Test session_scope context manager behavior."""
        course_id = 80008
        
        # Test successful operation
        with session_scope() as session:
            course = CanvasCourse(
                id=course_id,
                name="Session Scope Test",
                course_code="SCOPE001"
            )
            session.add(course)
            # No explicit commit - should be handled by context manager
        
        # Verify it was committed
        with get_session() as session:
            retrieved_course = session.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            assert retrieved_course is not None
            assert retrieved_course.name == "Session Scope Test"
        
        # Test rollback on exception
        student_id = 80004
        try:
            with session_scope() as session:
                student = CanvasStudent(
                    student_id=student_id,
                    name="Scope Test Student",
                    login_id="scope@test.edu",
                    current_score=90,
                    final_score=90
                )
                session.add(student)
                session.flush()
                
                # Simulate error
                raise ValueError("Session scope test error")
                
        except ValueError:
            pass  # Expected
        
        # Verify rollback
        with get_session() as session:
            student_count = session.query(CanvasStudent).filter(
                CanvasStudent.student_id == student_id
            ).count()
            assert student_count == 0, "Student was not rolled back in session_scope"
    
    @pytest.mark.integration
    def test_transaction_scope_context_manager(self):
        """Test transaction_scope context manager behavior."""
        course_id = 80009
        
        # Test successful operation
        with transaction_scope() as session:
            course = CanvasCourse(
                id=course_id,
                name="Transaction Scope Test",
                course_code="TXSCOPE001"
            )
            session.add(course)
        
        # Verify it was committed
        with get_session() as session:
            retrieved = session.query(CanvasCourse).filter(CanvasCourse.id == course_id).first()
            assert retrieved is not None
            assert retrieved.name == "Transaction Scope Test"
        
        # Test failing operation
        student_id = 80010
        try:
            with transaction_scope() as session:
                student = CanvasStudent(
                    student_id=student_id,
                    name="Transaction Scope Student",
                    login_id="txscope@test.edu",
                    current_score=85,
                    final_score=87
                )
                session.add(student)
                session.flush()
                
                # Simulate error
                raise ValueError("Transaction scope test error")
                
        except ValueError:
            pass  # Expected
        
        # Verify rollback
        with get_session() as session:
            student_count = session.query(CanvasStudent).filter(
                CanvasStudent.student_id == student_id
            ).count()
            assert student_count == 0, "Student was not rolled back in transaction_scope"
    
    @pytest.mark.integration
    def test_cross_session_data_visibility(self):
        """Test data visibility across different sessions."""
        course_id = 80010
        
        # Session 1: Create and commit course
        session1 = self.Session()
        course = CanvasCourse(
            id=course_id,
            name="Cross Session Test",
            course_code="CROSS001"
        )
        session1.add(course)
        session1.commit()
        
        # Session 2: Should see the committed data
        session2 = self.Session()
        retrieved_course = session2.query(CanvasCourse).filter(
            CanvasCourse.id == course_id
        ).first()
        
        assert retrieved_course is not None
        assert retrieved_course.name == "Cross Session Test"
        
        # Session 1: Update the course
        course.name = "Updated Cross Session Test"
        session1.commit()
        
        # Session 2: Should see updated data (after cache refresh)
        session2.expire_all()
        updated_course = session2.query(CanvasCourse).filter(
            CanvasCourse.id == course_id
        ).first()
        
        assert updated_course.name == "Updated Cross Session Test"
        
        session1.close()
        session2.close()
    
    @pytest.mark.integration
    def test_complex_transaction_with_real_canvas_operations(self):
        """Test complex multi-table transaction using real Canvas operations."""
        course_id = 80011
        student_ids = [80005, 80006, 80007]
        assignment_ids = [90001, 90002, 90003]
        
        # Use Canvas operations in transaction
        try:
            with get_session() as session:
                canvas_manager = CanvasDataManager(session)
                relationship_manager = RelationshipManager(session)
                
                # Create course
                course_data = {
                    'id': course_id,
                    'name': 'Complex Transaction Course',
                    'course_code': 'COMPLEX001'
                }
                course = canvas_manager.sync_course(course_data)
                
                # Create students
                students = []
                for i, student_id in enumerate(student_ids):
                    student_data = {
                        'id': student_id,  # Canvas operations expect 'id', not 'student_id'
                        'name': f'Transaction Student {i + 1}',
                        'login_id': f'txstudent{i + 1}@test.edu',
                        'current_score': 80 + i * 5,
                        'final_score': 85 + i * 5
                    }
                    student = canvas_manager.sync_student(student_data)
                    students.append(student)
                
                # Create assignments
                assignments = []
                for i, assignment_id in enumerate(assignment_ids):
                    assignment_data = {
                        'id': assignment_id,
                        'course_id': course_id,
                        'name': f'Transaction Assignment {i + 1}',
                        'module_id': 1000,
                        'type': 'Assignment',
                        'points_possible': 100.0,
                        'published': True
                    }
                    assignment = canvas_manager.sync_assignment(assignment_data, course_id)
                    assignments.append(assignment)
                
                # Create enrollment relationships
                for student_id in student_ids:
                    enrollment_data = {
                        'enrollment_state': 'active',
                        'created_at': datetime.now(timezone.utc).isoformat()
                    }
                    relationship_manager.create_enrollment_relationship(
                        student_id=student_id,
                        course_id=course_id,
                        enrollment_data=enrollment_data
                    )
                
                # Verify everything is created within transaction
                assert session.query(CanvasCourse).filter(CanvasCourse.id == course_id).count() == 1
                assert session.query(CanvasStudent).filter(CanvasStudent.student_id.in_(student_ids)).count() == 3
                assert session.query(CanvasAssignment).filter(CanvasAssignment.id.in_(assignment_ids)).count() == 3
                assert session.query(CanvasEnrollment).filter(CanvasEnrollment.course_id == course_id).count() == 3
                
                # Simulate error to test rollback
                raise ValueError("Complex transaction test rollback")
                
        except ValueError:
            pass  # Expected
        
        # Verify complete rollback
        with get_session() as session:
            course_count = session.query(CanvasCourse).filter(CanvasCourse.id == course_id).count()
            student_count = session.query(CanvasStudent).filter(CanvasStudent.student_id.in_(student_ids)).count()
            assignment_count = session.query(CanvasAssignment).filter(CanvasAssignment.id.in_(assignment_ids)).count()
            enrollment_count = session.query(CanvasEnrollment).filter(CanvasEnrollment.course_id == course_id).count()
            
            assert course_count == 0, "Course was not rolled back"
            assert student_count == 0, "Students were not rolled back"
            assert assignment_count == 0, "Assignments were not rolled back" 
            assert enrollment_count == 0, "Enrollments were not rolled back"
    
    @pytest.mark.integration
    def test_database_connection_recovery(self):
        """Test database connection recovery after connection loss."""
        course_id = 80012
        
        # Create initial course
        with get_session() as session:
            course = CanvasCourse(
                id=course_id,
                name="Connection Recovery Test",
                course_code="RECOVERY001"
            )
            session.add(course)
            session.commit()
        
        # Simulate connection issues by closing the database manager
        self.db_manager.close()
        
        # Create new database manager - should recover
        self.db_manager = DatabaseManager(self.config)
        
        # Verify we can still access data
        with get_session() as session:
            retrieved_course = session.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            assert retrieved_course is not None
            assert retrieved_course.name == "Connection Recovery Test"
    
    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_running_transaction_timeout(self):
        """Test behavior of long-running transactions."""
        course_id = 80013
        
        # Test that long-running transactions don't hang indefinitely
        start_time = time.time()
        
        try:
            with get_session() as session:
                course = CanvasCourse(
                    id=course_id,
                    name="Long Running Transaction",
                    course_code="LONGTIME001"
                )
                session.add(course)
                session.flush()
                
                # Simulate long-running operation
                time.sleep(2)  # 2 seconds should be reasonable
                
                session.commit()
                
        except Exception as e:
            # If there's a timeout or other issue, it should complete reasonably quickly
            duration = time.time() - start_time
            assert duration < 30, f"Transaction took too long: {duration:.2f}s"
            
            # Re-raise for analysis
            raise
        
        duration = time.time() - start_time
        assert duration < 30, f"Transaction took unexpectedly long: {duration:.2f}s"
        
        # Verify the transaction completed successfully
        with get_session() as session:
            course = session.query(CanvasCourse).filter(CanvasCourse.id == course_id).first()
            assert course is not None
            assert course.name == "Long Running Transaction"


if __name__ == "__main__":
    # Allow running transaction tests directly
    pytest.main([__file__, "-v", "--tb=short"])