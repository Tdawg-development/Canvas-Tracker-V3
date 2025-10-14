"""
Layer 1: Canvas Object Relationship Management

This module manages relationships between Canvas objects with referential integrity,
optimized queries, and relationship validation.

Key Features:
- Student-course enrollment relationship management
- Assignment-course relationship validation
- Referential integrity maintenance during sync
- Optimized relationship queries for performance
- Cascade operations for related data
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime, timezone
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import and_, or_, select, func, exists
from sqlalchemy.exc import SQLAlchemyError, IntegrityError

from ..base.base_operations import BaseOperation
from ..base.exceptions import (
    CanvasOperationError, RelationshipError, ValidationError
)
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)
from database.models.layer2_historical import AssignmentScore


class RelationshipManager(BaseOperation):
    """
    Canvas object relationship management operations.
    
    Manages complex relationships between Canvas objects with integrity
    validation, performance optimization, and cascade operations.
    """

    def __init__(self, session: Session):
        """
        Initialize relationship manager.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session)
    
    def validate_input(self, **kwargs) -> bool:
        """Validate relationship operation input parameters."""
        # Basic validation - can be overridden for specific operations
        return True
    
    # ==================== ENROLLMENT RELATIONSHIPS ====================
    
    def create_enrollment_relationship(
        self,
        student_id: int,
        course_id: int,
        enrollment_data: Optional[Dict[str, Any]] = None
    ) -> CanvasEnrollment:
        """
        Create student-course enrollment relationship with validation.
        
        Args:
            student_id: Canvas student ID
            course_id: Canvas course ID
            enrollment_data: Optional enrollment metadata
            
        Returns:
            Created CanvasEnrollment object
            
        Raises:
            ValidationError: If student or course doesn't exist
            RelationshipError: If enrollment already exists
        """
        try:
            # Validate student exists
            student = self.session.query(CanvasStudent).filter(
                CanvasStudent.student_id == student_id
            ).first()
            
            if not student:
                raise ValidationError(f"Student {student_id} not found")
            
            # Validate course exists
            course = self.session.query(CanvasCourse).filter(
                CanvasCourse.id == course_id
            ).first()
            
            if not course:
                raise ValidationError(f"Course {course_id} not found")
            
            # Check if enrollment already exists
            existing = self.session.query(CanvasEnrollment).filter(
                and_(
                    CanvasEnrollment.student_id == student_id,
                    CanvasEnrollment.course_id == course_id
                )
            ).first()
            
            if existing:
                raise RelationshipError(
                    f"Enrollment already exists for student {student_id} in course {course_id}"
                )
            
            # Create enrollment  
            enrollment_date = datetime.now(timezone.utc)
            if enrollment_data and enrollment_data.get('created_at'):
                try:
                    enrollment_date = datetime.fromisoformat(enrollment_data['created_at'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    pass
            
            enrollment = CanvasEnrollment(
                student_id=student_id,
                course_id=course_id,
                enrollment_date=enrollment_date,
                enrollment_status=enrollment_data.get('enrollment_state', 'active') if enrollment_data else 'active'
            )
            
            self.session.add(enrollment)
            self.session.flush()
            
            return enrollment
            
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to create enrollment relationship: {e}")
    
    def get_student_enrollments(
        self,
        student_id: int,
        active_only: bool = True,
        include_courses: bool = False
    ) -> List[CanvasEnrollment]:
        """
        Get all enrollments for a student.
        
        Args:
            student_id: Canvas student ID
            active_only: Only return active enrollments
            include_courses: Include course data in results
            
        Returns:
            List of CanvasEnrollment objects
        """
        query = self.session.query(CanvasEnrollment).filter(
            CanvasEnrollment.student_id == student_id
        )
        
        if active_only:
            query = query.filter(CanvasEnrollment.enrollment_status == 'active')
        
        if include_courses:
            query = query.options(joinedload(CanvasEnrollment.course))
        
        return query.all()
    
    def get_course_enrollments(
        self,
        course_id: int,
        active_only: bool = True,
        include_students: bool = False
    ) -> List[CanvasEnrollment]:
        """
        Get all enrollments for a course.
        
        Args:
            course_id: Canvas course ID
            active_only: Only return active enrollments
            include_students: Include student data in results
            
        Returns:
            List of CanvasEnrollment objects
        """
        query = self.session.query(CanvasEnrollment).filter(
            CanvasEnrollment.course_id == course_id
        )
        
        if active_only:
            query = query.filter(CanvasEnrollment.enrollment_status == 'active')
        
        if include_students:
            query = query.options(joinedload(CanvasEnrollment.student))
        
        return query.all()
    
    def update_enrollment_status(
        self,
        student_id: int,
        course_id: int,
        new_status: str
    ) -> CanvasEnrollment:
        """
        Update enrollment status.
        
        Args:
            student_id: Canvas student ID
            course_id: Canvas course ID
            new_status: New enrollment status
            
        Returns:
            Updated CanvasEnrollment object
            
        Raises:
            ValidationError: If enrollment doesn't exist
        """
        enrollment = self.session.query(CanvasEnrollment).filter(
            and_(
                CanvasEnrollment.student_id == student_id,
                CanvasEnrollment.course_id == course_id
            )
        ).first()
        
        if not enrollment:
            raise ValidationError(
                f"Enrollment not found for student {student_id} in course {course_id}"
            )
        
        enrollment.enrollment_status = new_status
        enrollment.updated_at = datetime.now(timezone.utc)
        self.session.flush()
        
        return enrollment
    
    # ==================== ASSIGNMENT RELATIONSHIPS ====================
    
    def validate_assignment_course_relationship(
        self,
        assignment_id: int,
        course_id: int
    ) -> bool:
        """
        Validate that assignment belongs to specified course.
        
        Args:
            assignment_id: Canvas assignment ID
            course_id: Canvas course ID
            
        Returns:
            True if relationship is valid, False otherwise
        """
        assignment = self.session.query(CanvasAssignment).filter(
            CanvasAssignment.id == assignment_id
        ).first()
        
        if not assignment:
            return False
        
        return assignment.course_id == course_id
    
    def get_course_assignments(
        self,
        course_id: int,
        include_scores: bool = False
    ) -> List[CanvasAssignment]:
        """
        Get all assignments for a course.
        
        Args:
            course_id: Canvas course ID
            include_scores: Include assignment scores in results
            
        Returns:
            List of CanvasAssignment objects
        """
        query = self.session.query(CanvasAssignment).filter(
            CanvasAssignment.course_id == course_id
        )
        
        if include_scores:
            # Note: assignment_scores relationship removed to prevent forward dependency
            # Scores must be fetched separately via AssignmentScore queries
            pass
        
        return query.order_by(CanvasAssignment.module_position).all()
    
    def get_student_assignments_in_course(
        self,
        student_id: int,
        course_id: int,
        include_scores: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get all assignments for a student in a specific course.
        
        Args:
            student_id: Canvas student ID
            course_id: Canvas course ID
            include_scores: Include score information
            
        Returns:
            List of assignment data with optional scores
        """
        assignments = self.session.query(CanvasAssignment).filter(
            CanvasAssignment.course_id == course_id
        ).all()
        
        if not include_scores:
            return [{'assignment': assignment} for assignment in assignments]
        
        # Get scores for this student
        scores = self.session.query(AssignmentScore).filter(
            and_(
                AssignmentScore.student_id == student_id,
                AssignmentScore.assignment_id.in_([a.id for a in assignments])
            )
        ).all()
        
        score_map = {score.assignment_id: score for score in scores}
        
        result = []
        for assignment in assignments:
            result.append({
                'assignment': assignment,
                'score': score_map.get(assignment.id)
            })
        
        return result
    
    # ==================== REFERENTIAL INTEGRITY ====================
    
    def validate_referential_integrity(self) -> Dict[str, List[str]]:
        """
        Validate referential integrity across all Canvas relationships.
        
        Returns:
            Dictionary with lists of integrity violations by type
        """
        violations = {
            'orphaned_assignments': [],
            'orphaned_enrollments': [],
            'orphaned_scores': [],
            'invalid_references': []
        }
        
        try:
            # Check for assignments without valid courses
            orphaned_assignments = self.session.query(CanvasAssignment).filter(
                ~CanvasAssignment.course_id.in_(
                    select(CanvasCourse.id)
                )
            ).all()
            
            violations['orphaned_assignments'] = [
                f"Assignment {a.id} references non-existent course {a.course_id}"
                for a in orphaned_assignments
            ]
            
            # Check for enrollments with invalid references
            orphaned_enrollments = self.session.query(CanvasEnrollment).filter(
                or_(
                    ~CanvasEnrollment.course_id.in_(select(CanvasCourse.id)),
                    ~CanvasEnrollment.student_id.in_(select(CanvasStudent.student_id))
                )
            ).all()
            
            violations['orphaned_enrollments'] = [
                f"Enrollment {e.student_id}-{e.course_id} has invalid references"
                for e in orphaned_enrollments
            ]
            
            # Check for scores with invalid references
            orphaned_scores = self.session.query(AssignmentScore).filter(
                or_(
                    ~AssignmentScore.assignment_id.in_(select(CanvasAssignment.id)),
                    ~AssignmentScore.student_id.in_(select(CanvasStudent.student_id))
                )
            ).all()
            
            violations['orphaned_scores'] = [
                f"Score {s.id} references invalid assignment {s.assignment_id} or student {s.student_id}"
                for s in orphaned_scores
            ]
            
        except SQLAlchemyError as e:
            violations['invalid_references'].append(f"Validation query failed: {e}")
        
        return violations
    
    def repair_referential_integrity(
        self,
        violations: Optional[Dict[str, List[str]]] = None,
        delete_orphans: bool = False
    ) -> Dict[str, int]:
        """
        Repair referential integrity violations.
        
        Args:
            violations: Specific violations to repair (if None, will detect them)
            delete_orphans: Whether to delete orphaned records
            
        Returns:
            Dictionary with count of repairs performed
        """
        if violations is None:
            violations = self.validate_referential_integrity()
        
        repair_counts = {
            'assignments_removed': 0,
            'enrollments_removed': 0,
            'scores_removed': 0
        }
        
        if not delete_orphans:
            # Just return the violation counts without making changes
            return repair_counts
        
        try:
            # Remove orphaned assignments
            if violations['orphaned_assignments']:
                orphaned_assignments = self.session.query(CanvasAssignment).filter(
                    ~CanvasAssignment.course_id.in_(select(CanvasCourse.id))
                )
                repair_counts['assignments_removed'] = orphaned_assignments.count()
                orphaned_assignments.delete(synchronize_session=False)
            
            # Remove orphaned enrollments
            if violations['orphaned_enrollments']:
                orphaned_enrollments = self.session.query(CanvasEnrollment).filter(
                    or_(
                        ~CanvasEnrollment.course_id.in_(select(CanvasCourse.id)),
                        ~CanvasEnrollment.student_id.in_(select(CanvasStudent.student_id))
                    )
                )
                repair_counts['enrollments_removed'] = orphaned_enrollments.count()
                orphaned_enrollments.delete(synchronize_session=False)
            
            # Remove orphaned scores
            if violations['orphaned_scores']:
                orphaned_scores = self.session.query(AssignmentScore).filter(
                    or_(
                        ~AssignmentScore.assignment_id.in_(select(CanvasAssignment.id)),
                        ~AssignmentScore.student_id.in_(select(CanvasStudent.student_id))
                    )
                )
                repair_counts['scores_removed'] = orphaned_scores.count()
                orphaned_scores.delete(synchronize_session=False)
            
            self.session.flush()
            
        except SQLAlchemyError as e:
            raise CanvasOperationError(f"Failed to repair referential integrity: {e}")
        
        return repair_counts
    
    # ==================== OPTIMIZED RELATIONSHIP QUERIES ====================
    
    def get_enrollment_summary(self, course_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Get enrollment summary statistics.
        
        Args:
            course_id: Optional course ID to filter by
            
        Returns:
            Dictionary with enrollment statistics
        """
        query = self.session.query(CanvasEnrollment)
        
        if course_id:
            query = query.filter(CanvasEnrollment.course_id == course_id)
        
        total_enrollments = query.count()
        active_enrollments = query.filter(CanvasEnrollment.enrollment_status == 'active').count()
        inactive_enrollments = total_enrollments - active_enrollments
        
        # Get enrollment counts by course if not filtered
        course_breakdown = {}
        if not course_id:
            course_counts = self.session.query(
                CanvasCourse.name,
                func.count(CanvasEnrollment.student_id).label('count')
            ).join(
                CanvasEnrollment, CanvasCourse.id == CanvasEnrollment.course_id
            ).group_by(
                CanvasCourse.name
            ).all()
            
            course_breakdown = {course_name: count for course_name, count in course_counts}
        
        return {
            'total_enrollments': total_enrollments,
            'active_enrollments': active_enrollments,
            'inactive_enrollments': inactive_enrollments,
            'course_breakdown': course_breakdown
        }
    
    def get_student_course_performance(
        self,
        student_id: int,
        include_assignments: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Get student performance across all enrolled courses.
        
        Args:
            student_id: Canvas student ID
            include_assignments: Include detailed assignment data
            
        Returns:
            List of course performance data
        """
        # Get all enrollments for student
        enrollments = self.session.query(CanvasEnrollment).filter(
            CanvasEnrollment.student_id == student_id
        ).options(joinedload(CanvasEnrollment.course)).all()
        
        performance_data = []
        
        for enrollment in enrollments:
            course = enrollment.course
            
            # Get assignment scores for this course
            scores = self.session.query(AssignmentScore).join(
                CanvasAssignment, AssignmentScore.assignment_id == CanvasAssignment.id
            ).filter(
                and_(
                    AssignmentScore.student_id == student_id,
                    CanvasAssignment.course_id == course.id
                )
            ).all()
            
            # Calculate statistics
            total_assignments = self.session.query(CanvasAssignment).filter(
                CanvasAssignment.course_id == course.id
            ).count()
            
            completed_assignments = len([s for s in scores if s.score is not None])
            average_score = sum(s.score for s in scores if s.score is not None) / len(scores) if scores else 0
            
            course_data = {
                'course': course,
                'enrollment': enrollment,
                'total_assignments': total_assignments,
                'completed_assignments': completed_assignments,
                'average_score': average_score,
                'completion_rate': completed_assignments / total_assignments if total_assignments > 0 else 0
            }
            
            if include_assignments:
                course_data['assignment_scores'] = scores
            
            performance_data.append(course_data)
        
        return performance_data
    
    def find_relationship_conflicts(self) -> List[Dict[str, Any]]:
        """
        Find potential relationship conflicts that need resolution.
        
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        try:
            # Find students enrolled in the same course multiple times
            duplicate_enrollments = self.session.query(
                CanvasEnrollment.student_id,
                CanvasEnrollment.course_id,
                func.count().label('count')
            ).group_by(
                CanvasEnrollment.student_id,
                CanvasEnrollment.course_id
            ).having(func.count() > 1).all()
            
            for student_id, course_id, count in duplicate_enrollments:
                conflicts.append({
                    'type': 'duplicate_enrollment',
                    'student_id': student_id,
                    'course_id': course_id,
                    'count': count,
                    'description': f"Student {student_id} has {count} enrollments in course {course_id}"
                })
            
            # Find assignments with scores but no enrollment relationship
            orphaned_assignment_scores = self.session.query(AssignmentScore).filter(
                ~exists().where(
                    and_(
                        CanvasEnrollment.student_id == AssignmentScore.student_id,
                        CanvasEnrollment.course_id == CanvasAssignment.course_id,
                        CanvasAssignment.id == AssignmentScore.assignment_id
                    )
                )
            ).count()
            
            if orphaned_assignment_scores > 0:
                conflicts.append({
                    'type': 'orphaned_assignment_scores',
                    'count': orphaned_assignment_scores,
                    'description': f"Found {orphaned_assignment_scores} assignment scores without valid enrollment"
                })
            
        except SQLAlchemyError as e:
            conflicts.append({
                'type': 'detection_error',
                'description': f"Failed to detect conflicts: {e}"
            })
        
        return conflicts