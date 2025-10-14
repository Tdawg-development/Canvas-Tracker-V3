"""
Layer 1: Canvas Data CRUD Operations

This module provides standard CRUD operations for all Canvas models with
sync-aware functionality, relationship management, and data validation.

Key Features:
- Sync-aware operations (replace vs update)
- Change detection for efficient updates
- Canvas data validation and normalization
- Relationship management between Canvas objects
- Batch operations for performance optimization
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, update, delete, func
from sqlalchemy.exc import SQLAlchemyError

from ..base.base_operations import BaseOperation, CRUDOperation
from ..base.exceptions import (
    CanvasOperationError, DataValidationError, SyncConflictError
)
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)
from database.models.layer2_historical import AssignmentScore


class CanvasDataManager(BaseOperation):
    """
    Comprehensive Canvas data management operations.
    
    Provides sync-aware CRUD operations for Canvas models with
    change detection, validation, and relationship management.
    
    Note: Inherits from BaseOperation instead of CRUDOperation because
    it handles multiple model classes (Course, Student, Assignment, etc.).
    """

    def __init__(self, session: Session):
        """
        Initialize Canvas data manager.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session=session)
    
    def validate_input(self, **kwargs) -> bool:
        """Validate Canvas data input parameters."""
        # Basic validation - can be overridden for specific operations
        return True
    
    # ==================== COURSE OPERATIONS ====================
    
    def sync_course(
        self, 
        canvas_data: Dict[str, Any], 
        update_existing: bool = True
    ) -> CanvasCourse:
        """
        Sync a single course with change detection.
        
        Args:
            canvas_data: Course data from Canvas API
            update_existing: Whether to update existing course or skip
            
        Returns:
            CanvasCourse object (created or updated)
            
        Raises:
            DataValidationError: If canvas_data is invalid
            CanvasOperationError: If sync operation fails
        """
        try:
            # Validate required fields
            if not canvas_data.get('id'):
                raise DataValidationError("Course data missing required 'id' field")
            
            course_id = canvas_data['id']
            
            # Check if course exists
            existing = self.session.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            if existing:
                if not update_existing:
                    return existing
                
                # Always update last_synced to track when record was last verified against Canvas
                existing.last_synced = datetime.now(timezone.utc)
                
                # Check if update is needed (change detection)
                if self._course_needs_update(existing, canvas_data):
                    self._update_course_fields(existing, canvas_data)
                    existing.updated_at = datetime.now(timezone.utc)
                
                self.session.flush()
                return existing
            else:
                # Create new course
                course = self._create_course_from_data(canvas_data)
                self.session.add(course)
                self.session.flush()
                
                return course
                
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to sync course {course_id}: {e}")
    
    def batch_sync_courses(
        self, 
        courses_data: List[Dict[str, Any]],
        update_existing: bool = True
    ) -> Dict[str, List[CanvasCourse]]:
        """
        Efficiently sync multiple courses in batch.
        
        Args:
            courses_data: List of course data from Canvas API
            update_existing: Whether to update existing courses
            
        Returns:
            Dictionary with 'created', 'updated', 'skipped' lists
        """
        result = {
            'created': [],
            'updated': [],
            'skipped': []
        }
        
        try:
            # Extract course IDs for bulk lookup
            course_ids = [course['id'] for course in courses_data if course.get('id')]
            
            # Get existing courses in one query
            existing_courses = self.session.query(CanvasCourse).filter(
                CanvasCourse.id.in_(course_ids)
            ).all()
            
            existing_map = {course.id: course for course in existing_courses}
            
            # Process each course
            for course_data in courses_data:
                if not course_data.get('id'):
                    continue
                    
                course_id = course_data['id']
                existing = existing_map.get(course_id)
                
                if existing:
                    if update_existing:
                        # Always update last_synced to track when record was last verified
                        existing.last_synced = datetime.now(timezone.utc)
                        
                        if self._course_needs_update(existing, course_data):
                            self._update_course_fields(existing, course_data)
                            existing.updated_at = datetime.now(timezone.utc)
                        
                        result['updated'].append(existing)
                    else:
                        result['skipped'].append(existing)
                else:
                    # Create new course
                    new_course = self._create_course_from_data(course_data)
                    self.session.add(new_course)
                    result['created'].append(new_course)
            
            self.session.flush()
            return result
            
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to batch sync courses: {e}")
    
    # ==================== STUDENT OPERATIONS ====================
    
    def sync_student(
        self, 
        canvas_data: Dict[str, Any], 
        update_existing: bool = True
    ) -> CanvasStudent:
        """
        Sync a single student with change detection.
        
        Args:
            canvas_data: Student data from Canvas API
            update_existing: Whether to update existing student
            
        Returns:
            CanvasStudent object (created or updated)
        """
        try:
            # Validate required fields
            if not canvas_data.get('id'):
                raise DataValidationError("Student data missing required 'id' field")
            
            student_id = canvas_data['id']
            
            # Check if student exists
            existing = self.session.query(CanvasStudent).filter(
                CanvasStudent.student_id == student_id
            ).first()
            
            if existing:
                if not update_existing:
                    return existing
                
                # Always update last_synced to track when record was last verified against Canvas
                existing.last_synced = datetime.now(timezone.utc)
                
                # Check if update is needed
                if self._student_needs_update(existing, canvas_data):
                    self._update_student_fields(existing, canvas_data)
                    existing.updated_at = datetime.now(timezone.utc)
                
                self.session.flush()
                return existing
            else:
                # Create new student
                student = self._create_student_from_data(canvas_data)
                self.session.add(student)
                self.session.flush()
                
                return student
                
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to sync student {student_id}: {e}")
    
    def batch_sync_students(
        self, 
        students_data: List[Dict[str, Any]],
        update_existing: bool = True
    ) -> Dict[str, List[CanvasStudent]]:
        """
        Efficiently sync multiple students in batch.
        
        Args:
            students_data: List of student data from Canvas API
            update_existing: Whether to update existing students
            
        Returns:
            Dictionary with 'created', 'updated', 'skipped' lists
        """
        result = {
            'created': [],
            'updated': [],
            'skipped': []
        }
        
        try:
            # Extract student IDs for bulk lookup
            student_ids = [student['id'] for student in students_data if student.get('id')]
            
            # Get existing students in one query
            existing_students = self.session.query(CanvasStudent).filter(
                CanvasStudent.student_id.in_(student_ids)
            ).all()
            
            existing_map = {student.student_id: student for student in existing_students}
            
            # Process each student
            for student_data in students_data:
                if not student_data.get('id'):
                    continue
                    
                student_id = student_data['id']
                existing = existing_map.get(student_id)
                
                if existing:
                    if update_existing:
                        # Always update last_synced to track when record was last verified
                        existing.last_synced = datetime.now(timezone.utc)
                        
                        if self._student_needs_update(existing, student_data):
                            self._update_student_fields(existing, student_data)
                            existing.updated_at = datetime.now(timezone.utc)
                        
                        result['updated'].append(existing)
                    else:
                        result['skipped'].append(existing)
                else:
                    # Create new student
                    new_student = self._create_student_from_data(student_data)
                    self.session.add(new_student)
                    result['created'].append(new_student)
            
            self.session.flush()
            return result
            
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to batch sync students: {e}")
    
    # ==================== ASSIGNMENT OPERATIONS ====================
    
    def sync_assignment(
        self, 
        canvas_data: Dict[str, Any], 
        course_id: int,
        update_existing: bool = True
    ) -> CanvasAssignment:
        """
        Sync a single assignment with change detection.
        
        Args:
            canvas_data: Assignment data from Canvas API
            course_id: ID of the parent course
            update_existing: Whether to update existing assignment
            
        Returns:
            CanvasAssignment object (created or updated)
        """
        try:
            # Validate required fields
            if not canvas_data.get('id'):
                raise DataValidationError("Assignment data missing required 'id' field")
            
            assignment_id = canvas_data['id']
            
            # Check if assignment exists
            existing = self.session.query(CanvasAssignment).filter(
                CanvasAssignment.id == assignment_id
            ).first()
            
            if existing:
                if not update_existing:
                    return existing
                
                # Always update last_synced to track when record was last verified against Canvas
                existing.last_synced = datetime.now(timezone.utc)
                
                # Check if update is needed
                if self._assignment_needs_update(existing, canvas_data):
                    self._update_assignment_fields(existing, canvas_data)
                    existing.updated_at = datetime.now(timezone.utc)
                
                self.session.flush()
                return existing
            else:
                # Create new assignment
                assignment = self._create_assignment_from_data(canvas_data, course_id)
                self.session.add(assignment)
                self.session.flush()
                
                return assignment
                
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to sync assignment {assignment_id}: {e}")
    
    # ==================== ENROLLMENT OPERATIONS ====================
    
    def sync_enrollment(
        self, 
        student_id: int, 
        course_id: int,
        canvas_data: Dict[str, Any],
        update_existing: bool = True
    ) -> CanvasEnrollment:
        """
        Sync a single enrollment relationship.
        
        Args:
            student_id: Canvas student ID
            course_id: Canvas course ID
            canvas_data: Enrollment data from Canvas API
            update_existing: Whether to update existing enrollment
            
        Returns:
            CanvasEnrollment object (created or updated)
        """
        try:
            # Check if enrollment exists
            existing = self.session.query(CanvasEnrollment).filter(
                and_(
                    CanvasEnrollment.student_id == student_id,
                    CanvasEnrollment.course_id == course_id
                )
            ).first()
            
            if existing:
                if not update_existing:
                    return existing
                
                # Always update last_synced to track when record was last verified against Canvas
                existing.last_synced = datetime.now(timezone.utc)
                
                # Check if update is needed
                if self._enrollment_needs_update(existing, canvas_data):
                    self._update_enrollment_fields(existing, canvas_data)
                    existing.updated_at = datetime.now(timezone.utc)
                
                self.session.flush()
                return existing
            else:
                # Create new enrollment
                enrollment = self._create_enrollment_from_data(
                    student_id, course_id, canvas_data
                )
                self.session.add(enrollment)
                self.session.flush()
                
                return enrollment
                
        except SQLAlchemyError as e:
            raise CanvasOperationError(
                f"Failed to sync enrollment {student_id}-{course_id}: {e}"
            )
    
    # ==================== UTILITY OPERATIONS ====================
    
    def get_stale_canvas_data(
        self, 
        hours_threshold: int = 24
    ) -> Dict[str, List[Any]]:
        """
        Identify Canvas objects that need refresh based on last update time.
        
        Args:
            hours_threshold: Hours since last update to consider stale
            
        Returns:
            Dictionary with lists of stale objects by type
        """
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours_threshold)
        
        stale_courses = self.session.query(CanvasCourse).filter(
            CanvasCourse.last_synced < cutoff_time
        ).all()
        
        stale_students = self.session.query(CanvasStudent).filter(
            CanvasStudent.last_synced < cutoff_time
        ).all()
        
        stale_assignments = self.session.query(CanvasAssignment).filter(
            CanvasAssignment.last_synced < cutoff_time
        ).all()
        
        return {
            'courses': stale_courses,
            'students': stale_students,
            'assignments': stale_assignments
        }
    
    def rebuild_course_statistics(self, course_id: int) -> Dict[str, Any]:
        """
        Recalculate derived statistics for a course.
        
        Args:
            course_id: ID of course to rebuild statistics for
            
        Returns:
            Dictionary with calculated statistics
        """
        try:
            # Get course enrollments count
            enrollment_count = self.session.query(CanvasEnrollment).filter(
                CanvasEnrollment.course_id == course_id
            ).count()
            
            # Get assignments count
            assignment_count = self.session.query(CanvasAssignment).filter(
                CanvasAssignment.course_id == course_id
            ).count()
            
            # Calculate average scores if available
            avg_scores = self.session.query(
                func.avg(AssignmentScore.score)
            ).join(
                CanvasAssignment, AssignmentScore.assignment_id == CanvasAssignment.id
            ).filter(
                CanvasAssignment.course_id == course_id
            ).scalar()
            
            stats = {
                'enrollment_count': enrollment_count,
                'assignment_count': assignment_count,
                'average_score': float(avg_scores) if avg_scores else None,
                'last_calculated': datetime.now(timezone.utc)
            }
            
            # Update course with calculated stats (if needed in future)
            # This could be extended to store stats in a course_statistics table
            
            return stats
            
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to rebuild course {course_id} statistics: {e}")
    
    # ==================== PRIVATE HELPER METHODS ====================
    
    def _course_needs_update(self, existing: CanvasCourse, canvas_data: Dict[str, Any]) -> bool:
        """Check if course data has changed and needs update."""
        # Compare key fields that might change
        calendar_ics = ''
        if canvas_data.get('calendar') and canvas_data['calendar'].get('ics'):
            calendar_ics = canvas_data['calendar']['ics']
            
        return (
            existing.name != canvas_data.get('name', existing.name) or
            existing.course_code != canvas_data.get('course_code', existing.course_code) or
            existing.calendar_ics != calendar_ics
        )
    
    def _student_needs_update(self, existing: CanvasStudent, canvas_data: Dict[str, Any]) -> bool:
        """Check if student data has changed and needs update."""
        # Extract name and login_id from user object if present
        name = canvas_data.get('name', existing.name)
        login_id = canvas_data.get('login_id', existing.login_id)
        
        if canvas_data.get('user'):
            user_data = canvas_data['user']
            name = user_data.get('name', name)
            login_id = user_data.get('login_id', login_id)
            
        current_score = canvas_data.get('current_score', existing.current_score) or 0
        final_score = canvas_data.get('final_score', existing.final_score) or 0
        
        # Compare last_activity timestamps (from transformed data)
        canvas_last_activity = canvas_data.get('last_activity')
        if isinstance(canvas_last_activity, str):
            try:
                canvas_last_activity = datetime.fromisoformat(canvas_last_activity.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                canvas_last_activity = None
        
        return (
            existing.name != name or
            existing.email != canvas_data.get('email', existing.email) or
            existing.login_id != login_id or
            existing.current_score != current_score or
            existing.final_score != final_score or
            existing.last_activity != canvas_last_activity
        )
    
    def _assignment_needs_update(self, existing: CanvasAssignment, canvas_data: Dict[str, Any]) -> bool:
        """Check if assignment data has changed and needs update."""
        # Canvas uses 'title' for assignment name
        name = canvas_data.get('title', canvas_data.get('name', existing.name))
        
        # Extract points_possible from content_details if present
        points_possible = existing.points_possible
        if canvas_data.get('content_details') and 'points_possible' in canvas_data['content_details']:
            points_possible = canvas_data['content_details']['points_possible']
        elif 'points_possible' in canvas_data:
            points_possible = canvas_data['points_possible']
            
        return (
            existing.name != name or
            existing.points_possible != points_possible or
            existing.assignment_type != canvas_data.get('assignment_type', canvas_data.get('type', existing.assignment_type)) or
            existing.published != canvas_data.get('published', existing.published) or
            existing.url != canvas_data.get('url', existing.url) or
            existing.module_position != canvas_data.get('position', existing.module_position)
        )
    
    def _enrollment_needs_update(self, existing: CanvasEnrollment, canvas_data: Dict[str, Any]) -> bool:
        """Check if enrollment data has changed and needs update."""
        return (
            existing.enrollment_status != canvas_data.get('enrollment_state', existing.enrollment_status)
        )
    
    def _create_course_from_data(self, canvas_data: Dict[str, Any]) -> CanvasCourse:
        """Create new CanvasCourse from Canvas API data."""
        # Parse Canvas timestamps
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        if canvas_data.get('created_at'):
            try:
                created_at_value = canvas_data['created_at']
                if isinstance(created_at_value, datetime):
                    created_at = created_at_value
                else:
                    created_at = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass  # Use default
                
        if canvas_data.get('updated_at'):
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    updated_at = updated_at_value
                else:
                    updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = created_at  # Fallback to created_at
        else:
            updated_at = created_at
        
        return CanvasCourse(
            id=canvas_data['id'],
            name=canvas_data.get('name', ''),
            course_code=canvas_data.get('course_code', ''),
            calendar_ics=canvas_data.get('calendar', {}).get('ics', '') if canvas_data.get('calendar') else '',
            created_at=created_at,
            updated_at=updated_at,
            last_synced=canvas_data.get('last_synced') or datetime.now(timezone.utc)
        )
    
    def _create_student_from_data(self, canvas_data: Dict[str, Any]) -> CanvasStudent:
        """Create new CanvasStudent from Canvas API data."""
        # Parse Canvas timestamps
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        enrollment_date = created_at
        
        if canvas_data.get('created_at'):
            try:
                created_at_value = canvas_data['created_at']
                if isinstance(created_at_value, datetime):
                    created_at = created_at_value
                else:
                    created_at = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
                enrollment_date = created_at  # Use Canvas creation time for enrollment
            except (ValueError, AttributeError):
                pass
                
        if canvas_data.get('updated_at'):
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    updated_at = updated_at_value
                else:
                    updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = created_at
        else:
            updated_at = created_at
            
        return CanvasStudent(
            student_id=canvas_data['id'],
            user_id=canvas_data.get('user_id'),
            name=canvas_data.get('user', {}).get('name', '') if canvas_data.get('user') else canvas_data.get('name', ''),
            login_id=canvas_data.get('user', {}).get('login_id', '') if canvas_data.get('user') else canvas_data.get('login_id', ''),
            email=canvas_data.get('email', ''),
            current_score=canvas_data.get('current_score', 0) or 0,
            final_score=canvas_data.get('final_score', 0) or 0,
            enrollment_date=enrollment_date,
            last_activity=canvas_data.get('last_activity'),
            created_at=created_at,
            updated_at=updated_at,
            last_synced=canvas_data.get('last_synced') or datetime.now(timezone.utc)
        )
    
    def _create_assignment_from_data(self, canvas_data: Dict[str, Any], course_id: int) -> CanvasAssignment:
        """Create new CanvasAssignment from Canvas API data."""
        # Parse Canvas timestamps
        created_at = datetime.now(timezone.utc)
        updated_at = datetime.now(timezone.utc)
        
        if canvas_data.get('created_at'):
            try:
                created_at_value = canvas_data['created_at']
                if isinstance(created_at_value, datetime):
                    created_at = created_at_value
                else:
                    created_at = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                pass
                
        if canvas_data.get('updated_at'):
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    updated_at = updated_at_value
                else:
                    updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                updated_at = created_at
        else:
            updated_at = created_at
        
        return CanvasAssignment(
            id=canvas_data['id'],
            course_id=course_id,
            module_id=canvas_data.get('module_id', 0),  # Required field from schema
            module_position=canvas_data.get('module_position') or canvas_data.get('position'),
            name=canvas_data.get('title', canvas_data.get('name', '')),  # Canvas uses 'title'
            url=canvas_data.get('url', ''),
            published=canvas_data.get('published', False),
            points_possible=canvas_data.get('content_details', {}).get('points_possible') if canvas_data.get('content_details') else canvas_data.get('points_possible'),
            assignment_type=canvas_data.get('assignment_type') or canvas_data.get('type'),  # Prefer assignment_type, fallback to type
            created_at=created_at,
            updated_at=updated_at,
            last_synced=canvas_data.get('last_synced') or datetime.now(timezone.utc)
        )
    
    def _create_enrollment_from_data(
        self, 
        student_id: int, 
        course_id: int, 
        canvas_data: Dict[str, Any]
    ) -> CanvasEnrollment:
        """Create new CanvasEnrollment from Canvas API data."""
        try:
            # Debug logging
            self.logger.debug(f"Creating enrollment: student_id={student_id} (type: {type(student_id)}), course_id={course_id} (type: {type(course_id)})")
            
            enrollment_date = datetime.now(timezone.utc)
            if canvas_data.get('created_at'):
                try:
                    created_at_value = canvas_data['created_at']
                    if isinstance(created_at_value, datetime):
                        # Already a datetime object
                        enrollment_date = created_at_value
                    else:
                        # String that needs parsing
                        enrollment_date = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
                    self.logger.debug(f"Parsed enrollment_date: {enrollment_date} (type: {type(enrollment_date)})")
                except (ValueError, AttributeError) as e:
                    self.logger.warning(f"Failed to parse enrollment date '{canvas_data.get('created_at')}': {e}")
            
            enrollment_status = canvas_data.get('enrollment_state', 'active')
            self.logger.debug(f"Enrollment status: {enrollment_status} (type: {type(enrollment_status)})")
            
            # Ensure all values are correct types before creating model
            if not isinstance(student_id, int):
                raise ValueError(f"student_id must be int, got {type(student_id)}: {student_id}")
            if not isinstance(course_id, int):
                raise ValueError(f"course_id must be int, got {type(course_id)}: {course_id}")
                
            # Parse Canvas timestamps for created_at/updated_at
            created_at = datetime.now(timezone.utc)
            updated_at = datetime.now(timezone.utc)
            
            if canvas_data.get('created_at'):
                try:
                    created_at_value = canvas_data['created_at']
                    if isinstance(created_at_value, datetime):
                        # Already a datetime object
                        created_at = created_at_value
                    else:
                        # String that needs parsing
                        created_at = datetime.fromisoformat(created_at_value.replace('Z', '+00:00'))
                    # Always use Canvas time for enrollment
                    enrollment_date = created_at
                except (ValueError, AttributeError):
                    pass
                    
            if canvas_data.get('updated_at'):
                try:
                    updated_at_value = canvas_data['updated_at']
                    if isinstance(updated_at_value, datetime):
                        # Already a datetime object
                        updated_at = updated_at_value
                    else:
                        # String that needs parsing
                        updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    updated_at = created_at
            else:
                updated_at = created_at
            
            # Log all parameters before model creation
            params = {
                'student_id': student_id,
                'course_id': course_id,
                'enrollment_date': enrollment_date,
                'enrollment_status': enrollment_status,
                'created_at': created_at,
                'updated_at': updated_at,
                'last_synced': canvas_data.get('last_synced') or datetime.now(timezone.utc)
            }
            self.logger.debug(f"CanvasEnrollment parameters: {params}")
            for key, value in params.items():
                self.logger.debug(f"  {key}: {value} (type: {type(value)})")
            
            # Try to create the model with detailed error handling
            try:
                enrollment = CanvasEnrollment(**params)
                self.logger.debug(f"CanvasEnrollment instance created successfully: {enrollment}")
                return enrollment
            except Exception as model_error:
                self.logger.error(f"Failed to create CanvasEnrollment instance: {model_error}")
                self.logger.error(f"Error type: {type(model_error)}")
                raise
        except Exception as e:
            self.logger.error(f"Failed to create enrollment from data: {e}")
            self.logger.error(f"Data: student_id={student_id}, course_id={course_id}, canvas_data={canvas_data}")
            raise
    
    def _update_course_fields(self, course: CanvasCourse, canvas_data: Dict[str, Any]) -> None:
        """Update existing course with new data."""
        if 'name' in canvas_data:
            course.name = canvas_data['name']
        if 'course_code' in canvas_data:
            course.course_code = canvas_data['course_code']
        if 'calendar' in canvas_data and canvas_data['calendar']:
            course.calendar_ics = canvas_data['calendar'].get('ics', '')
        
        # Update timestamp from Canvas data
        if 'updated_at' in canvas_data:
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    course.updated_at = updated_at_value
                else:
                    course.updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                course.updated_at = datetime.now(timezone.utc)
        
        # Always update last_synced on sync
        course.last_synced = datetime.now(timezone.utc)
    
    def _update_student_fields(self, student: CanvasStudent, canvas_data: Dict[str, Any]) -> None:
        """Update existing student with new data."""
        if 'user' in canvas_data and canvas_data['user']:
            user_data = canvas_data['user']
            if 'name' in user_data:
                student.name = user_data['name']
            if 'login_id' in user_data:
                student.login_id = user_data['login_id']
        elif 'name' in canvas_data:
            student.name = canvas_data['name']
        
        if 'email' in canvas_data:
            student.email = canvas_data['email']
        if 'login_id' in canvas_data:
            student.login_id = canvas_data['login_id']
        if 'current_score' in canvas_data:
            student.current_score = canvas_data['current_score'] or 0
        if 'final_score' in canvas_data:
            student.final_score = canvas_data['final_score'] or 0
        if 'last_activity' in canvas_data:
            last_activity_value = canvas_data['last_activity']
            if isinstance(last_activity_value, datetime):
                student.last_activity = last_activity_value
            elif isinstance(last_activity_value, str):
                try:
                    student.last_activity = datetime.fromisoformat(last_activity_value.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    student.last_activity = None
            else:
                student.last_activity = last_activity_value  # None or other value
        
        # Update timestamp from Canvas data
        if 'updated_at' in canvas_data:
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    student.updated_at = updated_at_value
                else:
                    student.updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                student.updated_at = datetime.now(timezone.utc)
        
        # Always update last_synced on sync
        student.last_synced = datetime.now(timezone.utc)
    
    def _update_assignment_fields(self, assignment: CanvasAssignment, canvas_data: Dict[str, Any]) -> None:
        """Update existing assignment with new data."""
        if 'title' in canvas_data:
            assignment.name = canvas_data['title']
        elif 'name' in canvas_data:
            assignment.name = canvas_data['name']
        
        if 'content_details' in canvas_data and canvas_data['content_details']:
            if 'points_possible' in canvas_data['content_details']:
                assignment.points_possible = canvas_data['content_details']['points_possible']
        elif 'points_possible' in canvas_data:
            assignment.points_possible = canvas_data['points_possible']
        
        if 'assignment_type' in canvas_data:
            assignment.assignment_type = canvas_data['assignment_type']
        elif 'type' in canvas_data:
            assignment.assignment_type = canvas_data['type']  # Fallback to type if assignment_type not available
        if 'module_position' in canvas_data:
            assignment.module_position = canvas_data['module_position']
        elif 'position' in canvas_data:
            assignment.module_position = canvas_data['position']
        if 'url' in canvas_data:
            assignment.url = canvas_data['url']
        if 'published' in canvas_data:
            assignment.published = canvas_data['published']
        if 'last_synced' in canvas_data:
            assignment.last_synced = canvas_data['last_synced']
        if 'position' in canvas_data:
            assignment.module_position = canvas_data['position']
        
        # Update timestamp from Canvas data
        if 'updated_at' in canvas_data:
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    assignment.updated_at = updated_at_value
                else:
                    assignment.updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                assignment.updated_at = datetime.now(timezone.utc)
    
    def _update_enrollment_fields(self, enrollment: CanvasEnrollment, canvas_data: Dict[str, Any]) -> None:
        """Update existing enrollment with new data."""
        if 'enrollment_state' in canvas_data:
            enrollment.enrollment_status = canvas_data['enrollment_state']
        
        # Update timestamp from Canvas data
        if 'updated_at' in canvas_data:
            try:
                updated_at_value = canvas_data['updated_at']
                if isinstance(updated_at_value, datetime):
                    enrollment.updated_at = updated_at_value
                else:
                    enrollment.updated_at = datetime.fromisoformat(updated_at_value.replace('Z', '+00:00'))
            except (ValueError, AttributeError):
                enrollment.updated_at = datetime.now(timezone.utc)
        
        # Always update last_synced on sync
        enrollment.last_synced = datetime.now(timezone.utc)
