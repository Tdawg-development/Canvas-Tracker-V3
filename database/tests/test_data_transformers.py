"""
Unit Tests for Canvas Data Transformers.

Tests the data transformation utilities that convert between TypeScript Canvas
staging data formats and Python database model formats. These tests validate:

- Canvas staging data structure validation
- TypeScript to Python data format conversion
- DateTime parsing and timezone handling
- Data normalization and validation
- Error handling and edge cases
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from database.operations.data_transformers import (
    CanvasDataTransformer, 
    TransformationResult,
    transform_canvas_data,
    validate_canvas_data_structure,
    get_transformation_preview
)
from database.operations.base.exceptions import ValidationError, DataValidationError


class TestCanvasDataTransformer:
    """Test CanvasDataTransformer core functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.transformer = CanvasDataTransformer()
    
    @pytest.mark.unit
    def test_transformer_initialization(self):
        """Test CanvasDataTransformer initialization."""
        assert isinstance(self.transformer, CanvasDataTransformer)
        assert hasattr(self.transformer, 'logger')
    
    # ==================== CANVAS DATA VALIDATION TESTS ====================
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_valid(self):
        """Test validation of valid Canvas data structure."""
        valid_data = {
            'success': True,
            'course_id': 123,
            'course': {'id': 123, 'name': 'Test Course'},
            'students': [],
            'modules': []
        }
        
        # Should not raise any exception
        self.transformer._validate_canvas_data_structure(valid_data)
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_not_dict(self):
        """Test validation fails for non-dictionary input."""
        with pytest.raises(ValidationError) as exc_info:
            self.transformer._validate_canvas_data_structure("not a dict")
        
        assert "must be a dictionary" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_failure_flag(self):
        """Test validation fails when success=False."""
        failed_data = {
            'success': False,
            'error': {'message': 'Canvas API failed'},
            'course': {'id': 123}
        }
        
        with pytest.raises(ValidationError) as exc_info:
            self.transformer._validate_canvas_data_structure(failed_data)
        
        assert "Canvas data indicates failure" in str(exc_info.value)
        assert "Canvas API failed" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_missing_fields(self):
        """Test validation fails for missing required fields."""
        incomplete_data = {
            'success': True,
            'course': {'id': 123}
            # Missing 'students' and 'modules'
        }
        
        with pytest.raises(ValidationError) as exc_info:
            self.transformer._validate_canvas_data_structure(incomplete_data)
        
        assert "missing required fields" in str(exc_info.value)
        assert "students" in str(exc_info.value)
        assert "modules" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_missing_course_id(self):
        """Test validation fails when course is missing ID."""
        invalid_data = {
            'success': True,
            'course': {'name': 'Test Course'},  # Missing 'id'
            'students': [],
            'modules': []
        }
        
        with pytest.raises(ValidationError) as exc_info:
            self.transformer._validate_canvas_data_structure(invalid_data)
        
        assert "Course data missing required 'id' field" in str(exc_info.value)
    
    # ==================== DATETIME PARSING TESTS ====================
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_valid_z_format(self):
        """Test parsing Canvas datetime with Z suffix."""
        date_string = "2024-03-15T14:30:00Z"
        result = self.transformer._parse_canvas_datetime(date_string)
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.year == 2024
        assert result.month == 3
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_with_timezone(self):
        """Test parsing Canvas datetime with explicit timezone."""
        date_string = "2024-03-15T14:30:00+05:00"
        result = self.transformer._parse_canvas_datetime(date_string)
        
        assert isinstance(result, datetime)
        # Should be converted to UTC
        assert result.tzinfo == timezone.utc
        # Should be adjusted for timezone difference
        assert result.hour == 9  # 14 - 5 = 9 UTC
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_no_timezone(self):
        """Test parsing Canvas datetime without timezone (assumes UTC)."""
        date_string = "2024-03-15T14:30:00"
        result = self.transformer._parse_canvas_datetime(date_string)
        
        assert isinstance(result, datetime)
        assert result.tzinfo == timezone.utc
        assert result.hour == 14
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_none_input(self):
        """Test parsing None datetime input."""
        result = self.transformer._parse_canvas_datetime(None)
        assert result is None
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_empty_string(self):
        """Test parsing empty string datetime input."""
        result = self.transformer._parse_canvas_datetime("")
        assert result is None
    
    @pytest.mark.unit
    def test_parse_canvas_datetime_invalid_format(self):
        """Test parsing invalid datetime format."""
        with patch.object(self.transformer.logger, 'warning') as mock_warn:
            result = self.transformer._parse_canvas_datetime("invalid-date")
            
            assert result is None
            mock_warn.assert_called_once()
            assert "Failed to parse Canvas datetime" in mock_warn.call_args[0][0]
    
    # ==================== DATA NORMALIZATION TESTS ====================
    
    @pytest.mark.unit
    def test_normalize_score_valid_float(self):
        """Test score normalization with valid float."""
        assert self.transformer._normalize_score(85.7) == 86
        assert self.transformer._normalize_score(92.3) == 92
        assert self.transformer._normalize_score(100.0) == 100
    
    @pytest.mark.unit
    def test_normalize_score_valid_int(self):
        """Test score normalization with valid integer."""
        assert self.transformer._normalize_score(85) == 85
        assert self.transformer._normalize_score(0) == 0
        assert self.transformer._normalize_score(100) == 100
    
    @pytest.mark.unit
    def test_normalize_score_string_number(self):
        """Test score normalization with string number."""
        assert self.transformer._normalize_score("85.5") == 86
        assert self.transformer._normalize_score("92") == 92
    
    @pytest.mark.unit
    def test_normalize_score_none(self):
        """Test score normalization with None."""
        assert self.transformer._normalize_score(None) == 0
    
    @pytest.mark.unit
    def test_normalize_score_invalid(self):
        """Test score normalization with invalid input."""
        with patch.object(self.transformer.logger, 'warning') as mock_warn:
            result = self.transformer._normalize_score("invalid")
            
            assert result == 0
            mock_warn.assert_called_once()
    
    @pytest.mark.unit
    def test_normalize_assignment_type_standard_types(self):
        """Test assignment type normalization for standard types."""
        assert self.transformer._normalize_assignment_type("assignment") == "Assignment"
        assert self.transformer._normalize_assignment_type("quiz") == "Quiz"
        assert self.transformer._normalize_assignment_type("discussion") == "Discussion"
        assert self.transformer._normalize_assignment_type("external_tool") == "ExternalTool"
    
    @pytest.mark.unit
    def test_normalize_assignment_type_case_insensitive(self):
        """Test assignment type normalization is case insensitive."""
        assert self.transformer._normalize_assignment_type("ASSIGNMENT") == "Assignment"
        assert self.transformer._normalize_assignment_type("Quiz") == "Quiz"
        assert self.transformer._normalize_assignment_type("QUIZ") == "Quiz"
    
    @pytest.mark.unit
    def test_normalize_assignment_type_unknown(self):
        """Test assignment type normalization with unknown type."""
        assert self.transformer._normalize_assignment_type("unknown_type") == "unknown_type"
    
    @pytest.mark.unit
    def test_normalize_assignment_type_none(self):
        """Test assignment type normalization with None."""
        assert self.transformer._normalize_assignment_type(None) == "Assignment"
    
    @pytest.mark.unit
    def test_extract_calendar_ics_valid(self):
        """Test calendar ICS extraction from valid course data."""
        course_data = {
            'calendar': {
                'ics': 'https://example.com/calendar.ics'
            }
        }
        
        result = self.transformer._extract_calendar_ics(course_data)
        assert result == 'https://example.com/calendar.ics'
    
    @pytest.mark.unit
    def test_extract_calendar_ics_no_calendar(self):
        """Test calendar ICS extraction when no calendar present."""
        course_data = {'name': 'Test Course'}
        
        result = self.transformer._extract_calendar_ics(course_data)
        assert result == ''
    
    @pytest.mark.unit
    def test_extract_calendar_ics_no_ics(self):
        """Test calendar ICS extraction when calendar has no ICS."""
        course_data = {
            'calendar': {'other_field': 'value'}
        }
        
        result = self.transformer._extract_calendar_ics(course_data)
        assert result == ''
    
    # ==================== COURSE TRANSFORMATION TESTS ====================
    
    @pytest.mark.unit
    def test_transform_course_data_complete(self):
        """Test transformation of complete course data."""
        course_data = {
            'id': 123,
            'name': 'Test Course',
            'course_code': 'TEST101', 
            'workflow_state': 'available',
            'start_at': '2024-01-15T00:00:00Z',
            'end_at': '2024-05-15T00:00:00Z',
            'calendar': {'ics': 'https://example.com/calendar.ics'},
            'metadata': {
                'total_students': 25,
                'total_modules': 8,
                'total_assignments': 42
            }
        }
        
        result = self.transformer.transform_course_data(course_data)
        
        assert len(result) == 1
        course = result[0]
        
        assert course['id'] == 123
        assert course['name'] == 'Test Course'
        assert course['course_code'] == 'TEST101'
        assert course['workflow_state'] == 'available'
        assert course['calendar_ics'] == 'https://example.com/calendar.ics'
        assert isinstance(course['start_at'], datetime)
        assert isinstance(course['end_at'], datetime)
        assert isinstance(course['last_synced'], datetime)
        assert course['total_students'] == 25
        assert course['total_modules'] == 8
        assert course['total_assignments'] == 42
    
    @pytest.mark.unit
    def test_transform_course_data_minimal(self):
        """Test transformation of minimal course data."""
        course_data = {
            'id': 123,
            'name': 'Minimal Course'
        }
        
        result = self.transformer.transform_course_data(course_data)
        
        assert len(result) == 1
        course = result[0]
        
        assert course['id'] == 123
        assert course['name'] == 'Minimal Course'
        assert course['course_code'] == ''
        assert course['calendar_ics'] == ''
        assert course['workflow_state'] == 'available'
        assert course['start_at'] is None
        assert course['end_at'] is None
    
    @pytest.mark.unit
    def test_transform_course_data_empty(self):
        """Test transformation of empty course data."""
        result = self.transformer.transform_course_data({})
        assert result == []
        
        result = self.transformer.transform_course_data(None)
        assert result == []
    
    @pytest.mark.unit
    def test_transform_course_data_error(self):
        """Test transformation error handling."""
        course_data = {
            'id': 123,
            'name': 'Test Course'
        }
        
        # Mock an error during date parsing
        with patch.object(self.transformer, '_parse_canvas_datetime', side_effect=Exception("Test error")):
            # The method should raise ValidationError when errors occur
            with pytest.raises(ValidationError) as exc_info:
                self.transformer.transform_course_data(course_data)
            
            # Verify the error message includes our test error
            assert "Course data transformation failed: Test error" in str(exc_info.value)
            assert exc_info.value.field_name == "course_data"
    
    # ==================== STUDENT TRANSFORMATION TESTS ====================
    
    @pytest.mark.unit
    def test_transform_students_data_complete(self):
        """Test transformation of complete student data."""
        students_data = [
            {
                'id': 456,
                'user_id': 789,
                'created_at': '2024-01-15T10:30:00Z',
                'last_activity_at': '2024-03-01T14:20:00Z',
                'current_score': 85.5,
                'final_score': 90.2,
                'user': {
                    'id': 789,
                    'name': 'John Doe',
                    'login_id': 'john.doe',
                    'sortable_name': 'Doe, John'
                },
                'email': 'john.doe@example.com'
            }
        ]
        
        result = self.transformer.transform_students_data(students_data)
        
        assert len(result) == 1
        student = result[0]
        
        assert student['student_id'] == 456
        assert student['user_id'] == 789
        assert student['name'] == 'John Doe'
        assert student['login_id'] == 'john.doe'
        assert student['email'] == 'john.doe@example.com'
        assert student['current_score'] == 86  # Normalized to int
        assert student['final_score'] == 90
        assert isinstance(student['enrollment_date'], datetime)
        assert isinstance(student['last_activity'], datetime)
        assert isinstance(student['created_at'], datetime)
        assert isinstance(student['updated_at'], datetime)
        assert isinstance(student['last_synced'], datetime)
    
    @pytest.mark.unit
    def test_transform_students_data_flat_structure(self):
        """Test transformation of student data with flat user structure."""
        students_data = [
            {
                'id': 456,
                'user_id': 789,
                'name': 'Jane Smith',
                'login_id': 'jane.smith',
                'current_score': 92,
                'final_score': 95
            }
        ]
        
        result = self.transformer.transform_students_data(students_data)
        
        assert len(result) == 1
        student = result[0]
        
        assert student['student_id'] == 456
        assert student['user_id'] == 789
        assert student['name'] == 'Jane Smith'
        assert student['login_id'] == 'jane.smith'
        assert student['current_score'] == 92
        assert student['final_score'] == 95
    
    @pytest.mark.unit
    def test_transform_students_data_missing_id(self):
        """Test transformation skips students without ID."""
        students_data = [
            {'name': 'No ID Student'},  # Missing ID
            {'id': 456, 'user_id': 789, 'name': 'Valid Student'}
        ]
        
        with patch.object(self.transformer.logger, 'warning') as mock_warn:
            result = self.transformer.transform_students_data(students_data)
        
        # Should skip the first student and keep the second
        assert len(result) == 1
        assert result[0]['student_id'] == 456
        mock_warn.assert_called_once()
    
    @pytest.mark.unit
    def test_transform_students_data_empty(self):
        """Test transformation of empty student data."""
        result = self.transformer.transform_students_data([])
        assert result == []
        
        result = self.transformer.transform_students_data(None)
        assert result == []
    
    @pytest.mark.unit
    def test_transform_students_data_error_recovery(self):
        """Test transformation continues after individual student errors."""
        students_data = [
            {'id': 456, 'name': 'Valid Student'},
            {'id': 789, 'name': 'Problem Student'},
            {'id': 101, 'name': 'Another Valid Student'}
        ]
        
        # Mock error for middle student
        with patch.object(self.transformer, '_normalize_score', side_effect=[0, 0, Exception("Test error"), 0, 0]):
            with patch.object(self.transformer.logger, 'error') as mock_error:
                result = self.transformer.transform_students_data(students_data)
            
            # Should get 2 students (skip the problematic one)
            assert len(result) == 2
            assert result[0]['student_id'] == 456
            assert result[1]['student_id'] == 101
            mock_error.assert_called_once()
    
    # ==================== ASSIGNMENT TRANSFORMATION TESTS ====================
    
    @pytest.mark.unit
    def test_transform_assignments_data_complete(self):
        """Test transformation of complete assignment data."""
        modules_data = [
            {
                'id': 301,
                'assignments': [
                    {
                        'id': 501,
                        'title': 'Assignment 1',
                        'type': 'Assignment',
                        'position': 1,
                        'published': True,
                        'url': 'https://example.com/assignment1',
                        'content_details': {'points_possible': 100},
                        'assignment_type': 'homework'
                    },
                    {
                        'id': 502,
                        'title': 'Quiz 1',
                        'type': 'Quiz',
                        'position': 2,
                        'published': False,
                        'content_details': {'points_possible': 50}
                    }
                ]
            }
        ]
        
        result = self.transformer.transform_assignments_data(modules_data, 123)
        
        assert len(result) == 2
        
        assignment1 = result[0]
        assert assignment1['id'] == 501
        assert assignment1['course_id'] == 123
        assert assignment1['module_id'] == 301
        assert assignment1['name'] == 'Assignment 1'
        assert assignment1['type'] == 'Assignment'
        assert assignment1['module_position'] == 1
        assert assignment1['published'] is True
        assert assignment1['url'] == 'https://example.com/assignment1'
        assert assignment1['points_possible'] == 100
        assert assignment1['assignment_type'] == 'homework'
        
        assignment2 = result[1]
        assert assignment2['id'] == 502
        assert assignment2['name'] == 'Quiz 1'
        assert assignment2['type'] == 'Quiz'
        assert assignment2['published'] is False
        assert assignment2['points_possible'] == 50
    
    @pytest.mark.unit
    def test_transform_assignments_data_no_course_id(self):
        """Test transformation with no course ID."""
        modules_data = [{'id': 301, 'assignments': []}]
        
        result = self.transformer.transform_assignments_data(modules_data, None)
        assert result == []
    
    @pytest.mark.unit
    def test_transform_assignments_data_empty_modules(self):
        """Test transformation with empty modules."""
        result = self.transformer.transform_assignments_data([], 123)
        assert result == []
        
        result = self.transformer.transform_assignments_data(None, 123)
        assert result == []
    
    @pytest.mark.unit
    def test_transform_assignments_data_missing_required_fields(self):
        """Test transformation skips assignments with missing required fields."""
        modules_data = [
            {
                'id': 301,
                'assignments': [
                    {'title': 'No ID Assignment'},  # Missing ID
                    {'id': 502, 'title': 'Valid Assignment'}
                ]
            }
        ]
        
        with patch.object(self.transformer.logger, 'warning') as mock_warn:
            result = self.transformer.transform_assignments_data(modules_data, 123)
        
        assert len(result) == 1
        assert result[0]['id'] == 502
        mock_warn.assert_called_once()
    
    # ==================== ENROLLMENT TRANSFORMATION TESTS ====================
    
    @pytest.mark.unit
    def test_transform_enrollments_data_complete(self):
        """Test transformation of complete enrollment data."""
        students_data = [
            {
                'id': 456,
                'user_id': 789,
                'created_at': '2024-01-15T10:30:00Z',
                'enrollment_state': 'active'
            },
            {
                'id': 457,
                'user_id': 790,
                'created_at': '2024-01-16T09:00:00Z'
            }
        ]
        
        result = self.transformer.transform_enrollments_data(students_data, 123)
        
        assert len(result) == 2
        
        enrollment1 = result[0]
        assert enrollment1['student_id'] == 456
        assert enrollment1['course_id'] == 123
        assert isinstance(enrollment1['enrollment_date'], datetime)
        assert enrollment1['enrollment_status'] == 'active'
        assert isinstance(enrollment1['created_at'], datetime)
        assert isinstance(enrollment1['updated_at'], datetime)
        assert isinstance(enrollment1['last_synced'], datetime)
        
        enrollment2 = result[1]
        assert enrollment2['student_id'] == 457
        assert enrollment2['enrollment_status'] == 'active'  # Default
    
    @pytest.mark.unit
    def test_transform_enrollments_data_no_course_id(self):
        """Test transformation with no course ID."""
        students_data = [{'id': 456}]
        
        result = self.transformer.transform_enrollments_data(students_data, None)
        assert result == []
    
    @pytest.mark.unit
    def test_transform_enrollments_data_missing_student_id(self):
        """Test transformation skips enrollments with missing student ID."""
        students_data = [
            {'name': 'No ID Student'},  # Missing ID
            {'id': 456, 'user_id': 789}
        ]
        
        with patch.object(self.transformer.logger, 'warning') as mock_warn:
            result = self.transformer.transform_enrollments_data(students_data, 123)
        
        assert len(result) == 1
        assert result[0]['student_id'] == 456
        mock_warn.assert_called_once()
    
    # ==================== FULL TRANSFORMATION TESTS ====================
    
    @pytest.mark.unit
    def test_transform_canvas_staging_data_complete(self):
        """Test complete Canvas staging data transformation."""
        canvas_data = {
            'success': True,
            'course_id': 123,
            'course': {
                'id': 123,
                'name': 'Test Course',
                'course_code': 'TEST101'
            },
            'students': [
                {
                    'id': 456,
                    'user_id': 789,
                    'user': {'name': 'John Doe', 'login_id': 'john.doe'},
                    'current_score': 85,
                    'final_score': 90
                }
            ],
            'modules': [
                {
                    'id': 301,
                    'assignments': [
                        {
                            'id': 501,
                            'title': 'Assignment 1',
                            'type': 'Assignment',
                            'content_details': {'points_possible': 100}
                        }
                    ]
                }
            ]
        }
        
        result = self.transformer.transform_canvas_staging_data(canvas_data)
        
        assert 'courses' in result
        assert 'students' in result
        assert 'assignments' in result
        assert 'enrollments' in result
        
        assert len(result['courses']) == 1
        assert len(result['students']) == 1
        assert len(result['assignments']) == 1
        assert len(result['enrollments']) == 1
        
        # Verify course
        course = result['courses'][0]
        assert course['id'] == 123
        assert course['name'] == 'Test Course'
        
        # Verify student
        student = result['students'][0]
        assert student['student_id'] == 456
        assert student['name'] == 'John Doe'
        
        # Verify assignment
        assignment = result['assignments'][0]
        assert assignment['id'] == 501
        assert assignment['course_id'] == 123
        assert assignment['module_id'] == 301
        
        # Verify enrollment
        enrollment = result['enrollments'][0]
        assert enrollment['student_id'] == 456
        assert enrollment['course_id'] == 123
    
    @pytest.mark.unit
    def test_transform_canvas_staging_data_validation_error(self):
        """Test transformation with validation error."""
        invalid_data = {'success': False, 'error': {'message': 'API failed'}}
        
        with pytest.raises(ValidationError) as exc_info:
            self.transformer.transform_canvas_staging_data(invalid_data)
        
        assert "Failed to transform Canvas staging data" in str(exc_info.value)
    
    @pytest.mark.unit
    def test_get_transformation_summary(self):
        """Test transformation summary without actual transformation."""
        canvas_data = {
            'success': True,
            'course': {'id': 123},
            'students': [{'id': 1}, {'id': 2}],
            'modules': [
                {'assignments': [{'id': 1}, {'id': 2}]},
                {'assignments': [{'id': 3}]}
            ]
        }
        
        summary = self.transformer.get_transformation_summary(canvas_data)
        
        assert summary['valid_structure'] is True
        assert summary['course_count'] == 1
        assert summary['student_count'] == 2
        assert summary['module_count'] == 2
        assert summary['assignment_count'] == 3
        assert 'errors' in summary
        assert 'warnings' in summary


class TestDataTransformerConvenienceFunctions:
    """Test standalone convenience functions."""
    
    @pytest.mark.unit
    def test_transform_canvas_data_function(self):
        """Test transform_canvas_data convenience function."""
        canvas_data = {
            'success': True,
            'course': {'id': 123, 'name': 'Test'},
            'students': [],
            'modules': []
        }
        
        result = transform_canvas_data(canvas_data)
        
        assert isinstance(result, dict)
        assert 'courses' in result
        assert 'students' in result
        assert 'assignments' in result
        assert 'enrollments' in result
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_function_valid(self):
        """Test validate_canvas_data_structure convenience function with valid data."""
        valid_data = {
            'success': True,
            'course': {'id': 123},
            'students': [],
            'modules': []
        }
        
        result = validate_canvas_data_structure(valid_data)
        
        assert result['valid'] is True
        assert result['errors'] == []
    
    @pytest.mark.unit
    def test_validate_canvas_data_structure_function_invalid(self):
        """Test validate_canvas_data_structure convenience function with invalid data."""
        invalid_data = {'success': False}
        
        result = validate_canvas_data_structure(invalid_data)
        
        assert result['valid'] is False
        assert len(result['errors']) > 0
    
    @pytest.mark.unit
    def test_get_transformation_preview_function(self):
        """Test get_transformation_preview convenience function."""
        canvas_data = {
            'success': True,
            'course': {'id': 123},
            'students': [{'id': 1}],
            'modules': [{'assignments': [{'id': 1}]}]
        }
        
        preview = get_transformation_preview(canvas_data)
        
        assert preview['valid_structure'] is True
        assert preview['course_count'] == 1
        assert preview['student_count'] == 1
        assert preview['assignment_count'] == 1


# ==================== INTEGRATION TEST MARKERS ====================

@pytest.mark.integration
class TestDataTransformerIntegration:
    """Integration tests requiring external dependencies or real data."""
    
    def test_transform_real_canvas_data_structure(self):
        """Test transformation with realistic Canvas data structure.
        
        This test uses a structure that matches real Canvas API responses
        to ensure compatibility.
        """
        # This would use actual Canvas API response structure
        # when integration testing is performed
        pass