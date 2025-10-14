"""
Data Transformation Layer

This module provides data transformation utilities to convert between TypeScript Canvas
staging data formats and Python database model formats. It handles the critical data
format bridging that enables seamless integration between the Canvas interface and
database operations.

Key Features:
- Transform TypeScript CanvasCourseStaging to database sync format
- Handle Canvas datetime parsing and timezone conversion
- Convert nested TypeScript objects to flat database records
- Validate and normalize data during transformation
- Support for all Canvas entity types (courses, students, assignments, enrollments)
"""

import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from .base.exceptions import ValidationError, DataValidationError


@dataclass
class TransformationResult:
    """Container for data transformation results."""
    success: bool
    transformed_data: Optional[Dict[str, List[Dict[str, Any]]]]
    source_counts: Dict[str, int]
    transformed_counts: Dict[str, int]
    errors: List[str]
    warnings: List[str]


class CanvasDataTransformer:
    """
    Transform between TypeScript Canvas staging data and Python database formats.
    
    This class handles the critical data format conversion that bridges TypeScript
    Canvas interface data with Python database operations. It converts nested,
    hierarchical Canvas data structures into flat database records suitable for
    SQLAlchemy model creation.
    
    Features:
    - TypeScript to Python data format conversion
    - Canvas datetime parsing with timezone handling
    - Nested object flattening for database storage
    - Data validation and normalization
    - Comprehensive error handling and logging
    """

    def __init__(self):
        """Initialize Canvas data transformer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info("Canvas Data Transformer initialized")

    def transform_canvas_staging_data(
        self, 
        canvas_data: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Transform complete TypeScript CanvasCourseStaging data to database sync format.
        
        Args:
            canvas_data: Complete Canvas data from TypeScript execution
            
        Returns:
            Dictionary with database-ready data organized by entity type:
            - courses: List of course records
            - students: List of student records  
            - assignments: List of assignment records
            - enrollments: List of enrollment records
            
        Raises:
            ValidationError: If data validation fails
        """
        self.logger.info("Starting Canvas staging data transformation")
        
        try:
            # Validate input data structure
            self._validate_canvas_data_structure(canvas_data)
            
            # Extract course information
            course_data = canvas_data.get('course', {})
            students_data = canvas_data.get('students', [])
            modules_data = canvas_data.get('modules', [])
            
            # Transform each entity type
            transformed_courses = self.transform_course_data(course_data)
            transformed_students = self.transform_students_data(students_data)
            transformed_assignments = self.transform_assignments_data(modules_data, course_data.get('id'))
            transformed_enrollments = self.transform_enrollments_data(students_data, course_data.get('id'))
            
            result = {
                'courses': transformed_courses,
                'students': transformed_students,
                'assignments': transformed_assignments,
                'enrollments': transformed_enrollments
            }
            
            # Log transformation summary
            self.logger.info(f"Transformation completed:")
            self.logger.info(f"  - Courses: {len(transformed_courses)} records")
            self.logger.info(f"  - Students: {len(transformed_students)} records")
            self.logger.info(f"  - Assignments: {len(transformed_assignments)} records")
            self.logger.info(f"  - Enrollments: {len(transformed_enrollments)} records")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Canvas data transformation failed: {str(e)}", exc_info=True)
            raise ValidationError(
                f"Failed to transform Canvas staging data: {str(e)}",
                operation_name="canvas_data_transformation"
            )

    def transform_course_data(self, course_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Transform TypeScript course data to database CanvasCourse format.
        
        Args:
            course_data: Course data from TypeScript CanvasCourseStaging
            
        Returns:
            List containing single transformed course record
        """
        if not course_data or not course_data.get('id'):
            self.logger.warning("Empty or invalid course data provided")
            return []
        
        try:
            transformed_course = {
                'id': course_data['id'],
                'name': course_data.get('name', ''),
                'course_code': course_data.get('course_code', ''),
                'calendar_ics': self._extract_calendar_ics(course_data),
                'workflow_state': course_data.get('workflow_state', 'available'),
                'start_at': self._parse_canvas_datetime(course_data.get('start_at')),
                'end_at': self._parse_canvas_datetime(course_data.get('end_at')),
                'last_synced': datetime.now(timezone.utc)
            }
            
            # Add computed fields if available from metadata
            metadata = course_data.get('metadata', {})
            if metadata:
                transformed_course.update({
                    'total_students': metadata.get('total_students'),
                    'total_modules': metadata.get('total_modules'),  
                    'total_assignments': metadata.get('total_assignments')
                })
            
            return [transformed_course]
            
        except Exception as e:
            self.logger.error(f"Failed to transform course data: {str(e)}")
            raise ValidationError(
                f"Course data transformation failed: {str(e)}",
                field_name="course_data",
                operation_name="transform_course_data"
            )

    def transform_students_data(self, students_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Transform TypeScript student data to database CanvasStudent format.
        
        Args:
            students_data: List of student data from TypeScript CanvasStudentStaging
            
        Returns:
            List of transformed student records
        """
        if not students_data:
            self.logger.info("No student data to transform")
            return []
        
        transformed_students = []
        
        for i, student_data in enumerate(students_data):
            try:
                # DEBUG: Print first student's raw data to understand structure
                if i == 0:
                    self.logger.info(f"DEBUG: First student raw data keys: {list(student_data.keys())}")
                    self.logger.info(f"DEBUG: last_activity_at value: {student_data.get('last_activity_at')}")
                    if 'user' in student_data:
                        self.logger.info(f"DEBUG: user object keys: {list(student_data['user'].keys())}")
                # Extract user information (handle both nested and flat structures)
                user_info = student_data.get('user', {})
                if not user_info and student_data.get('user_id'):
                    # Handle flat structure - extract user fields directly
                    user_info = {
                        'id': student_data.get('user_id'),
                        'name': student_data.get('name', 'Unknown'),
                        'login_id': student_data.get('login_id', 'unknown'),
                        'sortable_name': student_data.get('sortable_name', 'Unknown')
                    }
                
                # Get IDs and ensure they are integers
                student_id = student_data.get('id') or student_data.get('user_id')
                user_id = user_info.get('id') or student_data.get('user_id')
                
                transformed_student = {
                    'id': int(student_id) if student_id else None,  # Canvas student ID for sync operations
                    'student_id': int(student_id) if student_id else None,  # Keep for database compatibility
                    'user_id': int(user_id) if user_id else None,
                    'name': user_info.get('name', 'Unknown'),
                    'login_id': user_info.get('login_id', 'unknown'),
                    'email': user_info.get('email', student_data.get('email', '')),  # Check user object first, then root level
                    'current_score': self._normalize_score(student_data.get('current_score')),
                    'final_score': self._normalize_score(student_data.get('final_score')),
                    'enrollment_date': self._parse_canvas_datetime(student_data.get('created_at')),
                    'last_activity': self._parse_canvas_datetime(student_data.get('last_activity_at')),
                    # DEBUG: Log last_activity extraction
                    '_debug_last_activity_raw': student_data.get('last_activity_at'),
                    'created_at': self._parse_canvas_datetime(student_data.get('created_at')),
                    'updated_at': datetime.now(timezone.utc),
                    'last_synced': datetime.now(timezone.utc)
                }
                
                # Validate required fields
                if not transformed_student['id']:
                    self.logger.warning(f"Student missing required ID: {student_data}")
                    continue
                    
                transformed_students.append(transformed_student)
                
            except Exception as e:
                self.logger.error(f"Failed to transform student data {student_data.get('id', 'unknown')}: {str(e)}")
                continue  # Skip problematic records but continue processing
        
        self.logger.info(f"Transformed {len(transformed_students)} students")
        return transformed_students

    def transform_assignments_data(
        self, 
        modules_data: List[Dict[str, Any]], 
        course_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Transform TypeScript modules and assignments data to database CanvasAssignment format.
        
        Args:
            modules_data: List of module data from TypeScript CanvasModuleStaging
            course_id: Course ID to associate with assignments
            
        Returns:
            List of transformed assignment records
        """
        if not modules_data or not course_id:
            self.logger.info("No modules data or course ID to transform assignments")
            return []
        
        transformed_assignments = []
        
        for module_data in modules_data:
            module_id = module_data.get('id')
            assignments = module_data.get('assignments', [])
            
            for assignment_data in assignments:
                try:
                    # Extract content details
                    content_details = assignment_data.get('content_details', {})
                    points_possible = content_details.get('points_possible')
                    
                    # Parse Canvas timestamps with fallbacks
                    created_at = self._parse_canvas_datetime(assignment_data.get('created_at'))
                    updated_at = self._parse_canvas_datetime(assignment_data.get('updated_at'))
                    
                    # Use reasonable fallbacks when Canvas timestamps are not available
                    # This can happen for assignments fetched from modules API without full data
                    current_time = datetime.now(timezone.utc)
                    if created_at is None:
                        # Use a reasonable default creation date (course start or early timestamp)
                        created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)  # Reasonable course start fallback
                    if updated_at is None:
                        # Use created_at as updated_at fallback, or current time if created_at is also fallback
                        updated_at = created_at if assignment_data.get('created_at') else current_time
                    
                    # Get the assignment type - prefer assignment_type field, fallback to type
                    assignment_type = assignment_data.get('assignment_type') or assignment_data.get('type')
                    
                    transformed_assignment = {
                        'id': assignment_data.get('id'),
                        'course_id': course_id,
                        'module_id': assignment_data.get('module_id') or module_id,  # Prefer explicit module_id
                        'module_position': assignment_data.get('position'),
                        'url': assignment_data.get('url', ''),
                        'name': assignment_data.get('title', ''),  # TypeScript uses 'title'
                        'published': bool(assignment_data.get('published', False)),
                        'points_possible': points_possible,
                        'assignment_type': self._normalize_assignment_type(assignment_type),  # Use normalized type
                        'created_at': created_at,
                        'updated_at': updated_at,
                        'last_synced': current_time
                    }
                    
                    # Validate required fields
                    if not transformed_assignment['id'] or not transformed_assignment['module_id']:
                        self.logger.warning(f"Assignment missing required fields: {assignment_data}")
                        continue
                    
                    transformed_assignments.append(transformed_assignment)
                    
                except Exception as e:
                    self.logger.error(f"Failed to transform assignment {assignment_data.get('id', 'unknown')}: {str(e)}")
                    continue  # Skip problematic records but continue processing
        
        self.logger.info(f"Transformed {len(transformed_assignments)} assignments from {len(modules_data)} modules")
        return transformed_assignments

    def transform_enrollments_data(
        self, 
        students_data: List[Dict[str, Any]], 
        course_id: Optional[int]
    ) -> List[Dict[str, Any]]:
        """
        Transform student data to database CanvasEnrollment format.
        
        Args:
            students_data: List of student data from TypeScript
            course_id: Course ID to associate with enrollments
            
        Returns:
            List of transformed enrollment records
        """
        if not students_data or not course_id:
            self.logger.info("No students data or course ID to transform enrollments")
            return []
        
        transformed_enrollments = []
        
        for student_data in students_data:
            try:
                student_id = student_data.get('id') or student_data.get('user_id')
                if not student_id:
                    self.logger.warning(f"Student missing ID for enrollment: {student_data}")
                    continue
                
                enrollment_date = self._parse_canvas_datetime(student_data.get('created_at'))
                if not enrollment_date:
                    enrollment_date = datetime.now(timezone.utc)  # Fallback to current time
                
                transformed_enrollment = {
                    'student_id': int(student_id),  # Convert to integer for database
                    'course_id': int(course_id),    # Ensure course_id is also integer
                    'enrollment_date': enrollment_date,
                    'enrollment_status': student_data.get('enrollment_state', 'active'),  # Default to active
                    'created_at': enrollment_date,
                    'updated_at': datetime.now(timezone.utc),
                    'last_synced': datetime.now(timezone.utc)
                }
                
                transformed_enrollments.append(transformed_enrollment)
                
            except Exception as e:
                self.logger.error(f"Failed to transform enrollment for student {student_data.get('id', 'unknown')}: {str(e)}")
                continue  # Skip problematic records but continue processing
        
        self.logger.info(f"Transformed {len(transformed_enrollments)} enrollments")
        return transformed_enrollments

    def _validate_canvas_data_structure(self, canvas_data: Dict[str, Any]) -> None:
        """
        Validate the structure of Canvas data from TypeScript execution.
        
        Args:
            canvas_data: Canvas data to validate
            
        Raises:
            ValidationError: If data structure is invalid
        """
        if not isinstance(canvas_data, dict):
            raise ValidationError(
                f"Canvas data must be a dictionary, got {type(canvas_data)}",
                operation_name="canvas_data_validation"
            )
        
        # Check for success flag
        if not canvas_data.get('success', False):
            error_info = canvas_data.get('error', {})
            raise ValidationError(
                f"Canvas data indicates failure: {error_info.get('message', 'Unknown error')}",
                operation_name="canvas_data_validation"
            )
        
        # Check for required top-level fields
        required_fields = ['course', 'students', 'modules']
        missing_fields = [field for field in required_fields if field not in canvas_data]
        
        if missing_fields:
            raise ValidationError(
                f"Canvas data missing required fields: {missing_fields}",
                operation_name="canvas_data_validation"
            )
        
        # Validate course data has ID
        course_data = canvas_data.get('course', {})
        if not course_data.get('id'):
            raise ValidationError(
                "Course data missing required 'id' field",
                field_name="course.id",
                operation_name="canvas_data_validation"
            )

    def _parse_canvas_datetime(self, date_string: Optional[str]) -> Optional[datetime]:
        """
        Parse Canvas datetime strings to Python datetime objects with timezone handling.
        
        Args:
            date_string: Canvas datetime string (ISO 8601 format)
            
        Returns:
            Python datetime object with UTC timezone, or None if parsing fails
        """
        if not date_string:
            self.logger.debug(f"DEBUG: _parse_canvas_datetime received None/empty: {date_string}")
            return None
        
        # DEBUG: Log what we're trying to parse
        self.logger.debug(f"DEBUG: _parse_canvas_datetime parsing: '{date_string}'")
        
        try:
            # Handle Canvas ISO 8601 format (e.g., "2023-10-14T17:30:00Z")
            if date_string.endswith('Z'):
                # Replace Z with +00:00 for Python parsing
                date_string = date_string.replace('Z', '+00:00')
            elif '+' not in date_string and '-' not in date_string[-6:]:
                # No timezone specified, assume UTC
                date_string = date_string + '+00:00'
            
            # Parse to datetime with timezone
            dt = datetime.fromisoformat(date_string)
            
            # Convert to UTC if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            # DEBUG: Log successful parsing
            self.logger.debug(f"DEBUG: _parse_canvas_datetime success: '{date_string}' -> {dt}")
            return dt
            
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse Canvas datetime '{date_string}': {e}")
            return None

    def _extract_calendar_ics(self, course_data: Dict[str, Any]) -> str:
        """
        Extract calendar ICS URL from course data.
        
        Args:
            course_data: Course data from TypeScript
            
        Returns:
            Calendar ICS URL or empty string
        """
        calendar = course_data.get('calendar')
        if isinstance(calendar, dict):
            return calendar.get('ics', '')
        return ''

    def _normalize_score(self, score: Any) -> int:
        """
        Normalize Canvas scores to integer percentages.
        
        Args:
            score: Score value from Canvas (may be None, float, or string)
            
        Returns:
            Integer score (0-100) or 0 if invalid
        """
        if score is None:
            return 0
        
        try:
            # Convert to float first, then to int
            float_score = float(score)
            return int(round(float_score))
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to normalize score '{score}', defaulting to 0")
            return 0

    def _normalize_assignment_type(self, assignment_type: Optional[str]) -> str:
        """
        Normalize assignment type strings.
        
        Args:
            assignment_type: Assignment type from TypeScript
            
        Returns:
            Normalized assignment type string
        """
        if not assignment_type:
            return 'Assignment'
        
        # Normalize common variations
        type_mapping = {
            'assignment': 'Assignment',
            'quiz': 'Quiz',
            'discussion': 'Discussion',
            'external_tool': 'ExternalTool',
            'page': 'Page'
        }
        
        normalized = type_mapping.get(assignment_type.lower(), assignment_type)
        return normalized

    def get_transformation_summary(
        self, 
        canvas_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get summary of transformation without actually transforming data.
        
        Args:
            canvas_data: Canvas data from TypeScript execution
            
        Returns:
            Dictionary with transformation summary information
        """
        try:
            summary = {
                'valid_structure': False,
                'course_count': 0,
                'student_count': 0,
                'module_count': 0,
                'assignment_count': 0,
                'errors': [],
                'warnings': []
            }
            
            # Validate structure
            try:
                self._validate_canvas_data_structure(canvas_data)
                summary['valid_structure'] = True
            except ValidationError as e:
                summary['errors'].append(str(e))
                return summary
            
            # Count entities
            course_data = canvas_data.get('course', {})
            students_data = canvas_data.get('students', [])
            modules_data = canvas_data.get('modules', [])
            
            summary['course_count'] = 1 if course_data.get('id') else 0
            summary['student_count'] = len(students_data)
            summary['module_count'] = len(modules_data)
            
            # Count assignments across all modules
            assignment_count = 0
            for module_data in modules_data:
                assignments = module_data.get('assignments', [])
                assignment_count += len(assignments)
            summary['assignment_count'] = assignment_count
            
            return summary
            
        except Exception as e:
            return {
                'valid_structure': False,
                'error': f"Failed to generate summary: {str(e)}",
                'course_count': 0,
                'student_count': 0,
                'module_count': 0,
                'assignment_count': 0
            }


# Convenience functions for direct transformation
def transform_canvas_data(canvas_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Convenience function to transform Canvas data with default settings.
    
    Args:
        canvas_data: Canvas data from TypeScript execution
        
    Returns:
        Dictionary with transformed database-ready data
    """
    transformer = CanvasDataTransformer()
    return transformer.transform_canvas_staging_data(canvas_data)


def validate_canvas_data_structure(canvas_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to validate Canvas data structure.
    
    Args:
        canvas_data: Canvas data to validate
        
    Returns:
        Dictionary with validation results
    """
    transformer = CanvasDataTransformer()
    try:
        transformer._validate_canvas_data_structure(canvas_data)
        return {'valid': True, 'errors': []}
    except ValidationError as e:
        return {'valid': False, 'errors': [str(e)]}
    except Exception as e:
        return {'valid': False, 'errors': [f"Validation error: {str(e)}"]}


def get_transformation_preview(canvas_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to preview transformation results.
    
    Args:
        canvas_data: Canvas data from TypeScript execution
        
    Returns:
        Dictionary with transformation preview
    """
    transformer = CanvasDataTransformer()
    return transformer.get_transformation_summary(canvas_data)