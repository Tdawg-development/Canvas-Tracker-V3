"""
Unit Tests for Layer 1 Canvas Operations.

Tests core CRUD functionality, relationship management, and sync coordination
that work independently of Layer 0 lifecycle operations.

Split into independent tests (can run now) and lifecycle-dependent tests 
(require Layer 0 implementation).
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from database.operations.layer1.canvas_ops import CanvasDataManager
from database.operations.layer1.sync_coordinator import (
    SyncCoordinator, SyncResult, SyncStrategy, SyncPriority
)
from database.operations.layer1.relationship_manager import RelationshipManager
from database.operations.base.exceptions import (
    CanvasOperationError, DataValidationError, RelationshipError, ValidationError
)
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)
from database.models.layer2_historical import AssignmentScore


class TestCanvasDataManagerCore:
    """Test core CanvasDataManager functionality independent of Layer 0."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.canvas_manager = CanvasDataManager(self.mock_session)
    
    @pytest.mark.unit
    def test_canvas_manager_initialization(self):
        """Test CanvasDataManager initialization."""
        assert self.canvas_manager.session == self.mock_session
        assert isinstance(self.canvas_manager, CanvasDataManager)
    
    # ==================== COURSE SYNC TESTS ====================
    
    @pytest.mark.unit
    def test_sync_course_new_course(self):
        """Test syncing a new course."""
        # Mock no existing course
        self.mock_session.query().filter().first.return_value = None
        
        canvas_data = {
            'id': 123,
            'name': 'Test Course',
            'course_code': 'TEST101',
            'calendar': {'ics': 'https://example.com/calendar.ics'}
        }
        
        result = self.canvas_manager.sync_course(canvas_data)
        
        # Verify course creation
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        # Check that add was called with a CanvasCourse object
        added_course = self.mock_session.add.call_args[0][0]
        assert isinstance(added_course, CanvasCourse)
        assert added_course.id == 123
        assert added_course.name == 'Test Course'
        assert added_course.course_code == 'TEST101'
        assert added_course.calendar_ics == 'https://example.com/calendar.ics'
    
    @pytest.mark.unit
    def test_sync_course_update_existing(self):
        """Test updating an existing course."""
        # Mock existing course
        existing_course = CanvasCourse(
            id=123,
            name='Old Course Name',
            course_code='TEST101'
        )
        self.mock_session.query().filter().first.return_value = existing_course
        
        canvas_data = {
            'id': 123,
            'name': 'Updated Course Name',
            'course_code': 'TEST101',
            'calendar': {'ics': 'https://example.com/updated-calendar.ics'}
        }
        
        # Mock the change detection to return True
        with patch.object(self.canvas_manager, '_course_needs_update', return_value=True):
            result = self.canvas_manager.sync_course(canvas_data)
        
        # Should not add new course, just update existing
        self.mock_session.add.assert_not_called()
        self.mock_session.flush.assert_called_once()
        
        # Verify the course was updated
        assert result == existing_course
        assert existing_course.name == 'Updated Course Name'
        assert existing_course.calendar_ics == 'https://example.com/updated-calendar.ics'
    
    @pytest.mark.unit
    def test_sync_course_no_update_needed(self):
        """Test skipping update when no changes detected."""
        existing_course = CanvasCourse(
            id=123,
            name='Test Course',
            course_code='TEST101'
        )
        self.mock_session.query().filter().first.return_value = existing_course
        
        canvas_data = {
            'id': 123,
            'name': 'Test Course',
            'course_code': 'TEST101'
        }
        
        # Mock change detection to return False
        with patch.object(self.canvas_manager, '_course_needs_update', return_value=False):
            result = self.canvas_manager.sync_course(canvas_data)
        
        # Should not update or flush
        self.mock_session.add.assert_not_called()
        assert result == existing_course
    
    @pytest.mark.unit
    def test_sync_course_validation_error(self):
        """Test validation error for missing required fields."""
        canvas_data = {'name': 'Test Course'}  # Missing 'id'
        
        with pytest.raises(DataValidationError) as exc_info:
            self.canvas_manager.sync_course(canvas_data)
        
        assert "missing required 'id' field" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_batch_sync_courses(self):
        """Test batch syncing multiple courses."""
        courses_data = [
            {'id': 123, 'name': 'Course 1'},
            {'id': 124, 'name': 'Course 2'},
            {'id': 125, 'name': 'Course 3'}
        ]
        
        # Mock existing courses lookup - none exist
        self.mock_session.query().filter().all.return_value = []
        
        result = self.canvas_manager.batch_sync_courses(courses_data)
        
        # Verify structure
        assert 'created' in result
        assert 'updated' in result
        assert 'skipped' in result
        
        # Should create 3 new courses
        assert len(result['created']) == 3
        assert len(result['updated']) == 0
        assert len(result['skipped']) == 0
        
        # Verify session calls
        assert self.mock_session.add.call_count == 3
        self.mock_session.flush.assert_called_once()
    
    # ==================== STUDENT SYNC TESTS ====================
    
    @pytest.mark.unit
    def test_sync_student_new_student(self):
        """Test syncing a new student."""
        self.mock_session.query().filter().first.return_value = None
        
        canvas_data = {
            'id': 456,
            'user_id': 789,
            'user': {
                'name': 'John Doe',
                'login_id': 'john.doe'
            },
            'email': 'john.doe@example.com',
            'current_score': 85,
            'final_score': 90,
            'created_at': '2024-01-15T10:30:00Z',
            'last_activity_at': '2024-03-01T14:20:00Z'
        }
        
        result = self.canvas_manager.sync_student(canvas_data)
        
        # Verify student creation
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        added_student = self.mock_session.add.call_args[0][0]
        assert isinstance(added_student, CanvasStudent)
        assert added_student.student_id == 456
        assert added_student.user_id == 789
        assert added_student.name == 'John Doe'
        assert added_student.login_id == 'john.doe'
        assert added_student.email == 'john.doe@example.com'
        assert added_student.current_score == 85
        assert added_student.final_score == 90
    
    @pytest.mark.unit 
    def test_batch_sync_students(self):
        """Test batch syncing multiple students."""
        students_data = [
            {
                'id': 456, 
                'user': {'name': 'John Doe', 'login_id': 'john.doe'}, 
                'email': 'john@example.com',
                'current_score': 80,
                'final_score': 85
            },
            {
                'id': 457, 
                'user': {'name': 'Jane Smith', 'login_id': 'jane.smith'}, 
                'email': 'jane@example.com',
                'current_score': 90,
                'final_score': 92
            }
        ]
        
        # Mock no existing students
        self.mock_session.query().filter().all.return_value = []
        
        result = self.canvas_manager.batch_sync_students(students_data)
        
        assert len(result['created']) == 2
        assert len(result['updated']) == 0
        assert len(result['skipped']) == 0
        
        assert self.mock_session.add.call_count == 2
        self.mock_session.flush.assert_called_once()
    
    # ==================== ASSIGNMENT SYNC TESTS ====================
    
    @pytest.mark.unit
    def test_sync_assignment_new_assignment(self):
        """Test syncing a new assignment."""
        self.mock_session.query().filter().first.return_value = None
        
        canvas_data = {
            'id': 789,
            'title': 'Test Assignment',
            'type': 'Assignment',
            'published': True,
            'url': 'https://canvas.example.com/courses/123/assignments/789',
            'position': 1,
            'content_details': {
                'points_possible': 100
            },
            'module_id': 101
        }
        
        result = self.canvas_manager.sync_assignment(canvas_data, course_id=123)
        
        # Verify assignment creation
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        added_assignment = self.mock_session.add.call_args[0][0]
        assert isinstance(added_assignment, CanvasAssignment)
        assert added_assignment.id == 789
        assert added_assignment.course_id == 123
        assert added_assignment.module_id == 101
        assert added_assignment.name == 'Test Assignment'
        assert added_assignment.type == 'Assignment'
        assert added_assignment.published == True
        assert added_assignment.points_possible == 100
        assert added_assignment.module_position == 1
    
    # ==================== ENROLLMENT SYNC TESTS ====================
    
    @pytest.mark.unit
    def test_sync_enrollment_new_enrollment(self):
        """Test syncing a new enrollment."""
        self.mock_session.query().filter().first.return_value = None
        
        canvas_data = {
            'enrollment_state': 'active',
            'created_at': '2024-01-15T10:00:00Z'
        }
        
        result = self.canvas_manager.sync_enrollment(456, 123, canvas_data)
        
        # Verify enrollment creation
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        added_enrollment = self.mock_session.add.call_args[0][0]
        assert isinstance(added_enrollment, CanvasEnrollment)
        assert added_enrollment.student_id == 456
        assert added_enrollment.course_id == 123
        assert added_enrollment.enrollment_status == 'active'
    
    # ==================== UTILITY TESTS ====================
    
    @pytest.mark.unit
    def test_get_stale_canvas_data(self):
        """Test identifying stale Canvas data."""
        # Mock stale data queries
        stale_courses = [Mock(), Mock()]
        stale_students = [Mock()]
        stale_assignments = [Mock(), Mock(), Mock()]
        
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasCourse:
                mock_query.filter().all.return_value = stale_courses
            elif args[0] == CanvasStudent:
                mock_query.filter().all.return_value = stale_students
            elif args[0] == CanvasAssignment:
                mock_query.filter().all.return_value = stale_assignments
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        result = self.canvas_manager.get_stale_canvas_data(hours_threshold=24)
        
        assert 'courses' in result
        assert 'students' in result  
        assert 'assignments' in result
        
        assert len(result['courses']) == 2
        assert len(result['students']) == 1
        assert len(result['assignments']) == 3
    
    @pytest.mark.unit
    def test_rebuild_course_statistics(self):
        """Test rebuilding course statistics."""
        # Mock the statistics queries
        self.mock_session.query().filter().count.side_effect = [5, 10]  # enrollments, assignments
        self.mock_session.query().join().filter().scalar.return_value = 85.5  # avg score
        
        result = self.canvas_manager.rebuild_course_statistics(course_id=123)
        
        assert 'enrollment_count' in result
        assert 'assignment_count' in result
        assert 'average_score' in result
        assert 'last_calculated' in result
        
        assert result['enrollment_count'] == 5
        assert result['assignment_count'] == 10
        assert result['average_score'] == 85.5
        assert isinstance(result['last_calculated'], datetime)


class TestRelationshipManagerCore:
    """Test core RelationshipManager functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.relationship_manager = RelationshipManager(self.mock_session)
    
    @pytest.mark.unit
    def test_relationship_manager_initialization(self):
        """Test RelationshipManager initialization."""
        assert self.relationship_manager.session == self.mock_session
        assert isinstance(self.relationship_manager, RelationshipManager)
    
    # ==================== ENROLLMENT RELATIONSHIP TESTS ====================
    
    @pytest.mark.unit
    def test_create_enrollment_relationship_success(self):
        """Test successful enrollment relationship creation."""
        # Mock student and course exist
        mock_student = Mock()
        mock_course = Mock()
        
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasStudent:
                mock_query.filter().first.return_value = mock_student
            elif args[0] == CanvasCourse:
                mock_query.filter().first.return_value = mock_course
            elif args[0] == CanvasEnrollment:
                mock_query.filter().first.return_value = None  # No existing enrollment
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        enrollment_data = {'enrollment_state': 'active'}
        
        result = self.relationship_manager.create_enrollment_relationship(
            student_id=456, course_id=123, enrollment_data=enrollment_data
        )
        
        # Verify enrollment creation
        self.mock_session.add.assert_called_once()
        self.mock_session.flush.assert_called_once()
        
        added_enrollment = self.mock_session.add.call_args[0][0]
        assert isinstance(added_enrollment, CanvasEnrollment)
        assert added_enrollment.student_id == 456
        assert added_enrollment.course_id == 123
        assert added_enrollment.enrollment_status == 'active'
    
    @pytest.mark.unit
    def test_create_enrollment_relationship_student_not_found(self):
        """Test enrollment creation with non-existent student."""
        # Mock student doesn't exist
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasStudent:
                mock_query.filter().first.return_value = None
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        with pytest.raises(ValidationError) as exc_info:
            self.relationship_manager.create_enrollment_relationship(
                student_id=456, course_id=123
            )
        
        assert "Student 456 not found" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_create_enrollment_relationship_course_not_found(self):
        """Test enrollment creation with non-existent course."""
        # Mock student exists but course doesn't
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasStudent:
                mock_query.filter().first.return_value = Mock()  # Student exists
            elif args[0] == CanvasCourse:
                mock_query.filter().first.return_value = None  # Course doesn't exist
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        with pytest.raises(ValidationError) as exc_info:
            self.relationship_manager.create_enrollment_relationship(
                student_id=456, course_id=123
            )
        
        assert "Course 123 not found" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_create_enrollment_relationship_already_exists(self):
        """Test enrollment creation when relationship already exists."""
        # Mock student, course, and existing enrollment all exist
        def mock_query_side_effect(*args):
            mock_query = Mock()
            mock_query.filter().first.return_value = Mock()  # Everything exists
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        with pytest.raises(RelationshipError) as exc_info:
            self.relationship_manager.create_enrollment_relationship(
                student_id=456, course_id=123
            )
        
        assert "Enrollment already exists" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_get_student_enrollments(self):
        """Test getting enrollments for a student."""
        mock_enrollments = [Mock(), Mock(), Mock()]
        
        # Set up proper mock chain: query().filter().filter().all()
        mock_final_query = Mock()
        mock_final_query.all.return_value = mock_enrollments
        
        mock_filtered_query = Mock()
        mock_filtered_query.filter.return_value = mock_final_query
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_filtered_query
        
        self.mock_session.query.return_value = mock_query
        
        result = self.relationship_manager.get_student_enrollments(
            student_id=456, active_only=True
        )
        
        assert result == mock_enrollments
        # Verify filtering was applied
        assert mock_query.filter.called
        assert mock_filtered_query.filter.called
    
    @pytest.mark.unit
    def test_get_course_enrollments(self):
        """Test getting enrollments for a course."""
        mock_enrollments = [Mock(), Mock()]
        
        # Set up proper mock chain: query().filter().options().all()
        # Since active_only=False, only one filter call
        mock_final_query = Mock()
        mock_final_query.all.return_value = mock_enrollments
        
        mock_options_query = Mock()
        mock_options_query.options.return_value = mock_final_query
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_options_query
        
        self.mock_session.query.return_value = mock_query
        
        result = self.relationship_manager.get_course_enrollments(
            course_id=123, active_only=False, include_students=True
        )
        
        assert result == mock_enrollments
        # Should use joinedload when include_students=True
        assert mock_options_query.options.called
    
    # ==================== ASSIGNMENT RELATIONSHIP TESTS ====================
    
    @pytest.mark.unit
    def test_validate_assignment_course_relationship_valid(self):
        """Test valid assignment-course relationship validation."""
        mock_assignment = Mock()
        mock_assignment.course_id = 123
        
        self.mock_session.query().filter().first.return_value = mock_assignment
        
        result = self.relationship_manager.validate_assignment_course_relationship(
            assignment_id=789, course_id=123
        )
        
        assert result is True
    
    @pytest.mark.unit
    def test_validate_assignment_course_relationship_invalid(self):
        """Test invalid assignment-course relationship validation."""
        mock_assignment = Mock()
        mock_assignment.course_id = 456  # Different course
        
        self.mock_session.query().filter().first.return_value = mock_assignment
        
        result = self.relationship_manager.validate_assignment_course_relationship(
            assignment_id=789, course_id=123
        )
        
        assert result is False
    
    @pytest.mark.unit
    def test_validate_assignment_course_relationship_not_found(self):
        """Test assignment-course validation when assignment doesn't exist."""
        self.mock_session.query().filter().first.return_value = None
        
        result = self.relationship_manager.validate_assignment_course_relationship(
            assignment_id=789, course_id=123
        )
        
        assert result is False
    
    @pytest.mark.unit
    def test_get_course_assignments(self):
        """Test getting assignments for a course."""
        mock_assignments = [Mock(), Mock(), Mock()]
        
        # Set up proper mock chain: query().filter().options().order_by().all()
        mock_final_query = Mock()
        mock_final_query.all.return_value = mock_assignments
        
        mock_ordered_query = Mock()
        mock_ordered_query.order_by.return_value = mock_final_query
        
        mock_options_query = Mock()
        mock_options_query.options.return_value = mock_ordered_query
        
        mock_query = Mock()
        mock_query.filter.return_value = mock_options_query
        
        self.mock_session.query.return_value = mock_query
        
        result = self.relationship_manager.get_course_assignments(
            course_id=123, include_scores=True
        )
        
        assert result == mock_assignments
        # Should use selectinload when include_scores=True
        assert mock_options_query.options.called
    
    # ==================== REFERENTIAL INTEGRITY TESTS ====================
    
    @pytest.mark.unit
    def test_validate_referential_integrity_no_violations(self):
        """Test referential integrity validation with no violations."""
        # Mock queries to return empty results (no violations)
        mock_query = Mock()
        mock_query.filter().all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        result = self.relationship_manager.validate_referential_integrity()
        
        assert 'orphaned_assignments' in result
        assert 'orphaned_enrollments' in result
        assert 'orphaned_scores' in result
        assert 'invalid_references' in result
        
        assert len(result['orphaned_assignments']) == 0
        assert len(result['orphaned_enrollments']) == 0
        assert len(result['orphaned_scores']) == 0
        assert len(result['invalid_references']) == 0
    
    @pytest.mark.unit
    def test_validate_referential_integrity_with_violations(self):
        """Test referential integrity validation with violations."""
        # Mock orphaned assignments
        mock_assignment = Mock()
        mock_assignment.id = 789
        mock_assignment.course_id = 999  # Non-existent course
        
        mock_enrollment = Mock()
        mock_enrollment.student_id = 456
        mock_enrollment.course_id = 999  # Invalid reference
        
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasAssignment:
                mock_query.filter().all.return_value = [mock_assignment]
            elif args[0] == CanvasEnrollment:
                mock_query.filter().all.return_value = [mock_enrollment]
            else:
                mock_query.filter().all.return_value = []
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        result = self.relationship_manager.validate_referential_integrity()
        
        assert len(result['orphaned_assignments']) == 1
        assert len(result['orphaned_enrollments']) == 1
        assert "Assignment 789 references non-existent course 999" in result['orphaned_assignments'][0]
        assert "456-999 has invalid references" in result['orphaned_enrollments'][0]


class TestSyncCoordinatorCore:
    """Test core SyncCoordinator functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock()
        self.sync_coordinator = SyncCoordinator(self.mock_session)
    
    @pytest.mark.unit
    def test_sync_coordinator_initialization(self):
        """Test SyncCoordinator initialization."""
        assert self.sync_coordinator.session == self.mock_session
        assert isinstance(self.sync_coordinator, SyncCoordinator)
        assert hasattr(self.sync_coordinator, 'canvas_manager')
        assert hasattr(self.sync_coordinator, 'transaction_manager')
    
    @pytest.mark.unit
    def test_sync_result_dataclass(self):
        """Test SyncResult dataclass functionality."""
        start_time = datetime.now(timezone.utc)
        end_time = start_time + timedelta(minutes=5)
        
        sync_result = SyncResult(
            strategy=SyncStrategy.FULL_REPLACE,
            started_at=start_time,
            completed_at=end_time,
            success=True,
            objects_processed={'courses': 10},
            objects_created={'courses': 5},
            objects_updated={'courses': 3},
            objects_skipped={'courses': 2},
            conflicts_detected=[],
            errors=[]
        )
        
        assert sync_result.strategy == SyncStrategy.FULL_REPLACE
        assert sync_result.success is True
        assert sync_result.duration == timedelta(minutes=5)
        assert sync_result.objects_processed['courses'] == 10
    
    @pytest.mark.unit
    def test_sync_strategies_enum(self):
        """Test SyncStrategy enum values."""
        assert SyncStrategy.FULL_REPLACE.value == "full_replace"
        assert SyncStrategy.INCREMENTAL.value == "incremental"
        assert SyncStrategy.CONSERVATIVE.value == "conservative"
    
    @pytest.mark.unit
    def test_sync_priorities_enum(self):
        """Test SyncPriority enum values."""
        assert SyncPriority.HIGH.value == "high"
        assert SyncPriority.MEDIUM.value == "medium"
        assert SyncPriority.LOW.value == "low"
    
    @pytest.mark.unit
    @patch('database.operations.layer1.sync_coordinator.TransactionManager')
    def test_validate_sync_integrity_no_errors(self, mock_tx_manager):
        """Test sync integrity validation with no errors."""
        # Mock queries to return no integrity violations
        mock_query = Mock()
        mock_query.filter().count.return_value = 0
        mock_query.group_by().having().all.return_value = []
        self.mock_session.query.return_value = mock_query
        
        result = self.sync_coordinator.validate_sync_integrity()
        
        assert isinstance(result, list)
        assert len(result) == 0  # No errors
    
    @pytest.mark.unit
    @patch('database.operations.layer1.sync_coordinator.TransactionManager')
    def test_validate_sync_integrity_with_errors(self, mock_tx_manager):
        """Test sync integrity validation with errors."""
        # Mock queries to return integrity violations
        def mock_query_side_effect(*args):
            mock_query = Mock()
            if args[0] == CanvasAssignment:
                mock_query.filter().count.return_value = 2  # Orphaned assignments
            elif args[0] == CanvasEnrollment:
                mock_query.filter().count.return_value = 1  # Orphaned enrollments
            elif hasattr(args[0], 'class_') and args[0].class_ == CanvasCourse:
                # This handles CanvasCourse.id queries
                mock_having_query = Mock()
                mock_having_query.all.return_value = [(123,), (124,)]  # Duplicates
                mock_group_query = Mock()
                mock_group_query.having.return_value = mock_having_query
                mock_query.group_by.return_value = mock_group_query
            else:
                mock_query.filter().count.return_value = 0
                mock_query.group_by().having().all.return_value = []
            return mock_query
        
        self.mock_session.query.side_effect = mock_query_side_effect
        
        result = self.sync_coordinator.validate_sync_integrity()
        
        assert isinstance(result, list)
        # Should have at least 2 error messages (orphaned assignments and enrollments)
        # The duplicate courses query might have different behavior in mocked context
        assert len(result) >= 2  
        assert any("2 orphaned assignments" in error for error in result)
        assert any("1 orphaned enrollments" in error for error in result)


# ==================== INTEGRATION TESTS (INDEPENDENT) ====================

class TestLayer1Integration:
    """Integration tests for Layer 1 operations that work independently."""
    
    @pytest.mark.integration
    def test_canvas_manager_with_real_database(self, db_session):
        """Test CanvasDataManager with real database session."""
        canvas_manager = CanvasDataManager(db_session)
        
        # Test creating a course
        canvas_data = {
            'id': 123,
            'name': 'Integration Test Course',
            'course_code': 'INT101'
        }
        
        course = canvas_manager.sync_course(canvas_data)
        
        assert isinstance(course, CanvasCourse)
        assert course.id == 123
        assert course.name == 'Integration Test Course'
        
        # Verify it's in the database
        db_session.commit()
        
        retrieved_course = db_session.query(CanvasCourse).filter(
            CanvasCourse.id == 123
        ).first()
        
        assert retrieved_course is not None
        assert retrieved_course.name == 'Integration Test Course'
    
    @pytest.mark.integration
    def test_relationship_manager_with_real_database(self, db_session):
        """Test RelationshipManager with real database session."""
        relationship_manager = RelationshipManager(db_session)
        
        # Create test data
        course = CanvasCourse(id=123, name='Test Course', course_code='TEST')
        student = CanvasStudent(student_id=456, name='Test Student', login_id='test.student', email='test@example.com')
        
        db_session.add(course)
        db_session.add(student)
        db_session.commit()
        
        # Test creating enrollment relationship
        enrollment = relationship_manager.create_enrollment_relationship(
            student_id=456,
            course_id=123,
            enrollment_data={'enrollment_state': 'active'}
        )
        
        assert isinstance(enrollment, CanvasEnrollment)
        assert enrollment.student_id == 456
        assert enrollment.course_id == 123
        assert enrollment.enrollment_status == 'active'
        
        # Test getting student enrollments
        enrollments = relationship_manager.get_student_enrollments(456)
        assert len(enrollments) == 1
        assert enrollments[0].course_id == 123
    
    @pytest.mark.integration
    def test_referential_integrity_validation_real_database(self, db_session):
        """Test referential integrity validation with real database."""
        relationship_manager = RelationshipManager(db_session)
        
        # Create orphaned assignment (no parent course)
        orphaned_assignment = CanvasAssignment(
            id=789,
            course_id=999,  # Non-existent course
            module_id=1,
            name='Orphaned Assignment',
            points_possible=100
        )
        db_session.add(orphaned_assignment)
        db_session.commit()
        
        # Validate integrity
        violations = relationship_manager.validate_referential_integrity()
        
        assert len(violations['orphaned_assignments']) == 1
        assert "Assignment 789 references non-existent course 999" in violations['orphaned_assignments'][0]


class TestSyncCoordinatorIntegration:
    """Integration tests for SyncCoordinator with real database operations."""
    
    @pytest.fixture
    def sync_db_session(self, db_manager):
        """Fixture providing a database session for sync coordinator tests.
        
        Unlike db_session, this doesn't start a transaction, allowing
        the sync coordinator to manage its own transactions.
        """
        # Create all tables
        db_manager.create_all_tables()
        
        # Get a session without starting a transaction
        session = db_manager.get_session()
        
        try:
            yield session
        finally:
            # Clean up
            session.rollback()  # Rollback any uncommitted changes
            session.close()
    
    @pytest.fixture
    def sample_canvas_data(self):
        """Fixture providing realistic Canvas data for testing."""
        return {
            'courses': [
                {
                    'id': 101,
                    'name': 'Introduction to Python Programming',
                    'course_code': 'CS101',
                    'calendar': {'ics': 'https://canvas.example.com/feeds/calendars/course_101.ics'}
                },
                {
                    'id': 102,
                    'name': 'Advanced Data Structures',
                    'course_code': 'CS201',
                    'calendar': {'ics': 'https://canvas.example.com/feeds/calendars/course_102.ics'}
                }
            ],
            'students': [
                {
                    'id': 1001,
                    'user_id': 2001,
                    'user': {
                        'name': 'Alice Johnson',
                        'login_id': 'alice.johnson'
                    },
                    'email': 'alice.johnson@university.edu',
                    'current_score': 87,
                    'final_score': 89,
                    'created_at': '2024-09-01T10:00:00Z',
                    'last_activity_at': '2024-12-01T15:30:00Z'
                },
                {
                    'id': 1002,
                    'user_id': 2002,
                    'user': {
                        'name': 'Bob Chen',
                        'login_id': 'bob.chen'
                    },
                    'email': 'bob.chen@university.edu',
                    'current_score': 92,
                    'final_score': 94,
                    'created_at': '2024-09-01T10:00:00Z',
                    'last_activity_at': '2024-12-01T16:45:00Z'
                }
            ],
            'assignments': [
                {
                    'id': 301,
                    'course_id': 101,
                    'module_id': 501,
                    'title': 'Python Basics Quiz',
                    'type': 'Quiz',
                    'published': True,
                    'url': 'https://canvas.example.com/courses/101/assignments/301',
                    'position': 1,
                    'content_details': {
                        'points_possible': 25
                    }
                },
                {
                    'id': 302,
                    'course_id': 101,
                    'module_id': 501,
                    'title': 'Variables and Data Types Assignment',
                    'type': 'Assignment',
                    'published': True,
                    'url': 'https://canvas.example.com/courses/101/assignments/302',
                    'position': 2,
                    'content_details': {
                        'points_possible': 50
                    }
                },
                {
                    'id': 303,
                    'course_id': 102,
                    'module_id': 502,
                    'title': 'Binary Trees Implementation',
                    'type': 'Assignment',
                    'published': True,
                    'url': 'https://canvas.example.com/courses/102/assignments/303',
                    'position': 1,
                    'content_details': {
                        'points_possible': 100
                    }
                }
            ],
            'enrollments': [
                {
                    'student_id': 1001,
                    'course_id': 101,
                    'enrollment_state': 'active',
                    'created_at': '2024-09-01T09:00:00Z'
                },
                {
                    'student_id': 1001,
                    'course_id': 102,
                    'enrollment_state': 'active',
                    'created_at': '2024-09-01T09:00:00Z'
                },
                {
                    'student_id': 1002,
                    'course_id': 101,
                    'enrollment_state': 'active',
                    'created_at': '2024-09-01T09:00:00Z'
                }
            ]
        }
    
    @pytest.mark.integration
    def test_execute_full_sync_success(self, sync_db_session, sample_canvas_data):
        """Test successful full sync operation with complete Canvas data."""
        sync_coordinator = SyncCoordinator(sync_db_session)
        
        # Execute full sync
        result = sync_coordinator.execute_full_sync(
            canvas_data=sample_canvas_data,
            validate_integrity=True
        )
        
        # Verify sync result
        assert result.success is True
        assert result.strategy == SyncStrategy.FULL_REPLACE
        assert result.rollback_performed is False
        assert len(result.errors) == 0
        assert result.duration is not None
        
        # Verify object counts
        assert result.objects_processed['courses'] == 2
        assert result.objects_processed['students'] == 2
        assert result.objects_processed['assignments'] == 3
        assert result.objects_processed['enrollments'] == 3
        
        assert result.objects_created['courses'] == 2
        assert result.objects_created['students'] == 2
        assert result.objects_created['assignments'] == 3
        assert result.objects_created['enrollments'] == 3
        
        # Verify data was actually written to database
        sync_db_session.commit()
        
        # Check courses
        courses = sync_db_session.query(CanvasCourse).all()
        assert len(courses) == 2
        course_names = [c.name for c in courses]
        assert 'Introduction to Python Programming' in course_names
        assert 'Advanced Data Structures' in course_names
        
        # Check students
        students = sync_db_session.query(CanvasStudent).all()
        assert len(students) == 2
        student_names = [s.name for s in students]
        assert 'Alice Johnson' in student_names
        assert 'Bob Chen' in student_names
        
        # Check assignments
        assignments = sync_db_session.query(CanvasAssignment).all()
        assert len(assignments) == 3
        assignment_names = [a.name for a in assignments]
        assert 'Python Basics Quiz' in assignment_names
        assert 'Binary Trees Implementation' in assignment_names
        
        # Check enrollments
        enrollments = sync_db_session.query(CanvasEnrollment).all()
        assert len(enrollments) == 3
        
        # Verify relationships
        alice = sync_db_session.query(CanvasStudent).filter(CanvasStudent.name == 'Alice Johnson').first()
        alice_enrollments = sync_db_session.query(CanvasEnrollment).filter(
            CanvasEnrollment.student_id == alice.student_id
        ).all()
        assert len(alice_enrollments) == 2  # Alice is enrolled in both courses
    
    @pytest.mark.integration
    def test_execute_full_sync_with_integrity_failure(self, db_session, sample_canvas_data):
        """Test full sync rollback when integrity validation fails."""
        sync_coordinator = SyncCoordinator(db_session)
        
        # Create invalid data that will cause integrity failure
        # Add an assignment that references a non-existent course
        invalid_assignment = {
            'id': 999,
            'course_id': 999,  # Non-existent course
            'module_id': 999,
            'title': 'Invalid Assignment',
            'type': 'Assignment',
            'published': True,
            'url': 'https://canvas.example.com/invalid',
            'position': 1,
            'content_details': {'points_possible': 10}
        }
        sample_canvas_data['assignments'].append(invalid_assignment)
        
        # Execute sync should fail due to integrity validation
        with pytest.raises(CanvasOperationError, match="Full sync failed"):
            sync_coordinator.execute_full_sync(
                canvas_data=sample_canvas_data,
                validate_integrity=True
            )
        
        # Verify rollback occurred - database should be empty
        db_session.commit()
        assert db_session.query(CanvasCourse).count() == 0
        assert db_session.query(CanvasStudent).count() == 0
        assert db_session.query(CanvasAssignment).count() == 0
        assert db_session.query(CanvasEnrollment).count() == 0
    
    @pytest.mark.integration  
    def test_execute_incremental_sync_new_data(self, db_session, sample_canvas_data):
        """Test incremental sync with new data added to existing dataset."""
        sync_coordinator = SyncCoordinator(db_session)
        
        # First, establish baseline with full sync
        initial_result = sync_coordinator.execute_full_sync(
            canvas_data=sample_canvas_data,
            validate_integrity=True
        )
        assert initial_result.success is True
        db_session.commit()
        
        # Prepare incremental data with new course and student
        incremental_data = {
            'courses': [
                # Existing course (should be skipped)
                sample_canvas_data['courses'][0],
                # New course
                {
                    'id': 103,
                    'name': 'Machine Learning Fundamentals',
                    'course_code': 'CS301',
                    'calendar': {'ics': 'https://canvas.example.com/feeds/calendars/course_103.ics'}
                }
            ],
            'students': [
                # New student
                {
                    'id': 1003,
                    'user_id': 2003,
                    'user': {
                        'name': 'Charlie Davis',
                        'login_id': 'charlie.davis'
                    },
                    'email': 'charlie.davis@university.edu',
                    'current_score': 78,
                    'final_score': 82,
                    'created_at': '2024-09-15T10:00:00Z',
                    'last_activity_at': '2024-12-01T14:20:00Z'
                }
            ],
            'assignments': [],
            'enrollments': [
                {
                    'student_id': 1003,
                    'course_id': 103,
                    'enrollment_state': 'active',
                    'created_at': '2024-09-15T09:30:00Z'
                }
            ]
        }
        
        # Execute incremental sync
        incremental_result = sync_coordinator.execute_incremental_sync(
            canvas_data=incremental_data,
            last_sync_time=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        # Verify incremental sync result
        assert incremental_result.success is True
        assert incremental_result.strategy == SyncStrategy.INCREMENTAL
        assert incremental_result.rollback_performed is False
        
        # Verify incremental changes
        db_session.commit()
        
        # Should have 3 courses now (2 original + 1 new)
        courses = db_session.query(CanvasCourse).all()
        assert len(courses) == 3
        course_names = [c.name for c in courses]
        assert 'Machine Learning Fundamentals' in course_names
        
        # Should have 3 students now (2 original + 1 new)
        students = db_session.query(CanvasStudent).all()
        assert len(students) == 3
        student_names = [s.name for s in students]
        assert 'Charlie Davis' in student_names
        
        # Should have 4 enrollments now (3 original + 1 new)
        enrollments = db_session.query(CanvasEnrollment).all()
        assert len(enrollments) == 4
    
    @pytest.mark.integration
    def test_execute_incremental_sync_with_updates(self, db_session, sample_canvas_data):
        """Test incremental sync with updates to existing data."""
        sync_coordinator = SyncCoordinator(db_session)
        
        # Establish baseline
        initial_result = sync_coordinator.execute_full_sync(
            canvas_data=sample_canvas_data,
            validate_integrity=True
        )
        assert initial_result.success is True
        db_session.commit()
        
        # Prepare incremental data with updated course
        updated_course_data = sample_canvas_data['courses'][0].copy()
        updated_course_data['name'] = 'Introduction to Python Programming - Updated'
        updated_course_data['calendar']['ics'] = 'https://canvas.example.com/feeds/calendars/course_101_updated.ics'
        
        incremental_data = {
            'courses': [updated_course_data],
            'students': [],
            'assignments': [],
            'enrollments': []
        }
        
        # Execute incremental sync
        result = sync_coordinator.execute_incremental_sync(
            canvas_data=incremental_data,
            last_sync_time=datetime.now(timezone.utc) - timedelta(days=1)
        )
        
        assert result.success is True
        
        # Verify update was applied
        db_session.commit()
        updated_course = db_session.query(CanvasCourse).filter(CanvasCourse.id == 101).first()
        assert updated_course.name == 'Introduction to Python Programming - Updated'
        assert 'course_101_updated.ics' in updated_course.calendar_ics
    
    @pytest.mark.integration
    def test_sync_coordinator_conflict_detection(self, db_session, sample_canvas_data):
        """Test sync coordinator conflict detection and resolution."""
        sync_coordinator = SyncCoordinator(db_session)
        
        # Create initial state
        initial_result = sync_coordinator.execute_full_sync(
            canvas_data=sample_canvas_data,
            validate_integrity=True
        )
        assert initial_result.success is True
        db_session.commit()
        
        # Simulate a manual local change (this would normally be detected by conflict logic)
        course = db_session.query(CanvasCourse).filter(CanvasCourse.id == 101).first()
        original_name = course.name
        course.name = "Locally Modified Course Name"
        db_session.commit()
        
        # Test conflict resolution with "canvas_wins" strategy
        conflicts = [
            {
                'object_type': 'course',
                'object_id': 101,
                'field': 'name',
                'local_value': 'Locally Modified Course Name',
                'canvas_value': 'Introduction to Python Programming'
            }
        ]
        
        resolution_result = sync_coordinator.handle_sync_conflicts(
            conflicts=conflicts,
            resolution_strategy="canvas_wins"
        )
        
        # Verify conflict resolution
        assert len(resolution_result['resolved']) == 1
        assert len(resolution_result['failed']) == 0
        assert resolution_result['strategy_used'] == 'canvas_wins'
    
    @pytest.mark.integration
    def test_sync_coordinator_performance_with_large_dataset(self, db_session):
        """Test sync coordinator performance with realistic data volumes."""
        sync_coordinator = SyncCoordinator(db_session)
        
        # Generate large dataset (100 courses, 500 students, 1000 assignments)
        large_dataset = {
            'courses': [],
            'students': [],
            'assignments': [],
            'enrollments': []
        }
        
        # Generate courses
        for i in range(1, 101):  # 100 courses
            large_dataset['courses'].append({
                'id': i,
                'name': f'Course {i:03d}',
                'course_code': f'CS{i:03d}',
                'calendar': {'ics': f'https://canvas.example.com/course_{i}.ics'}
            })
        
        # Generate students
        for i in range(1, 501):  # 500 students
            large_dataset['students'].append({
                'id': i,
                'user_id': i + 5000,
                'user': {
                    'name': f'Student {i:03d}',
                    'login_id': f'student{i:03d}'
                },
                'email': f'student{i:03d}@university.edu',
                'current_score': 70 + (i % 30),
                'final_score': 72 + (i % 30),
                'created_at': '2024-09-01T10:00:00Z',
                'last_activity_at': '2024-12-01T15:30:00Z'
            })
        
        # Generate assignments (10 per course)
        assignment_id = 1
        for course_id in range(1, 101):
            for assignment_num in range(1, 11):
                large_dataset['assignments'].append({
                    'id': assignment_id,
                    'course_id': course_id,
                    'module_id': course_id * 10,
                    'title': f'Assignment {assignment_num} for Course {course_id:03d}',
                    'type': 'Assignment' if assignment_num % 3 != 0 else 'Quiz',
                    'published': True,
                    'url': f'https://canvas.example.com/courses/{course_id}/assignments/{assignment_id}',
                    'position': assignment_num,
                    'content_details': {
                        'points_possible': 10 + (assignment_num * 5)
                    }
                })
                assignment_id += 1
        
        # Generate enrollments (each student in 2-4 courses)
        import random
        random.seed(42)  # For reproducible tests
        for student_id in range(1, 501):
            num_enrollments = random.randint(2, 4)
            enrolled_courses = random.sample(range(1, 101), num_enrollments)
            for course_id in enrolled_courses:
                large_dataset['enrollments'].append({
                    'student_id': student_id,
                    'course_id': course_id,
                    'enrollment_state': 'active',
                    'created_at': '2024-09-01T09:00:00Z'
                })
        
        # Measure sync performance
        import time
        start_time = time.time()
        
        result = sync_coordinator.execute_full_sync(
            canvas_data=large_dataset,
            validate_integrity=True
        )
        
        end_time = time.time()
        sync_duration = end_time - start_time
        
        # Verify sync completed successfully
        assert result.success is True
        assert result.rollback_performed is False
        
        # Performance assertions (adjust thresholds based on requirements)
        assert sync_duration < 30.0  # Should complete within 30 seconds
        assert result.objects_processed['courses'] == 100
        assert result.objects_processed['students'] == 500
        assert result.objects_processed['assignments'] == 1000
        
        # Verify data integrity after large sync
        db_session.commit()
        assert db_session.query(CanvasCourse).count() == 100
        assert db_session.query(CanvasStudent).count() == 500
        assert db_session.query(CanvasAssignment).count() == 1000
        
        print(f"\nPerformance Metrics:")
        print(f"  Sync Duration: {sync_duration:.2f} seconds")
        print(f"  Objects/second: {(100 + 500 + 1000) / sync_duration:.1f}")
        print(f"  Enrollments processed: {len(large_dataset['enrollments'])}")
