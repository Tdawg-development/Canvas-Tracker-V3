"""
Unit tests for Query Builder Utilities.

Tests the QueryBuilder class and utility functions for query construction,
parameter validation, joins, and performance optimization across all layers
of the Canvas Tracker database architecture.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from sqlalchemy import select, and_, or_, func, desc, case
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select, CompoundSelect
from sqlalchemy.exc import SQLAlchemyError

# Import the QueryBuilder and utilities
from database.operations.utilities.query_builder import (
    QueryBuilder, 
    optimize_query_performance, 
    add_pagination, 
    add_active_filter
)

# Import models for testing
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)
from database.models.layer2_historical import (
    GradeHistory, AssignmentScore, CourseSnapshot
)
from database.models.layer3_metadata import (
    StudentMetadata, CourseMetadata, AssignmentMetadata
)
from database.models.layer0_lifecycle import (
    ObjectStatus, EnrollmentStatus
)


class TestQueryBuilder:
    """Test suite for QueryBuilder class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.unit
    def test_query_builder_initialization(self):
        """Test QueryBuilder initialization."""
        assert self.query_builder.session == self.mock_session
        
        # Test with different session
        other_session = Mock(spec=Session)
        other_builder = QueryBuilder(other_session)
        assert other_builder.session == other_session
    
    @pytest.mark.unit
    def test_build_student_grades_query_basic(self):
        """Test basic student grades query construction."""
        query = self.query_builder.build_student_grades_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes required columns
        column_labels = [col.name for col in query.selected_columns]
        expected_columns = [
            'student_id', 'student_name', 'course_id', 'course_name',
            'assignment_id', 'assignment_name', 'points_possible',
            'current_score', 'percentage_score', 'submission_date', 'submission_status'
        ]
        
        for expected_col in expected_columns:
            assert expected_col in column_labels
    
    @pytest.mark.unit
    def test_build_student_grades_query_with_filters(self):
        """Test student grades query with various filters."""
        # Test with student ID filter
        query = self.query_builder.build_student_grades_query(student_id=123)
        assert isinstance(query, Select)
        
        # Test with course ID filter  
        query = self.query_builder.build_student_grades_query(course_id=456)
        assert isinstance(query, Select)
        
        # Test with assignment IDs filter
        query = self.query_builder.build_student_grades_query(assignment_ids=[1, 2, 3])
        assert isinstance(query, Select)
        
        # Test with date range filter
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        query = self.query_builder.build_student_grades_query(
            date_range=(start_date, end_date)
        )
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_student_grades_query_with_metadata(self):
        """Test student grades query with metadata inclusion."""
        query = self.query_builder.build_student_grades_query(include_metadata=True)
        
        # Check that metadata columns are included
        column_labels = [col.name for col in query.selected_columns]
        metadata_columns = ['student_notes', 'student_tags', 'assignment_notes', 'difficulty']
        
        for meta_col in metadata_columns:
            assert meta_col in column_labels
    
    @pytest.mark.unit
    def test_build_student_grades_query_with_history(self):
        """Test student grades query with historical data inclusion."""
        query = self.query_builder.build_student_grades_query(include_history=True)
        
        # Check that historical columns are included
        column_labels = [col.name for col in query.selected_columns]
        history_columns = ['previous_score', 'grade_change', 'change_date']
        
        for hist_col in history_columns:
            assert hist_col in column_labels
    
    @pytest.mark.unit
    def test_build_course_enrollment_query_basic(self):
        """Test basic course enrollment query construction."""
        query = self.query_builder.build_course_enrollment_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes required columns
        column_labels = [col.name for col in query.selected_columns]
        expected_columns = [
            'course_id', 'course_name', 'course_code', 'student_id', 'student_name',
            'current_score', 'final_score', 'enrollment_status', 'enrolled_at'
        ]
        
        for expected_col in expected_columns:
            assert expected_col in column_labels
    
    @pytest.mark.unit
    def test_build_course_enrollment_query_with_grades(self):
        """Test course enrollment query with grade summaries."""
        query = self.query_builder.build_course_enrollment_query(include_grades=True)
        
        # Check that grade summary columns are included
        column_labels = [col.name for col in query.selected_columns]
        grade_columns = ['average_score', 'total_assignments', 'missing_count', 'late_count']
        
        for grade_col in grade_columns:
            assert grade_col in column_labels
    
    @pytest.mark.unit
    def test_build_course_enrollment_query_with_metadata(self):
        """Test course enrollment query with metadata inclusion."""
        query = self.query_builder.build_course_enrollment_query(include_metadata=True)
        
        # Check that metadata columns are included
        column_labels = [col.name for col in query.selected_columns]
        metadata_columns = ['student_notes', 'course_notes', 'student_tags', 'course_color', 'course_tracked']
        
        for meta_col in metadata_columns:
            assert meta_col in column_labels
    
    @pytest.mark.unit
    def test_build_assignment_submissions_query_basic(self):
        """Test basic assignment submissions query construction."""
        query = self.query_builder.build_assignment_submissions_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes required columns
        column_labels = [col.name for col in query.selected_columns]
        expected_columns = [
            'assignment_id', 'assignment_name', 'max_points', 'course_id', 'course_name',
            'student_id', 'student_name', 'submission_id', 'score', 'percentage',
            'submitted_at', 'graded_at', 'status'
        ]
        
        for expected_col in expected_columns:
            assert expected_col in column_labels
    
    @pytest.mark.unit
    def test_build_assignment_submissions_query_with_late_analysis(self):
        """Test assignment submissions query with late submission analysis."""
        query = self.query_builder.build_assignment_submissions_query(include_late_submissions=True)
        
        # Check that late submission columns are included
        column_labels = [col.name for col in query.selected_columns]
        late_columns = ['is_late', 'hours_late']
        
        for late_col in late_columns:
            assert late_col in column_labels
    
    @pytest.mark.unit
    def test_build_assignment_submissions_query_with_history(self):
        """Test assignment submissions query with grade history."""
        query = self.query_builder.build_assignment_submissions_query(include_grade_history=True)
        
        # Check that grade history columns are included
        column_labels = [col.name for col in query.selected_columns]
        history_columns = ['previous_score', 'grade_change', 'last_grade_change']
        
        for hist_col in history_columns:
            assert hist_col in column_labels
    
    @pytest.mark.unit
    def test_build_assignment_submissions_query_sorting(self):
        """Test assignment submissions query with different sorting options."""
        # Test sorting by submission date
        query = self.query_builder.build_assignment_submissions_query(sort_by='submission_date')
        assert isinstance(query, Select)
        
        # Test sorting by student name
        query = self.query_builder.build_assignment_submissions_query(sort_by='student_name')
        assert isinstance(query, Select)
        
        # Test sorting by score
        query = self.query_builder.build_assignment_submissions_query(sort_by='score')
        assert isinstance(query, Select)
        
        # Test default sorting
        query = self.query_builder.build_assignment_submissions_query(sort_by='default')
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_recent_activity_query_basic(self):
        """Test basic recent activity query construction."""
        query = self.query_builder.build_recent_activity_query()
        
        # Verify it returns a CompoundSelect query (UNION operation)
        assert isinstance(query, (Select, CompoundSelect))
        
        # Query should be limited by default
        assert query._limit == 100
    
    @pytest.mark.unit
    def test_build_recent_activity_query_with_filters(self):
        """Test recent activity query with various filters."""
        # Test with specific hours
        query = self.query_builder.build_recent_activity_query(hours=48)
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with activity type filter
        query = self.query_builder.build_recent_activity_query(activity_types=['grade'])
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with user filter
        query = self.query_builder.build_recent_activity_query(user_id=123)
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with course filter
        query = self.query_builder.build_recent_activity_query(course_id=456)
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with custom limit
        query = self.query_builder.build_recent_activity_query(limit=50)
        assert isinstance(query, (Select, CompoundSelect))
        assert query._limit == 50
    
    @pytest.mark.unit
    def test_build_performance_summary_query_basic(self):
        """Test basic performance summary query construction."""
        query = self.query_builder.build_performance_summary_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes required columns
        column_labels = [col.name for col in query.selected_columns]
        expected_columns = [
            'student_id', 'student_name', 'current_score', 'final_score',
            'course_id', 'course_name', 'total_assignments', 'completed_assignments',
            'average_score', 'lowest_score', 'highest_score',
            'late_submissions', 'missing_assignments'
        ]
        
        for expected_col in expected_columns:
            assert expected_col in column_labels
    
    @pytest.mark.unit
    def test_build_performance_summary_query_with_filters(self):
        """Test performance summary query with filters."""
        # Test with course ID filter
        query = self.query_builder.build_performance_summary_query(course_id=123)
        assert isinstance(query, Select)
        
        # Test with student ID filter
        query = self.query_builder.build_performance_summary_query(student_id=456)
        assert isinstance(query, Select)
        
        # Test with date range filter
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        query = self.query_builder.build_performance_summary_query(
            date_range=(start_date, end_date)
        )
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_query_builder_parameter_validation(self):
        """Test parameter validation in query builder methods."""
        # Test that None values are handled correctly
        query = self.query_builder.build_student_grades_query(
            student_id=None,
            course_id=None,
            assignment_ids=None
        )
        assert isinstance(query, Select)
        
        # Test that empty lists are handled correctly
        query = self.query_builder.build_student_grades_query(assignment_ids=[])
        assert isinstance(query, Select)
        
        # Test that boolean parameters work correctly
        query = self.query_builder.build_student_grades_query(
            include_metadata=False,
            include_history=False
        )
        assert isinstance(query, Select)


class TestQueryUtilities:
    """Test suite for query utility functions."""
    
    @pytest.mark.unit
    def test_optimize_query_performance(self):
        """Test query performance optimization utility."""
        # Create a basic query
        base_query = select(CanvasStudent.student_id, CanvasStudent.name)
        
        # Apply optimization
        optimized_query = optimize_query_performance(base_query)
        
        # Verify it's still a Select query
        assert isinstance(optimized_query, Select)
        
        # Verify execution options are set
        assert optimized_query._execution_options is not None
        assert optimized_query._execution_options.get('autoflush') == False
    
    @pytest.mark.unit
    def test_add_pagination(self):
        """Test pagination utility function."""
        # Create a basic query
        base_query = select(CanvasStudent.student_id, CanvasStudent.name)
        
        # Test default pagination (page 1, 50 per page)
        paginated_query = add_pagination(base_query)
        assert isinstance(paginated_query, Select)
        assert paginated_query._offset == 0
        assert paginated_query._limit == 50
        
        # Test custom pagination (page 2, 25 per page)
        paginated_query = add_pagination(base_query, page=2, per_page=25)
        assert paginated_query._offset == 25
        assert paginated_query._limit == 25
        
        # Test page 3 with 10 per page
        paginated_query = add_pagination(base_query, page=3, per_page=10)
        assert paginated_query._offset == 20
        assert paginated_query._limit == 10
    
    @pytest.mark.unit
    def test_add_active_filter(self):
        """Test active filter utility function."""
        from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
        
        # Create a basic query
        base_query = select(ObjectStatus.object_id, EnrollmentStatus.student_id)
        
        # Test with Layer 0 lifecycle models that have active field
        model_classes = [ObjectStatus, EnrollmentStatus]
        filtered_query = add_active_filter(base_query, model_classes)
        
        # Verify it's still a Select query
        assert isinstance(filtered_query, Select)
        
        # Test with empty model list
        filtered_query = add_active_filter(base_query, [])
        assert isinstance(filtered_query, Select)
        
        # Test with Canvas models (should not add filters since they don't have active field)
        model_classes = [CanvasStudent, CanvasCourse, CanvasAssignment]
        filtered_query = add_active_filter(base_query, model_classes)
        assert isinstance(filtered_query, Select)
        
        # Test with models that don't have active field (should not crash)
        class MockModel:
            pass
        
        filtered_query = add_active_filter(base_query, [MockModel])
        assert isinstance(filtered_query, Select)


class TestQueryBuilderIntegration:
    """Integration tests for QueryBuilder functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.integration
    def test_complex_student_grades_query(self):
        """Test complex student grades query with all options."""
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)
        
        query = self.query_builder.build_student_grades_query(
            student_id=123,
            course_id=456,
            assignment_ids=[1, 2, 3],
            include_metadata=True,
            include_history=True,
            date_range=(start_date, end_date)
        )
        
        assert isinstance(query, Select)
        
        # Check that all requested columns are present
        column_labels = [col.name for col in query.selected_columns]
        
        # Basic columns
        basic_columns = ['student_id', 'student_name', 'course_id', 'assignment_id']
        for col in basic_columns:
            assert col in column_labels
        
        # Metadata columns
        metadata_columns = ['student_notes', 'assignment_notes']
        for col in metadata_columns:
            assert col in column_labels
            
        # History columns
        history_columns = ['previous_score', 'grade_change']
        for col in history_columns:
            assert col in column_labels
    
    @pytest.mark.integration
    def test_performance_optimized_query_chain(self):
        """Test chaining query builder with performance utilities."""
        # Build base query
        base_query = self.query_builder.build_course_enrollment_query(
            include_grades=True,
            include_metadata=True
        )
        
        # Apply performance optimization
        optimized_query = optimize_query_performance(base_query)
        
        # Add pagination
        final_query = add_pagination(optimized_query, page=2, per_page=20)
        
        # Verify final query structure
        assert isinstance(final_query, Select)
        assert final_query._offset == 20
        assert final_query._limit == 20
        assert final_query._execution_options is not None
    
    @pytest.mark.integration  
    def test_recent_activity_with_multiple_types(self):
        """Test recent activity query with multiple activity types."""
        query = self.query_builder.build_recent_activity_query(
            hours=72,
            activity_types=['grade', 'note'],
            limit=200
        )
        
        assert isinstance(query, (Select, CompoundSelect))
        assert query._limit == 200
    
    @pytest.mark.integration
    def test_assignment_submissions_with_all_features(self):
        """Test assignment submissions query with all features enabled."""
        query = self.query_builder.build_assignment_submissions_query(
            assignment_id=123,
            course_id=456,
            submission_status='submitted',
            include_late_submissions=True,
            include_grade_history=True,
            sort_by='score'
        )
        
        assert isinstance(query, Select)
        
        # Verify all feature columns are present
        column_labels = [col.name for col in query.selected_columns]
        
        # Late submission columns
        assert 'is_late' in column_labels
        assert 'hours_late' in column_labels
        
        # Grade history columns
        assert 'previous_score' in column_labels
        assert 'grade_change' in column_labels
    
    @pytest.mark.integration
    def test_error_handling_and_edge_cases(self):
        """Test error handling and edge case scenarios."""
        # Test with invalid sort_by parameter (should use default)
        query = self.query_builder.build_assignment_submissions_query(
            sort_by='invalid_sort_option'
        )
        assert isinstance(query, Select)
        
        # Test with empty activity types list
        query = self.query_builder.build_recent_activity_query(
            activity_types=[]
        )
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with zero hours (should work but return no recent data)
        query = self.query_builder.build_recent_activity_query(hours=0)
        assert isinstance(query, (Select, CompoundSelect))
        
        # Test with negative values (should be handled gracefully)
        query = self.query_builder.build_recent_activity_query(
            hours=-24,  # Should be handled gracefully
            limit=0     # Should be handled gracefully
        )
        assert isinstance(query, (Select, CompoundSelect))


class TestQueryBuilderPerformance:
    """Performance-focused tests for QueryBuilder."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.performance
    def test_query_construction_efficiency(self):
        """Test that query construction is efficient."""
        import time
        
        # Time basic query construction
        start_time = time.time()
        
        for _ in range(100):
            query = self.query_builder.build_student_grades_query()
        
        basic_time = time.time() - start_time
        
        # Time complex query construction
        start_time = time.time()
        
        for _ in range(100):
            query = self.query_builder.build_student_grades_query(
                student_id=123,
                include_metadata=True,
                include_history=True,
                date_range=(datetime.now(), datetime.now())
            )
        
        complex_time = time.time() - start_time
        
        # Basic performance checks (should be very fast)
        assert basic_time < 1.0  # Less than 1 second for 100 basic queries
        assert complex_time < 2.0  # Less than 2 seconds for 100 complex queries
    
    @pytest.mark.performance
    def test_query_optimization_utilities(self):
        """Test performance optimization utilities."""
        base_query = self.query_builder.build_performance_summary_query()
        
        # Test that optimization doesn't break the query
        optimized_query = optimize_query_performance(base_query)
        assert isinstance(optimized_query, Select)
        
        # Test that pagination doesn't break the query
        paginated_query = add_pagination(optimized_query)
        assert isinstance(paginated_query, Select)


# Test fixtures and helpers
@pytest.fixture
def sample_date_range():
    """Provide sample date range for testing."""
    start = datetime(2024, 1, 1)
    end = datetime(2024, 12, 31)
    return (start, end)


@pytest.fixture
def sample_student_ids():
    """Provide sample student IDs for testing."""
    return [123, 456, 789]


@pytest.fixture
def sample_assignment_ids():
    """Provide sample assignment IDs for testing."""
    return [1, 2, 3, 4, 5]


class TestQueryBuilderLayer0Unit:
    """Unit tests for Layer 0 lifecycle integration methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.unit
    def test_build_active_objects_query_parameter_validation(self):
        """Test parameter validation for build_active_objects_query."""
        # Test valid object types
        valid_types = ['student', 'course', 'assignment']
        for obj_type in valid_types:
            query = self.query_builder.build_active_objects_query(obj_type)
            assert isinstance(query, Select)
        
        # Test invalid object type raises ValueError
        invalid_types = ['invalid', 'teacher', 'module', '', None]
        for invalid_type in invalid_types:
            with pytest.raises((ValueError, TypeError)):
                self.query_builder.build_active_objects_query(invalid_type)
    
    @pytest.mark.unit
    def test_build_active_objects_query_boolean_parameters(self):
        """Test boolean parameter combinations for build_active_objects_query."""
        # Test all boolean combinations
        boolean_combinations = [
            (False, False),  # Default: active only
            (True, False),   # Include inactive
            (False, True),   # Include pending deletion
            (True, True)     # Include all
        ]
        
        for include_inactive, include_pending in boolean_combinations:
            query = self.query_builder.build_active_objects_query(
                'student',
                include_inactive=include_inactive,
                include_pending_deletion=include_pending
            )
            assert isinstance(query, Select)
            # Verify query construction doesn't fail
    
    @pytest.mark.unit
    def test_build_active_objects_query_model_mapping(self):
        """Test that object types map to correct Canvas models."""
        # Test student mapping
        query = self.query_builder.build_active_objects_query('student')
        column_names = [col.name for col in query.selected_columns]
        # Should include student-specific columns when they're selected
        assert isinstance(query, Select)
        
        # Test course mapping
        query = self.query_builder.build_active_objects_query('course')
        assert isinstance(query, Select)
        
        # Test assignment mapping
        query = self.query_builder.build_active_objects_query('assignment')
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_active_enrollments_query_parameter_validation(self):
        """Test parameter validation for build_active_enrollments_query."""
        # Test with no parameters (should work)
        query = self.query_builder.build_active_enrollments_query()
        assert isinstance(query, Select)
        
        # Test with student_id parameter
        query = self.query_builder.build_active_enrollments_query(student_id=123)
        assert isinstance(query, Select)
        
        # Test with course_id parameter
        query = self.query_builder.build_active_enrollments_query(course_id=456)
        assert isinstance(query, Select)
        
        # Test with both parameters
        query = self.query_builder.build_active_enrollments_query(
            student_id=123, course_id=456
        )
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_active_enrollments_query_boolean_parameters(self):
        """Test boolean parameter handling for build_active_enrollments_query."""
        boolean_combinations = [
            (False, False),
            (True, False), 
            (False, True),
            (True, True)
        ]
        
        for include_inactive, include_pending in boolean_combinations:
            query = self.query_builder.build_active_enrollments_query(
                include_inactive=include_inactive,
                include_pending_deletion=include_pending
            )
            assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_active_enrollments_query_column_selection(self):
        """Test that build_active_enrollments_query selects expected columns."""
        query = self.query_builder.build_active_enrollments_query()
        
        column_names = [col.name for col in query.selected_columns]
        
        # Check for expected Canvas data columns
        expected_canvas_columns = [
            'student_id', 'course_id', 'enrollment_date', 
            'student_name', 'course_name', 'course_code'
        ]
        
        for col in expected_canvas_columns:
            assert col in column_names
        
        # Check for expected lifecycle columns
        expected_lifecycle_columns = [
            'lifecycle_active', 'lifecycle_pending_deletion', 
            'lifecycle_removed_date', 'lifecycle_last_seen'
        ]
        
        for col in expected_lifecycle_columns:
            assert col in column_names
    
    @pytest.mark.unit
    def test_build_pending_deletion_review_query_parameter_validation(self):
        """Test parameter validation for build_pending_deletion_review_query."""
        # Test with no object_type filter (should work)
        query = self.query_builder.build_pending_deletion_review_query()
        assert isinstance(query, Select)
        
        # Test with valid object types
        valid_types = ['student', 'course', 'assignment']
        for obj_type in valid_types:
            query = self.query_builder.build_pending_deletion_review_query(obj_type)
            assert isinstance(query, Select)
        
        # Test with None (should work - means no filter)
        query = self.query_builder.build_pending_deletion_review_query(None)
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_build_pending_deletion_review_query_column_selection(self):
        """Test that build_pending_deletion_review_query selects expected columns."""
        query = self.query_builder.build_pending_deletion_review_query()
        
        column_names = [col.name for col in query.selected_columns]
        
        # Check for expected ObjectStatus columns
        expected_columns = [
            'object_type', 'object_id', 'removed_date', 'removal_reason',
            'user_data_exists', 'historical_data_exists', 'last_seen_sync'
        ]
        
        for col in expected_columns:
            assert col in column_names
    
    @pytest.mark.unit
    def test_build_active_objects_query_edge_cases(self):
        """Test edge cases for build_active_objects_query."""
        # Test case sensitivity (should be case sensitive)
        with pytest.raises(ValueError):
            self.query_builder.build_active_objects_query('Student')  # Capital S
        
        with pytest.raises(ValueError):
            self.query_builder.build_active_objects_query('STUDENT')  # All caps
        
        # Test empty string
        with pytest.raises(ValueError):
            self.query_builder.build_active_objects_query('')
        
        # Test whitespace
        with pytest.raises(ValueError):
            self.query_builder.build_active_objects_query(' student ')  # Extra spaces
    
    @pytest.mark.unit
    def test_build_active_enrollments_query_edge_cases(self):
        """Test edge cases for build_active_enrollments_query."""
        # Test with zero IDs (should work)
        query = self.query_builder.build_active_enrollments_query(student_id=0)
        assert isinstance(query, Select)
        
        query = self.query_builder.build_active_enrollments_query(course_id=0) 
        assert isinstance(query, Select)
        
        # Test with negative IDs (should work - could be valid in some systems)
        query = self.query_builder.build_active_enrollments_query(student_id=-1)
        assert isinstance(query, Select)
        
        query = self.query_builder.build_active_enrollments_query(course_id=-1)
        assert isinstance(query, Select)
    
    @pytest.mark.unit
    def test_add_active_filter_unit_layer0_only(self):
        """Unit test for updated add_active_filter function."""
        from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
        from database.models.layer1_canvas import CanvasStudent, CanvasCourse, CanvasAssignment
        
        # Create base query
        base_query = select(CanvasStudent.student_id)
        
        # Test with Layer 1 models only (should not add any conditions)
        layer1_models = [CanvasStudent, CanvasCourse, CanvasAssignment]
        filtered_query = add_active_filter(base_query, layer1_models)
        
        # Query should be unchanged (no WHERE conditions added)
        assert isinstance(filtered_query, Select)
        
        # Test with Layer 0 models only (should add conditions)
        layer0_models = [ObjectStatus, EnrollmentStatus]
        filtered_query = add_active_filter(base_query, layer0_models) 
        
        assert isinstance(filtered_query, Select)
        
        # Test with mixed models (only Layer 0 should be filtered)
        mixed_models = [CanvasStudent, ObjectStatus, CanvasCourse, EnrollmentStatus]
        filtered_query = add_active_filter(base_query, mixed_models)
        
        assert isinstance(filtered_query, Select)
        
        # Test with empty list (should not add conditions)
        filtered_query = add_active_filter(base_query, [])
        assert isinstance(filtered_query, Select)
        
        # Test with non-model classes (should not crash)
        non_models = [str, int, dict]
        filtered_query = add_active_filter(base_query, non_models)
        assert isinstance(filtered_query, Select)


class TestQueryBuilderLayer0Integration:
    """Test Layer 0 lifecycle integration methods."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.integration
    def test_build_active_objects_query_student(self):
        """Test active objects query for students."""
        query = self.query_builder.build_active_objects_query('student')
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes lifecycle columns
        column_labels = [col.name for col in query.selected_columns]
        lifecycle_columns = ['lifecycle_active', 'lifecycle_pending_deletion', 'lifecycle_removed_date']
        
        for lifecycle_col in lifecycle_columns:
            assert lifecycle_col in column_labels
    
    @pytest.mark.integration
    def test_build_active_objects_query_course(self):
        """Test active objects query for courses."""
        query = self.query_builder.build_active_objects_query('course')
        assert isinstance(query, Select)
        
        # Test with include options
        query_with_inactive = self.query_builder.build_active_objects_query(
            'course', include_inactive=True
        )
        assert isinstance(query_with_inactive, Select)
    
    @pytest.mark.integration
    def test_build_active_objects_query_assignment(self):
        """Test active objects query for assignments."""
        query = self.query_builder.build_active_objects_query('assignment')
        assert isinstance(query, Select)
        
        # Test with pending deletion inclusion
        query_with_pending = self.query_builder.build_active_objects_query(
            'assignment', include_pending_deletion=True
        )
        assert isinstance(query_with_pending, Select)
    
    @pytest.mark.integration
    def test_build_active_objects_query_invalid_type(self):
        """Test active objects query with invalid object type."""
        with pytest.raises(ValueError) as exc_info:
            self.query_builder.build_active_objects_query('invalid_type')
        
        assert "Unsupported object_type" in str(exc_info.value)
        assert "invalid_type" in str(exc_info.value)
    
    @pytest.mark.integration
    def test_build_active_enrollments_query_basic(self):
        """Test basic active enrollments query."""
        query = self.query_builder.build_active_enrollments_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes lifecycle columns
        column_labels = [col.name for col in query.selected_columns]
        lifecycle_columns = ['lifecycle_active', 'lifecycle_pending_deletion']
        canvas_columns = ['student_name', 'course_name', 'course_code']
        
        for col in lifecycle_columns + canvas_columns:
            assert col in column_labels
    
    @pytest.mark.integration
    def test_build_active_enrollments_query_with_filters(self):
        """Test active enrollments query with filters."""
        # Test with student filter
        query = self.query_builder.build_active_enrollments_query(student_id=123)
        assert isinstance(query, Select)
        
        # Test with course filter
        query = self.query_builder.build_active_enrollments_query(course_id=456)
        assert isinstance(query, Select)
        
        # Test with both filters and inclusion options
        query = self.query_builder.build_active_enrollments_query(
            student_id=123, 
            course_id=456,
            include_inactive=True,
            include_pending_deletion=True
        )
        assert isinstance(query, Select)
    
    @pytest.mark.integration
    def test_build_pending_deletion_review_query_basic(self):
        """Test basic pending deletion review query."""
        query = self.query_builder.build_pending_deletion_review_query()
        
        # Verify it returns a Select query
        assert isinstance(query, Select)
        
        # Check that the query includes expected columns
        column_labels = [col.name for col in query.selected_columns]
        expected_columns = [
            'object_type', 'object_id', 'removed_date', 'removal_reason',
            'user_data_exists', 'historical_data_exists', 'last_seen_sync'
        ]
        
        for expected_col in expected_columns:
            assert expected_col in column_labels
    
    @pytest.mark.integration
    def test_build_pending_deletion_review_query_with_filter(self):
        """Test pending deletion review query with object type filter."""
        query = self.query_builder.build_pending_deletion_review_query('student')
        assert isinstance(query, Select)
        
        # Test other object types
        for obj_type in ['course', 'assignment']:
            query = self.query_builder.build_pending_deletion_review_query(obj_type)
            assert isinstance(query, Select)
    
    @pytest.mark.integration
    def test_layer0_integration_query_construction_efficiency(self):
        """Test that Layer 0 integration queries construct efficiently."""
        import time
        
        # Time Layer 0 query construction
        start_time = time.time()
        
        for _ in range(50):
            query = self.query_builder.build_active_objects_query('student')
            query = self.query_builder.build_active_enrollments_query()
            query = self.query_builder.build_pending_deletion_review_query()
        
        construction_time = time.time() - start_time
        
        # Should be very fast (less than 1 second for 50 iterations of 3 queries each)
        assert construction_time < 1.0


class TestQueryBuilderRealDatabaseIntegration:
    """
    PHASE 1 CRITICAL: Integration tests with real database execution.
    
    These tests address the critical gap identified in our analysis:
    validating query execution against real models, not just structure.
    """
    
    @pytest.mark.integration
    def test_student_grades_query_database_execution(self, db_session):
        """Test student grades query actually executes against real database."""
        query_builder = QueryBuilder(db_session)
        
        # Build and execute basic student grades query
        query = query_builder.build_student_grades_query()
        
        # Critical test: Execute query against real database
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            # Should execute without error (may return empty results)
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Query execution failed: {e}")
    
    @pytest.mark.integration
    def test_course_enrollment_query_database_execution(self, db_session):
        """Test course enrollment query actually executes against real database."""
        query_builder = QueryBuilder(db_session)
        
        # Build and execute course enrollment query
        query = query_builder.build_course_enrollment_query()
        
        # Critical test: Execute query against real database
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Course enrollment query execution failed: {e}")
    
    @pytest.mark.integration
    def test_assignment_submissions_query_database_execution(self, db_session):
        """Test assignment submissions query actually executes against real database."""
        query_builder = QueryBuilder(db_session)
        
        # Build and execute assignment submissions query
        query = query_builder.build_assignment_submissions_query()
        
        # Critical test: Execute query against real database
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Assignment submissions query execution failed: {e}")
    
    @pytest.mark.integration
    def test_recent_activity_query_database_execution(self, db_session):
        """Test recent activity query actually executes against real database."""
        query_builder = QueryBuilder(db_session)
        
        # Build and execute recent activity query
        query = query_builder.build_recent_activity_query()
        
        # Critical test: Execute query against real database
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Recent activity query execution failed: {e}")
    
    @pytest.mark.integration
    def test_layer0_lifecycle_queries_database_execution(self, db_session):
        """Test Layer 0 lifecycle integration queries execute against real database."""
        query_builder = QueryBuilder(db_session)
        
        # Test all Layer 0 object types
        object_types = ['student', 'course', 'assignment']
        
        for obj_type in object_types:
            query = query_builder.build_active_objects_query(obj_type)
            
            # Critical test: Execute query against real database
            try:
                result = db_session.execute(query)
                rows = result.fetchall()
                assert isinstance(rows, list)
            except SQLAlchemyError as e:
                pytest.fail(f"Layer 0 {obj_type} query execution failed: {e}")
        
        # Test enrollment status query
        query = query_builder.build_active_enrollments_query()
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Layer 0 enrollment query execution failed: {e}")
        
        # Test pending deletion review query
        query = query_builder.build_pending_deletion_review_query()
        try:
            result = db_session.execute(query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Layer 0 pending deletion query execution failed: {e}")
    
    @pytest.mark.integration
    def test_sql_compilation_validation(self, db_session):
        """Test that all queries compile to valid SQL without execution errors."""
        query_builder = QueryBuilder(db_session)
        
        # List of all query methods to test
        test_cases = [
            # Basic queries
            lambda: query_builder.build_student_grades_query(),
            lambda: query_builder.build_course_enrollment_query(),
            lambda: query_builder.build_assignment_submissions_query(),
            lambda: query_builder.build_recent_activity_query(),
            lambda: query_builder.build_performance_summary_query(),
            
            # Layer 0 queries
            lambda: query_builder.build_active_objects_query('student'),
            lambda: query_builder.build_active_objects_query('course'),
            lambda: query_builder.build_active_objects_query('assignment'),
            lambda: query_builder.build_active_enrollments_query(),
            lambda: query_builder.build_pending_deletion_review_query(),
            
            # Queries with parameters
            lambda: query_builder.build_student_grades_query(student_id=123),
            lambda: query_builder.build_course_enrollment_query(include_grades=True),
            lambda: query_builder.build_assignment_submissions_query(include_late_submissions=True),
        ]
        
        # Test SQL compilation for all queries
        for i, test_case in enumerate(test_cases):
            try:
                query = test_case()
                # Attempt to compile query to SQL
                compiled = query.compile(compile_kwargs={"literal_binds": True})
                sql_text = str(compiled)
                
                # Basic validation that we got SQL
                assert "SELECT" in sql_text.upper()
                assert len(sql_text) > 10  # Should be substantial SQL
                
            except Exception as e:
                pytest.fail(f"Query compilation failed for test case {i}: {e}")
    
    @pytest.mark.integration
    def test_query_execution_with_filters(self, db_session):
        """Test filtered queries execute without errors."""
        query_builder = QueryBuilder(db_session)
        
        # Test student grades with various filters
        test_filters = [
            {'student_id': 123},
            {'course_id': 456}, 
            {'assignment_ids': [1, 2, 3]},
            {'include_metadata': True},
            {'include_history': True},
            {'student_id': 123, 'course_id': 456, 'include_metadata': True}
        ]
        
        for filters in test_filters:
            query = query_builder.build_student_grades_query(**filters)
            
            try:
                result = db_session.execute(query)
                rows = result.fetchall()
                assert isinstance(rows, list)
            except SQLAlchemyError as e:
                pytest.fail(f"Filtered query execution failed with filters {filters}: {e}")
    
    @pytest.mark.integration
    def test_utility_functions_with_real_queries(self, db_session):
        """Test utility functions work with real queries and database."""
        query_builder = QueryBuilder(db_session)
        
        # Test optimize_query_performance
        base_query = query_builder.build_student_grades_query()
        optimized_query = optimize_query_performance(base_query)
        
        try:
            result = db_session.execute(optimized_query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Optimized query execution failed: {e}")
        
        # Test add_pagination
        paginated_query = add_pagination(base_query, page=1, per_page=10)
        
        try:
            result = db_session.execute(paginated_query)
            rows = result.fetchall()
            assert isinstance(rows, list)
            # Should respect pagination limit
            assert len(rows) <= 10
        except SQLAlchemyError as e:
            pytest.fail(f"Paginated query execution failed: {e}")
        
        # Test add_active_filter
        from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
        filtered_query = add_active_filter(base_query, [ObjectStatus, EnrollmentStatus])
        
        try:
            result = db_session.execute(filtered_query)
            rows = result.fetchall()
            assert isinstance(rows, list)
        except SQLAlchemyError as e:
            pytest.fail(f"Active filter query execution failed: {e}")


class TestQueryBuilderRuntimeValidation:
    """Test runtime validation and error handling."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_session = Mock(spec=Session)
        self.query_builder = QueryBuilder(self.mock_session)
    
    @pytest.mark.integration
    def test_add_active_filter_with_layer0_models(self):
        """Test that add_active_filter works correctly with Layer 0 models."""
        from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
        from database.models.layer1_canvas import CanvasStudent, CanvasCourse
        
        # Create base query
        base_query = select(CanvasStudent.student_id, CanvasStudent.name)
        
        # Test with Layer 1 models (should not add filters)
        filtered_query = add_active_filter(base_query, [CanvasStudent, CanvasCourse])
        assert isinstance(filtered_query, Select)
        # Query should be unchanged since Layer 1 models don't have 'active' fields
        
        # Test with Layer 0 models (should add filters)
        filtered_query = add_active_filter(base_query, [ObjectStatus, EnrollmentStatus])
        assert isinstance(filtered_query, Select)
        
        # Test with mixed models
        filtered_query = add_active_filter(base_query, [CanvasStudent, ObjectStatus])
        assert isinstance(filtered_query, Select)
    
    @pytest.mark.integration
    def test_query_parameter_validation(self):
        """Test parameter validation in Layer 0 integration methods."""
        # Test valid object types
        valid_types = ['student', 'course', 'assignment']
        for obj_type in valid_types:
            query = self.query_builder.build_active_objects_query(obj_type)
            assert isinstance(query, Select)
        
        # Test invalid object type
        with pytest.raises(ValueError):
            self.query_builder.build_active_objects_query('invalid')
    
    @pytest.mark.integration
    def test_query_complex_parameter_combinations(self):
        """Test complex parameter combinations don't break query construction."""
        # Test all combinations of boolean flags for active objects query
        boolean_combinations = [
            (True, True), (True, False), (False, True), (False, False)
        ]
        
        for include_inactive, include_pending in boolean_combinations:
            query = self.query_builder.build_active_objects_query(
                'student',
                include_inactive=include_inactive,
                include_pending_deletion=include_pending
            )
            assert isinstance(query, Select)
        
        # Test enrollments with all parameter combinations
        for include_inactive, include_pending in boolean_combinations:
            query = self.query_builder.build_active_enrollments_query(
                include_inactive=include_inactive,
                include_pending_deletion=include_pending,
                student_id=123,
                course_id=456
            )
            assert isinstance(query, Select)


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
