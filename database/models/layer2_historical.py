"""
Layer 2: Historical Data Models

These models store historical snapshots and change tracking data that accumulates
over time during sync operations. They provide append-only historical records
that are never modified, only added to.

Key Characteristics:
- Append-only data (records are never updated or deleted)
- Track changes in Canvas data over time
- Maintain historical snapshots for trend analysis
- Reference Layer 1 Canvas objects but exist independently
- Enable rollback and audit trail functionality
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship

from ..base import BaseModel, HistoricalBaseModel


class GradeHistory(HistoricalBaseModel):
    """
    Historical record of student grade changes over time.
    
    Tracks grade progression for students across assignments and courses.
    Each record represents a snapshot of grades at a specific sync time,
    enabling trend analysis and grade change tracking.
    """
    
    __tablename__ = 'grade_history'
    
    # References to Layer 1 Canvas objects (these may no longer exist)
    student_id = Column(Integer, nullable=False, index=True)       # Canvas student ID
    course_id = Column(Integer, nullable=False, index=True)        # Canvas course ID  
    assignment_id = Column(Integer, nullable=True, index=True)     # Canvas assignment ID (null for course grades)
    
    # Grade information at time of recording
    current_score = Column(Integer, nullable=True)                 # Student's current score (percentage)
    final_score = Column(Integer, nullable=True)                   # Student's potential final score (percentage)
    points_earned = Column(Float, nullable=True)                   # Actual points earned on assignment
    points_possible = Column(Float, nullable=True)                 # Total points possible for assignment
    
    # Grade context and metadata
    grade_type = Column(String(50), nullable=False, default='assignment')  # 'assignment', 'course_current', 'course_final'
    submission_status = Column(String(50), nullable=True)          # 'submitted', 'missing', 'late', etc.
    
    # Change detection
    previous_score = Column(Integer, nullable=True)                # Previous score for change detection
    score_change = Column(Integer, nullable=True)                  # Change since last sync (positive/negative)
    
    def __repr__(self):
        """String representation showing student, assignment, and grade info."""
        if self.assignment_id:
            return f"<GradeHistory(student:{self.student_id}, assignment:{self.assignment_id}, score:{self.current_score}, {self.recorded_at})>"
        else:
            return f"<GradeHistory(student:{self.student_id}, course:{self.course_id}, {self.grade_type}:{self.current_score}, {self.recorded_at})>"
    
    def calculate_score_change(self, previous_grade_record=None):
        """
        Calculate score change from previous record.
        
        Args:
            previous_grade_record: Previous GradeHistory record for comparison
            
        Returns:
            int: Score change (positive for improvement, negative for decline)
        """
        if not previous_grade_record or not previous_grade_record.current_score:
            return None
            
        if self.current_score is None:
            return None
            
        return self.current_score - previous_grade_record.current_score
    
    def is_improvement(self):
        """Check if this grade represents an improvement."""
        return self.score_change is not None and self.score_change > 0
    
    def is_decline(self):
        """Check if this grade represents a decline."""
        return self.score_change is not None and self.score_change < 0
    
    @classmethod
    def get_student_grade_history(cls, session, student_id, course_id=None, assignment_id=None, limit=None):
        """
        Get grade history for a student.
        
        Args:
            session: Database session
            student_id: Canvas student ID
            course_id: Filter by specific course (optional)
            assignment_id: Filter by specific assignment (optional)  
            limit: Maximum number of records to return
            
        Returns:
            List of GradeHistory records ordered by recorded_at desc
        """
        query = session.query(cls).filter(cls.student_id == student_id)
        
        if course_id:
            query = query.filter(cls.course_id == course_id)
        if assignment_id:
            query = query.filter(cls.assignment_id == assignment_id)
            
        query = query.order_by(cls.recorded_at.desc())
        
        if limit:
            query = query.limit(limit)
            
        return query.all()
    
    @classmethod
    def get_grade_trends(cls, session, student_id, course_id, days_back=30):
        """
        Get grade trends for a student in a course over time.
        
        Args:
            session: Database session
            student_id: Canvas student ID
            course_id: Canvas course ID
            days_back: Number of days of history to analyze
            
        Returns:
            List of GradeHistory records for trend analysis
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        return session.query(cls).filter(
            cls.student_id == student_id,
            cls.course_id == course_id,
            cls.recorded_at >= cutoff_date
        ).order_by(cls.recorded_at.asc()).all()


class AssignmentScore(HistoricalBaseModel):
    """
    Historical record of individual assignment score changes.
    
    Tracks detailed assignment-level scoring including submission status,
    due dates, and grading changes over time. More granular than GradeHistory
    for assignment-specific analysis.
    """
    
    __tablename__ = 'assignment_scores'
    
    # References to Layer 1 Canvas objects
    student_id = Column(Integer, nullable=False, index=True)        # Canvas student ID
    course_id = Column(Integer, nullable=False, index=True)         # Canvas course ID
    assignment_id = Column(Integer, nullable=False, index=True)     # Canvas assignment ID
    
    # Score details
    score = Column(Float, nullable=True)                            # Points earned on assignment  
    points_possible = Column(Float, nullable=True)                  # Total points possible
    percentage = Column(Integer, nullable=True)                     # Score as percentage (0-100)
    
    # Assignment submission details
    submitted_at = Column(DateTime, nullable=True)                  # When assignment was submitted
    due_at = Column(DateTime, nullable=True)                        # Assignment due date
    submission_status = Column(String(50), nullable=False, default='missing')  # 'submitted', 'missing', 'late', 'on_time'
    
    # Grading information
    graded_at = Column(DateTime, nullable=True)                     # When assignment was graded
    grade_changed = Column(Boolean, nullable=False, default=False)  # Whether grade changed this sync
    
    # Change tracking
    previous_score = Column(Float, nullable=True)                   # Previous score for change detection
    score_change = Column(Float, nullable=True)                     # Change in points since last sync
    
    # Submission metadata
    submission_type = Column(String(50), nullable=True)             # 'online_text_entry', 'online_upload', etc.
    attempt_number = Column(Integer, nullable=True)                 # Submission attempt number
    
    def __repr__(self):
        """String representation showing assignment score details."""
        status = f"({self.submission_status})" if self.submission_status != 'submitted' else ""
        return f"<AssignmentScore(student:{self.student_id}, assignment:{self.assignment_id}, score:{self.score}/{self.points_possible} {status}, {self.recorded_at})>"
    
    def calculate_percentage(self):
        """Calculate percentage score if not already stored."""
        if self.score is None or self.points_possible is None or self.points_possible == 0:
            return None
        return round((self.score / self.points_possible) * 100)
    
    def is_late_submission(self):
        """Check if assignment was submitted after due date."""
        if not self.submitted_at or not self.due_at:
            return False
        return self.submitted_at > self.due_at
    
    def is_missing_assignment(self):
        """Check if assignment is missing/not submitted."""
        return self.submission_status == 'missing'
    
    def days_late(self):
        """Calculate how many days late the submission was."""
        if not self.is_late_submission():
            return 0
        return (self.submitted_at - self.due_at).days
    
    @classmethod
    def get_assignment_scores(cls, session, assignment_id, student_id=None):
        """
        Get all historical scores for an assignment.
        
        Args:
            session: Database session
            assignment_id: Canvas assignment ID
            student_id: Filter by specific student (optional)
            
        Returns:
            List of AssignmentScore records ordered by recorded_at desc
        """
        query = session.query(cls).filter(cls.assignment_id == assignment_id)
        
        if student_id:
            query = query.filter(cls.student_id == student_id)
            
        return query.order_by(cls.recorded_at.desc()).all()
    
    @classmethod
    def get_recent_score_changes(cls, session, student_id=None, days_back=7):
        """
        Get recent assignment score changes.
        
        Args:
            session: Database session
            student_id: Filter by specific student (optional)
            days_back: Number of days to look back for changes
            
        Returns:
            List of AssignmentScore records with recent changes
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        query = session.query(cls).filter(
            cls.recorded_at >= cutoff_date,
            cls.grade_changed == True
        )
        
        if student_id:
            query = query.filter(cls.student_id == student_id)
            
        return query.order_by(cls.recorded_at.desc()).all()
    
    @classmethod  
    def get_missing_assignments(cls, session, student_id, course_id=None):
        """
        Get missing assignments for a student.
        
        Args:
            session: Database session
            student_id: Canvas student ID
            course_id: Filter by specific course (optional)
            
        Returns:
            List of AssignmentScore records for missing assignments
        """
        query = session.query(cls).filter(
            cls.student_id == student_id,
            cls.submission_status == 'missing'
        )
        
        if course_id:
            query = query.filter(cls.course_id == course_id)
            
        return query.order_by(cls.due_at.desc()).all()


class CourseSnapshot(HistoricalBaseModel):
    """
    Historical snapshot of course-level statistics and metrics.
    
    Captures course-wide data at sync time including enrollment counts,
    assignment statistics, and grade distributions. Enables tracking
    course progress and changes over time.
    """
    
    __tablename__ = 'course_snapshots'
    
    # Course reference
    course_id = Column(Integer, nullable=False, index=True)          # Canvas course ID
    
    # Enrollment statistics
    total_students = Column(Integer, nullable=False, default=0)      # Total enrolled students
    active_students = Column(Integer, nullable=False, default=0)     # Currently active students  
    
    # Assignment statistics
    total_assignments = Column(Integer, nullable=False, default=0)   # Total assignments in course
    published_assignments = Column(Integer, nullable=False, default=0)  # Published assignments
    graded_assignments = Column(Integer, nullable=False, default=0)  # Assignments with grades
    
    # Grade distribution
    average_score = Column(Float, nullable=True)                     # Course average score
    median_score = Column(Float, nullable=True)                      # Course median score
    passing_rate = Column(Float, nullable=True)                      # Percentage of passing students
    
    # Activity metrics
    recent_submissions = Column(Integer, nullable=False, default=0)  # Submissions in last 7 days
    pending_grading = Column(Integer, nullable=False, default=0)     # Ungraded submissions
    
    # Sync metadata
    sync_duration = Column(Float, nullable=True)                     # How long sync took (seconds)
    objects_synced = Column(Integer, nullable=True)                  # Number of objects synced
    
    def __repr__(self):
        """String representation showing course snapshot summary."""
        return f"<CourseSnapshot(course:{self.course_id}, students:{self.active_students}, avg:{self.average_score}, {self.recorded_at})>"
    
    def calculate_completion_rate(self):
        """Calculate assignment completion rate."""
        if self.total_assignments == 0:
            return 0.0
        return (self.graded_assignments / self.total_assignments) * 100
    
    def is_healthy_course(self):
        """Basic health check for course activity."""
        return (
            self.active_students > 0 and
            self.recent_submissions > 0 and
            self.average_score is not None and
            self.average_score > 50  # Basic passing threshold
        )
    
    @classmethod
    def get_course_history(cls, session, course_id, limit=30):
        """
        Get historical snapshots for a course.
        
        Args:
            session: Database session
            course_id: Canvas course ID
            limit: Maximum number of snapshots to return
            
        Returns:
            List of CourseSnapshot records ordered by recorded_at desc
        """
        return session.query(cls).filter(
            cls.course_id == course_id
        ).order_by(cls.recorded_at.desc()).limit(limit).all()
    
    @classmethod
    def get_trend_data(cls, session, course_id, days_back=30):
        """
        Get trend data for course metrics.
        
        Args:
            session: Database session
            course_id: Canvas course ID
            days_back: Number of days of history to analyze
            
        Returns:
            List of CourseSnapshot records for trend analysis
        """
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
        return session.query(cls).filter(
            cls.course_id == course_id,
            cls.recorded_at >= cutoff_date
        ).order_by(cls.recorded_at.asc()).all()