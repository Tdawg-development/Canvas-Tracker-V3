"""
Query Builder Utilities for Canvas Tracker V3.

This module provides specialized query construction methods for Canvas models,
optimizing common queries and providing consistent patterns for complex joins
and filtering operations based on the actual database architecture.

The QueryBuilder class provides methods for:
- Student grade queries with performance optimization
- Course enrollment queries with relationship loading
- Assignment submission queries with aggregations
- Recent activity tracking across all layers
"""

from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from sqlalchemy import and_, or_, func, select, desc, asc, case, text, literal_column, String
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

# Import actual models from our Layer 1, 2, and 3 models
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)
from database.models.layer2_historical import (
    GradeHistory, AssignmentScore, CourseSnapshot
)
from database.models.layer3_metadata import (
    StudentMetadata, CourseMetadata, AssignmentMetadata
)


class QueryBuilder:
    """
    Centralized query builder for Canvas Tracker operations.
    
    Provides optimized query construction methods for common Canvas data
    retrieval patterns, with built-in performance optimization and
    relationship loading strategies.
    """
    
    def __init__(self, session: Session):
        """
        Initialize the query builder.
        
        Args:
            session: SQLAlchemy session for query execution
        """
        self.session = session
    
    def build_student_grades_query(
        self,
        student_id: Optional[int] = None,
        course_id: Optional[int] = None,
        assignment_ids: Optional[List[int]] = None,
        include_metadata: bool = False,
        include_history: bool = False,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Select:
        """
        Build optimized query for student grades with flexible filtering.
        
        Args:
            student_id: Filter by specific student ID
            course_id: Filter by specific course ID
            assignment_ids: Filter by specific assignment IDs
            include_metadata: Include Layer 3 metadata in results
            include_history: Include Layer 2 historical data
            date_range: Tuple of (start_date, end_date) for filtering
            
        Returns:
            SQLAlchemy Select query object
        """
        # Start with base grade query joining core Canvas entities
        query = select(
            CanvasStudent.student_id.label('student_id'),
            CanvasStudent.name.label('student_name'),
            CanvasCourse.id.label('course_id'),
            CanvasCourse.name.label('course_name'),
            CanvasAssignment.id.label('assignment_id'),
            CanvasAssignment.name.label('assignment_name'),
            CanvasAssignment.points_possible.label('points_possible'),
            AssignmentScore.score.label('current_score'),
            AssignmentScore.percentage.label('percentage_score'),
            AssignmentScore.submitted_at.label('submission_date'),
            AssignmentScore.submission_status.label('submission_status')
        ).select_from(
            CanvasStudent.__table__
            .join(CanvasEnrollment.__table__, CanvasStudent.student_id == CanvasEnrollment.student_id)
            .join(CanvasCourse.__table__, CanvasEnrollment.course_id == CanvasCourse.id)
            .join(CanvasAssignment.__table__, CanvasAssignment.course_id == CanvasCourse.id)
            .join(AssignmentScore.__table__, and_(
                AssignmentScore.student_id == CanvasStudent.student_id,
                AssignmentScore.assignment_id == CanvasAssignment.id
            ))
        )
        
        # Apply filtering conditions
        conditions = []
        
        if student_id:
            conditions.append(CanvasStudent.student_id == student_id)
        
        if course_id:
            conditions.append(CanvasCourse.id == course_id)
            
        if assignment_ids:
            conditions.append(CanvasAssignment.id.in_(assignment_ids))
            
        if date_range:
            start_date, end_date = date_range
            if start_date:
                conditions.append(AssignmentScore.submitted_at >= start_date)
            if end_date:
                conditions.append(AssignmentScore.submitted_at <= end_date)
        
        # Add enrollment status filtering
        conditions.append(
            CanvasEnrollment.enrollment_status == 'active'
        )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Add metadata if requested
        if include_metadata:
            query = query.add_columns(
                StudentMetadata.notes.label('student_notes'),
                StudentMetadata.custom_tags.label('student_tags'),
                AssignmentMetadata.notes.label('assignment_notes'),
                AssignmentMetadata.difficulty_rating.label('difficulty')
            ).outerjoin(
                StudentMetadata, StudentMetadata.student_id == CanvasStudent.student_id
            ).outerjoin(
                AssignmentMetadata, AssignmentMetadata.assignment_id == CanvasAssignment.id
            )
        
        # Add historical data if requested
        if include_history:
            query = query.add_columns(
                GradeHistory.previous_score.label('previous_score'),
                GradeHistory.score_change.label('grade_change'),
                GradeHistory.recorded_at.label('change_date')
            ).outerjoin(
                GradeHistory, and_(
                    GradeHistory.student_id == CanvasStudent.student_id,
                    GradeHistory.assignment_id == CanvasAssignment.id
                )
            )
        
        # Order by course, then assignment, then student for consistent results
        query = query.order_by(
            CanvasCourse.name,
            CanvasAssignment.module_position.asc().nullslast(),
            CanvasStudent.name
        )
        
        return query
    
    def build_course_enrollment_query(
        self,
        course_id: Optional[int] = None,
        student_id: Optional[int] = None,
        enrollment_status: Optional[str] = None,
        include_grades: bool = False,
        include_metadata: bool = False
    ) -> Select:
        """
        Build optimized query for course enrollments with grade summaries.
        
        Args:
            course_id: Filter by specific course ID
            student_id: Filter by specific student ID  
            enrollment_status: Filter by enrollment status ('active', 'inactive', etc.)
            include_grades: Include grade summary statistics
            include_metadata: Include Layer 3 metadata
            
        Returns:
            SQLAlchemy Select query object
        """
        # Base enrollment query
        query = select(
            CanvasCourse.id.label('course_id'),
            CanvasCourse.name.label('course_name'),
            CanvasCourse.course_code.label('course_code'),
            CanvasStudent.student_id.label('student_id'),
            CanvasStudent.name.label('student_name'),
            CanvasStudent.current_score.label('current_score'),
            CanvasStudent.final_score.label('final_score'),
            CanvasEnrollment.enrollment_status.label('enrollment_status'),
            CanvasEnrollment.enrollment_date.label('enrolled_at')
        ).select_from(
            CanvasEnrollment.__table__
            .join(CanvasCourse.__table__, CanvasEnrollment.course_id == CanvasCourse.id)
            .join(CanvasStudent.__table__, CanvasEnrollment.student_id == CanvasStudent.student_id)
        )
        
        # Apply filtering
        conditions = []
        
        if course_id:
            conditions.append(CanvasCourse.id == course_id)
            
        if student_id:
            conditions.append(CanvasStudent.student_id == student_id)
            
        if enrollment_status:
            conditions.append(CanvasEnrollment.enrollment_status == enrollment_status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Add grade summaries if requested
        if include_grades:
            # Subquery for assignment statistics
            assignment_stats = select(
                AssignmentScore.student_id,
                CanvasAssignment.course_id,
                func.avg(AssignmentScore.score).label('avg_score'),
                func.count(AssignmentScore.id).label('assignment_count'),
                func.sum(
                    case(
                        (AssignmentScore.submission_status == 'missing', 1),
                        else_=0
                    )
                ).label('missing_assignments'),
                func.sum(
                    case(
                        (AssignmentScore.submission_status == 'late', 1),
                        else_=0
                    )
                ).label('late_submissions')
            ).select_from(
                AssignmentScore.__table__.join(CanvasAssignment.__table__, AssignmentScore.assignment_id == CanvasAssignment.id)
            ).group_by(
                AssignmentScore.student_id,
                CanvasAssignment.course_id
            ).subquery()
            
            query = query.add_columns(
                assignment_stats.c.avg_score.label('average_score'),
                assignment_stats.c.assignment_count.label('total_assignments'),
                assignment_stats.c.missing_assignments.label('missing_count'),
                assignment_stats.c.late_submissions.label('late_count')
            ).outerjoin(
                assignment_stats, and_(
                    assignment_stats.c.student_id == CanvasStudent.student_id,
                    assignment_stats.c.course_id == CanvasCourse.id
                )
            )
        
        # Add metadata if requested
        if include_metadata:
            query = query.add_columns(
                StudentMetadata.notes.label('student_notes'),
                CourseMetadata.notes.label('course_notes'),
                StudentMetadata.custom_tags.label('student_tags'),
                CourseMetadata.custom_color.label('course_color'),
                CourseMetadata.tracking_enabled.label('course_tracked')
            ).outerjoin(
                StudentMetadata, StudentMetadata.student_id == CanvasStudent.student_id
            ).outerjoin(
                CourseMetadata, CourseMetadata.course_id == CanvasCourse.id
            )
        
        # Order by course name, then student name
        query = query.order_by(CanvasCourse.name, CanvasStudent.name)
        
        return query
    
    def build_assignment_submissions_query(
        self,
        assignment_id: Optional[int] = None,
        course_id: Optional[int] = None,
        submission_status: Optional[str] = None,
        include_late_submissions: bool = True,
        include_grade_history: bool = False,
        sort_by: str = 'submission_date'
    ) -> Select:
        """
        Build optimized query for assignment submissions with status tracking.
        
        Args:
            assignment_id: Filter by specific assignment ID
            course_id: Filter by specific course ID
            submission_status: Filter by submission status ('submitted', 'missing', 'late')
            include_late_submissions: Include late submission analysis
            include_grade_history: Include historical grade changes
            sort_by: Sort field ('submission_date', 'student_name', 'score')
            
        Returns:
            SQLAlchemy Select query object
        """
        # Base submissions query
        query = select(
            CanvasAssignment.id.label('assignment_id'),
            CanvasAssignment.name.label('assignment_name'),
            CanvasAssignment.points_possible.label('max_points'),
            CanvasCourse.id.label('course_id'),
            CanvasCourse.name.label('course_name'),
            CanvasStudent.student_id.label('student_id'),
            CanvasStudent.name.label('student_name'),
            AssignmentScore.id.label('submission_id'),
            AssignmentScore.score.label('score'),
            AssignmentScore.percentage.label('percentage'),
            AssignmentScore.submitted_at.label('submitted_at'),
            AssignmentScore.graded_at.label('graded_at'),
            AssignmentScore.submission_status.label('status')
        ).select_from(
            CanvasAssignment.__table__
            .join(CanvasCourse.__table__, CanvasAssignment.course_id == CanvasCourse.id)
            .join(AssignmentScore.__table__, AssignmentScore.assignment_id == CanvasAssignment.id)
            .join(CanvasStudent.__table__, AssignmentScore.student_id == CanvasStudent.student_id)
        )
        
        # Apply basic filtering (no active field exists in Canvas models)
        conditions = []
        
        if assignment_id:
            conditions.append(CanvasAssignment.id == assignment_id)
            
        if course_id:
            conditions.append(CanvasCourse.id == course_id)
            
        if submission_status:
            conditions.append(AssignmentScore.submission_status == submission_status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Add late submission analysis if requested
        if include_late_submissions:
            query = query.add_columns(
                case(
                    (AssignmentScore.submission_status == 'late', True),
                    else_=False
                ).label('is_late'),
                case(
                    (and_(
                        AssignmentScore.submitted_at.is_not(None),
                        AssignmentScore.due_at.is_not(None),
                        AssignmentScore.submitted_at > AssignmentScore.due_at
                    ), 
                    func.extract('epoch', AssignmentScore.submitted_at - AssignmentScore.due_at) / 3600),
                    else_=0
                ).label('hours_late')
            )
        
        # Add grade history if requested
        if include_grade_history:
            # Subquery for latest grade change
            latest_change = select(
                GradeHistory.assignment_id,
                GradeHistory.student_id,
                GradeHistory.previous_score,
                GradeHistory.score_change,
                func.max(GradeHistory.recorded_at).label('last_change')
            ).where(
                GradeHistory.assignment_id.is_not(None)
            ).group_by(
                GradeHistory.assignment_id,
                GradeHistory.student_id,
                GradeHistory.previous_score,
                GradeHistory.score_change
            ).subquery()
            
            query = query.add_columns(
                latest_change.c.previous_score.label('previous_score'),
                latest_change.c.score_change.label('grade_change'),
                latest_change.c.last_change.label('last_grade_change')
            ).outerjoin(
                latest_change, and_(
                    latest_change.c.assignment_id == CanvasAssignment.id,
                    latest_change.c.student_id == CanvasStudent.student_id
                )
            )
        
        # Apply sorting
        if sort_by == 'submission_date':
            query = query.order_by(AssignmentScore.submitted_at.desc().nullslast())
        elif sort_by == 'student_name':
            query = query.order_by(CanvasStudent.name)
        elif sort_by == 'score':
            query = query.order_by(AssignmentScore.score.desc().nullslast())
        else:
            # Default: assignment name, then student name
            query = query.order_by(
                CanvasAssignment.name,
                CanvasStudent.name
            )
        
        return query
    
    def build_recent_activity_query(
        self,
        hours: int = 24,
        activity_types: Optional[List[str]] = None,
        user_id: Optional[int] = None,
        course_id: Optional[int] = None,
        limit: int = 100
    ) -> Select:
        """
        Build query for recent activity across all layers.
        
        Args:
            hours: Number of hours to look back for activity
            activity_types: Filter by activity types ('grade', 'submission', 'note')
            user_id: Filter by specific user ID
            course_id: Filter by specific course ID
            limit: Maximum number of results to return
            
        Returns:
            SQLAlchemy Select query object
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Build union query for different activity types
        activities = []
        
        # Grade submissions/changes
        if not activity_types or 'grade' in activity_types:
            grade_activity = select(
                literal_column("'grade'").label('activity_type'),
                AssignmentScore.id.label('activity_id'),
                CanvasStudent.student_id.label('student_id'),
                CanvasStudent.name.label('student_name'),
                CanvasCourse.id.label('course_id'),
                CanvasCourse.name.label('course_name'),
                CanvasAssignment.name.label('item_name'),
                func.coalesce(
                    AssignmentScore.graded_at,
                    AssignmentScore.submitted_at,
                    AssignmentScore.recorded_at
                ).label('activity_time'),
                (func.coalesce(AssignmentScore.score, 0).cast(String) +
                 ' out of ' + 
                 CanvasAssignment.points_possible.cast(String) +
                 ' (' + AssignmentScore.submission_status + ')'
                ).label('activity_description')
            ).select_from(
                AssignmentScore.__table__
                .join(CanvasStudent.__table__, AssignmentScore.student_id == CanvasStudent.student_id)
                .join(CanvasAssignment.__table__, AssignmentScore.assignment_id == CanvasAssignment.id)
                .join(CanvasCourse.__table__, CanvasAssignment.course_id == CanvasCourse.id)
            ).where(
                and_(
                    or_(
                        AssignmentScore.submitted_at >= cutoff_time,
                        AssignmentScore.graded_at >= cutoff_time,
                        AssignmentScore.recorded_at >= cutoff_time
                    )
                )
            )
            activities.append(grade_activity)
        
        # Metadata updates (notes, tags)
        if not activity_types or 'note' in activity_types:
            note_activity = select(
                literal_column("'note'").label('activity_type'),
                StudentMetadata.student_id.label('activity_id'),
                StudentMetadata.student_id.label('student_id'),
                CanvasStudent.name.label('student_name'),
                literal_column('NULL').label('course_id'),
                literal_column("'Personal Notes'").label('course_name'),
                literal_column("'Student Note'").label('item_name'),
                StudentMetadata.updated_at.label('activity_time'),
                func.substr(StudentMetadata.notes, 1, 50).label('activity_description')
            ).select_from(
                StudentMetadata.__table__.join(CanvasStudent.__table__, StudentMetadata.student_id == CanvasStudent.student_id)
            ).where(
                and_(
                    StudentMetadata.updated_at >= cutoff_time,
                    StudentMetadata.notes.is_not(None)
                )
            )
            activities.append(note_activity)
        
        # Apply user and course filtering
        filtered_activities = []
        for activity in activities:
            conditions = []
            if user_id:
                conditions.append(activity.selected_columns.student_id == user_id)
            if course_id and hasattr(activity.selected_columns, 'course_id'):
                conditions.append(activity.selected_columns.course_id == course_id)
            
            if conditions:
                activity = activity.where(and_(*conditions))
            
            filtered_activities.append(activity)
        
        # Combine activities with UNION
        if len(filtered_activities) == 1:
            final_query = filtered_activities[0]
        else:
            final_query = filtered_activities[0]
            for activity in filtered_activities[1:]:
                final_query = final_query.union_all(activity)
        
        # Order by activity time and limit results
        final_query = final_query.order_by(desc('activity_time')).limit(limit)
        
        return final_query
    
    def build_performance_summary_query(
        self,
        course_id: Optional[int] = None,
        student_id: Optional[int] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None
    ) -> Select:
        """
        Build query for performance summary with grade statistics.
        
        Args:
            course_id: Filter by specific course ID
            student_id: Filter by specific student ID
            date_range: Tuple of (start_date, end_date) for filtering
            
        Returns:
            SQLAlchemy Select query object with performance metrics
        """
        # Base performance query with aggregations
        query = select(
            CanvasStudent.student_id.label('student_id'),
            CanvasStudent.name.label('student_name'),
            CanvasStudent.current_score.label('current_score'),
            CanvasStudent.final_score.label('final_score'),
            CanvasCourse.id.label('course_id'),
            CanvasCourse.name.label('course_name'),
            func.count(AssignmentScore.id).label('total_assignments'),
            func.count(
                case((AssignmentScore.score.is_not(None), 1))
            ).label('completed_assignments'),
            func.avg(
                case((AssignmentScore.score.is_not(None), AssignmentScore.score))
            ).label('average_score'),
            func.min(AssignmentScore.score).label('lowest_score'),
            func.max(AssignmentScore.score).label('highest_score'),
            func.sum(
                case((AssignmentScore.submission_status == 'late', 1), else_=0)
            ).label('late_submissions'),
            func.sum(
                case((AssignmentScore.submission_status == 'missing', 1), else_=0)
            ).label('missing_assignments')
        ).select_from(
            CanvasStudent.__table__
            .join(CanvasEnrollment.__table__, CanvasStudent.student_id == CanvasEnrollment.student_id)
            .join(CanvasCourse.__table__, CanvasEnrollment.course_id == CanvasCourse.id)
            .join(CanvasAssignment.__table__, CanvasAssignment.course_id == CanvasCourse.id)
            .join(AssignmentScore.__table__, and_(
                AssignmentScore.student_id == CanvasStudent.student_id,
                AssignmentScore.assignment_id == CanvasAssignment.id
            ))
        ).group_by(
            CanvasStudent.student_id,
            CanvasStudent.name,
            CanvasStudent.current_score,
            CanvasStudent.final_score,
            CanvasCourse.id,
            CanvasCourse.name
        )
        
        # Apply filtering - prefer Layer 0 lifecycle integration for enrollment filtering
        # Note: For full lifecycle awareness, consider using build_active_enrollments_query() instead
        conditions = [
            CanvasEnrollment.enrollment_status == 'active'  # Layer 1 Canvas status filtering
        ]
        
        if course_id:
            conditions.append(CanvasCourse.id == course_id)
            
        if student_id:
            conditions.append(CanvasStudent.student_id == student_id)
            
        if date_range:
            start_date, end_date = date_range
            if start_date:
                conditions.append(AssignmentScore.submitted_at >= start_date)
            if end_date:
                conditions.append(AssignmentScore.submitted_at <= end_date)
        
        query = query.where(and_(*conditions))
        
        # Order by course name, then average score descending
        query = query.order_by(
            CanvasCourse.name,
            desc('average_score')
        )
        
        return query
    
    def build_active_objects_query(
        self, 
        object_type: str, 
        include_inactive: bool = False,
        include_pending_deletion: bool = False
    ) -> Select:
        """
        Build query that respects Layer 0 object lifecycle status.
        
        This method joins Canvas data (Layer 1) with object lifecycle tracking (Layer 0)
        to ensure queries only return objects that should be visible based on their
        lifecycle status.
        
        Args:
            object_type: Type of objects ('student', 'course', 'assignment')
            include_inactive: Include objects marked as inactive
            include_pending_deletion: Include objects pending user deletion approval
            
        Returns:
            SQLAlchemy Select query with lifecycle-aware filtering
        """
        from database.models.layer0_lifecycle import ObjectStatus
        
        # Map object types to their corresponding Canvas models
        model_mapping = {
            'student': (CanvasStudent, 'student_id'),
            'course': (CanvasCourse, 'id'), 
            'assignment': (CanvasAssignment, 'id')
        }
        
        if object_type not in model_mapping:
            raise ValueError(f"Unsupported object_type: {object_type}. Must be one of {list(model_mapping.keys())}")
            
        canvas_model, id_field = model_mapping[object_type]
        
        # Build base query joining Canvas model with ObjectStatus
        query = select(
            canvas_model,
            ObjectStatus.active.label('lifecycle_active'),
            ObjectStatus.pending_deletion.label('lifecycle_pending_deletion'),
            ObjectStatus.removed_date.label('lifecycle_removed_date'),
            ObjectStatus.last_seen_sync.label('lifecycle_last_seen')
        ).select_from(
            canvas_model.__table__.join(
                ObjectStatus.__table__,
                and_(
                    ObjectStatus.object_type == object_type,
                    ObjectStatus.object_id == getattr(canvas_model, id_field)
                )
            )
        )
        
        # Apply lifecycle filtering
        conditions = []
        
        if not include_inactive and not include_pending_deletion:
            # Default: Only active objects that aren't pending deletion
            conditions.append(ObjectStatus.active == True)
            conditions.append(ObjectStatus.pending_deletion == False)
        elif not include_inactive:
            # Include pending deletion but not inactive
            conditions.append(ObjectStatus.active == True)
        elif not include_pending_deletion:
            # Include inactive but not pending deletion  
            conditions.append(ObjectStatus.pending_deletion == False)
        # If both flags are True, include all objects (no additional filtering)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def build_active_enrollments_query(
        self,
        include_inactive: bool = False,
        include_pending_deletion: bool = False,
        student_id: Optional[int] = None,
        course_id: Optional[int] = None
    ) -> Select:
        """
        Build enrollment query respecting Layer 0 EnrollmentStatus lifecycle.
        
        This method joins Canvas enrollment data with enrollment lifecycle tracking
        to ensure queries only return enrollments that should be visible.
        
        Args:
            include_inactive: Include enrollments marked as inactive
            include_pending_deletion: Include enrollments pending deletion
            student_id: Filter by specific student ID
            course_id: Filter by specific course ID
            
        Returns:
            SQLAlchemy Select query with enrollment lifecycle awareness
        """
        from database.models.layer0_lifecycle import EnrollmentStatus
        
        # Build base query joining Canvas data with EnrollmentStatus
        query = select(
            CanvasEnrollment.student_id,
            CanvasEnrollment.course_id,
            CanvasEnrollment.enrollment_date,
            CanvasEnrollment.enrollment_status.label('canvas_enrollment_status'),
            CanvasStudent.name.label('student_name'),
            CanvasCourse.name.label('course_name'),
            CanvasCourse.course_code,
            EnrollmentStatus.active.label('lifecycle_active'),
            EnrollmentStatus.pending_deletion.label('lifecycle_pending_deletion'),
            EnrollmentStatus.removed_date.label('lifecycle_removed_date'),
            EnrollmentStatus.last_seen_sync.label('lifecycle_last_seen')
        ).select_from(
            CanvasEnrollment.__table__
            .join(CanvasStudent.__table__, CanvasEnrollment.student_id == CanvasStudent.student_id)
            .join(CanvasCourse.__table__, CanvasEnrollment.course_id == CanvasCourse.id)
            .join(
                EnrollmentStatus.__table__,
                and_(
                    EnrollmentStatus.student_id == CanvasEnrollment.student_id,
                    EnrollmentStatus.course_id == CanvasEnrollment.course_id
                )
            )
        )
        
        # Apply lifecycle filtering
        conditions = []
        
        if not include_inactive and not include_pending_deletion:
            # Default: Only active enrollments that aren't pending deletion
            conditions.append(EnrollmentStatus.active == True)
            conditions.append(EnrollmentStatus.pending_deletion == False)
        elif not include_inactive:
            # Include pending deletion but not inactive
            conditions.append(EnrollmentStatus.active == True)
        elif not include_pending_deletion:
            # Include inactive but not pending deletion
            conditions.append(EnrollmentStatus.pending_deletion == False)
        
        # Apply optional filters
        if student_id:
            conditions.append(CanvasEnrollment.student_id == student_id)
        if course_id:
            conditions.append(CanvasEnrollment.course_id == course_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        return query
    
    def build_pending_deletion_review_query(self, object_type: Optional[str] = None) -> Select:
        """
        Build query for objects requiring user review for deletion.
        
        Returns objects that have been removed from Canvas but have dependencies
        (user data or historical data) that require user approval before deletion.
        
        Args:
            object_type: Filter by specific object type ('student', 'course', 'assignment')
            
        Returns:
            SQLAlchemy Select query for pending deletion review
        """
        from database.models.layer0_lifecycle import ObjectStatus
        
        # Base query for pending deletions
        query = select(
            ObjectStatus.object_type,
            ObjectStatus.object_id,
            ObjectStatus.removed_date,
            ObjectStatus.removal_reason,
            ObjectStatus.user_data_exists,
            ObjectStatus.historical_data_exists,
            ObjectStatus.last_seen_sync
        ).select_from(ObjectStatus.__table__)
        
        # Filter for pending deletions
        conditions = [ObjectStatus.pending_deletion == True]
        
        if object_type:
            conditions.append(ObjectStatus.object_type == object_type)
        
        query = query.where(and_(*conditions))
        
        # Order by removal date (most recent first)
        query = query.order_by(ObjectStatus.removed_date.desc())
        
        return query


# Utility functions for common query operations
def optimize_query_performance(query: Select) -> Select:
    """
    Apply performance optimizations to a query.
    
    Args:
        query: SQLAlchemy Select query to optimize
        
    Returns:
        Optimized Select query
    """
    return query.execution_options(
        autoflush=False
    )


def add_pagination(query: Select, page: int = 1, per_page: int = 50) -> Select:
    """
    Add pagination to a query.
    
    Args:
        query: SQLAlchemy Select query
        page: Page number (1-based)
        per_page: Number of items per page
        
    Returns:
        Query with pagination applied
    """
    offset = (page - 1) * per_page
    return query.offset(offset).limit(per_page)


def add_active_filter(query: Select, model_classes: List) -> Select:
    """
    Add active=True filters for Layer 0 lifecycle model classes only.
    
    Layer 1 Canvas models don't have 'active' fields - lifecycle management
    is handled by Layer 0 ObjectStatus and EnrollmentStatus tables.
    
    Args:
        query: SQLAlchemy Select query
        model_classes: List of model classes to filter
        
    Returns:
        Query with active filters applied (only for Layer 0 models)
    """
    from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
    
    conditions = []
    lifecycle_models = {ObjectStatus, EnrollmentStatus}
    
    for model_class in model_classes:
        if model_class in lifecycle_models and hasattr(model_class, 'active'):
            conditions.append(model_class.active == True)
    
    if conditions:
        query = query.where(and_(*conditions))
    
    return query
