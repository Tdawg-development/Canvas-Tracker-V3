"""
Layer 0: Object Lifecycle Management Models

These models track the existence and status of Canvas objects across sync operations.
They enable soft-delete functionality and handle removal detection without interfering 
with Canvas sync processes.

Key Characteristics:
- Track object lifecycle independently from Canvas data (Layer 1)
- Enable soft-delete with user approval workflows
- Handle object reactivation when Canvas objects return
- Separate tracking for individual objects and enrollment relationships
- Never interfere with Canvas sync operations (Layer 1)
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship

from ..base import BaseModel, TimestampMixin


class ObjectStatus(BaseModel):
    """
    Track lifecycle status of individual Canvas objects across sync operations.
    
    This model provides soft-delete functionality by tracking when Canvas objects
    exist or have been removed from Canvas, without interfering with Layer 1
    Canvas data operations.
    
    Supports objects: courses, students, assignments
    """
    
    __tablename__ = 'object_status'
    
    # Object identification
    object_type = Column(String(50), nullable=False)  # 'course', 'student', 'assignment'  
    object_id = Column(Integer, nullable=False)       # Canvas ID of the object
    
    # Lifecycle status
    active = Column(Boolean, nullable=False, default=True)              # Currently exists in Canvas
    pending_deletion = Column(Boolean, nullable=False, default=False)   # Awaiting user deletion approval
    removed_date = Column(DateTime, nullable=True)                      # When object disappeared from Canvas
    last_seen_sync = Column(DateTime, nullable=True)                    # Last sync where object was present
    
    # Optional metadata about removal
    removal_reason = Column(String(255), nullable=True)                 # Why object was marked for removal
    user_data_exists = Column(Boolean, nullable=False, default=False)   # Has associated user metadata
    historical_data_exists = Column(Boolean, nullable=False, default=False)  # Has historical data
    
    def __init__(self, **kwargs):
        """Initialize ObjectStatus with proper boolean defaults."""
        # Set defaults for boolean fields if not provided
        if 'active' not in kwargs:
            kwargs['active'] = True
        if 'pending_deletion' not in kwargs:
            kwargs['pending_deletion'] = False
        if 'user_data_exists' not in kwargs:
            kwargs['user_data_exists'] = False
        if 'historical_data_exists' not in kwargs:
            kwargs['historical_data_exists'] = False
        
        super().__init__(**kwargs)
    
    # Composite unique constraint on object_type + object_id
    __table_args__ = (
        {'sqlite_autoincrement': True},  # For SQLite compatibility
    )
    
    def __repr__(self):
        """String representation showing object identification and status."""
        status = "active" if self.active else "inactive"
        pending = " (pending deletion)" if self.pending_deletion else ""
        return f"<ObjectStatus({self.object_type}:{self.object_id}, {status}{pending})>"
    
    def mark_active(self, sync_timestamp=None):
        """
        Mark object as active and present in Canvas.
        
        Args:
            sync_timestamp (datetime, optional): Timestamp of sync. Defaults to now.
        """
        if sync_timestamp is None:
            sync_timestamp = datetime.now(timezone.utc)
            
        self.active = True
        self.pending_deletion = False
        self.last_seen_sync = sync_timestamp
        self.removed_date = None
        self.removal_reason = None
    
    def mark_removed(self, sync_timestamp=None, reason=None):
        """
        Mark object as removed from Canvas.
        
        If object has dependencies (user data or historical data), it will be
        marked for pending deletion requiring user approval.
        
        Args:
            sync_timestamp (datetime, optional): Timestamp of sync. Defaults to now.
            reason (str, optional): Reason for removal
        """
        if sync_timestamp is None:
            sync_timestamp = datetime.now(timezone.utc)
            
        self.removed_date = sync_timestamp
        self.removal_reason = reason
        
        # If object has dependencies, mark as pending deletion instead of inactive
        if self.has_dependencies():
            self.pending_deletion = True
            self.active = True  # Keep active until user confirms deletion
        else:
            self.active = False
            self.pending_deletion = False
    
    def mark_for_deletion(self, reason=None):
        """
        Manually mark object for deletion (user-initiated).
        
        Args:
            reason (str, optional): Reason for deletion request
        """
        self.pending_deletion = True
        if reason:
            self.removal_reason = reason
    
    def approve_deletion(self):
        """
        Approve pending deletion and mark object as inactive.
        
        This should trigger cleanup of associated data.
        """
        self.active = False
        self.pending_deletion = False
        if not self.removed_date:
            self.removed_date = datetime.now(timezone.utc)
    
    def cancel_deletion(self):
        """Cancel pending deletion and keep object active."""
        self.pending_deletion = False
        self.removal_reason = None
    
    def has_dependencies(self):
        """
        Check if object has dependencies that prevent automatic deletion.
        
        Returns:
            bool: True if object has user data or historical data
        """
        return self.user_data_exists or self.historical_data_exists
    
    def update_dependency_status(self, has_user_data=None, has_historical_data=None):
        """
        Update the dependency status flags.
        
        Args:
            has_user_data (bool, optional): Whether object has user metadata
            has_historical_data (bool, optional): Whether object has historical data
        """
        if has_user_data is not None:
            self.user_data_exists = has_user_data
        if has_historical_data is not None:
            self.historical_data_exists = has_historical_data
    
    def is_removal_candidate(self, days_threshold=30):
        """
        Check if object is a candidate for removal based on inactivity.
        
        Args:
            days_threshold (int): Number of days of inactivity before removal candidate
            
        Returns:
            bool: True if object hasn't been seen for longer than threshold
        """
        if self.active or not self.removed_date:
            return False
            
        now = datetime.now(timezone.utc)
        days_inactive = (now - self.removed_date).days
        return days_inactive >= days_threshold
    
    @classmethod
    def get_objects_by_type(cls, session, object_type, active_only=True):
        """
        Get all objects of a specific type.
        
        Args:
            session: Database session
            object_type (str): Type of objects to retrieve
            active_only (bool): Whether to return only active objects
            
        Returns:
            list: List of ObjectStatus records
        """
        query = session.query(cls).filter(cls.object_type == object_type)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()
    
    @classmethod
    def get_pending_deletions(cls, session, object_type=None):
        """
        Get objects pending deletion approval.
        
        Args:
            session: Database session  
            object_type (str, optional): Filter by specific object type
            
        Returns:
            list: List of ObjectStatus records pending deletion
        """
        query = session.query(cls).filter(cls.pending_deletion == True)
        if object_type:
            query = query.filter(cls.object_type == object_type)
        return query.order_by(cls.removed_date.desc()).all()


class EnrollmentStatus(BaseModel):
    """
    Track lifecycle status of student-course enrollment relationships.
    
    Separate from ObjectStatus because enrollments are relationships between
    objects rather than objects themselves, and have different lifecycle patterns.
    """
    
    __tablename__ = 'enrollment_status'
    
    # Enrollment identification (matches CanvasEnrollment composite key)
    student_id = Column(Integer, nullable=False)       # Canvas student ID
    course_id = Column(Integer, nullable=False)        # Canvas course ID
    
    # Lifecycle status
    active = Column(Boolean, nullable=False, default=True)              # Currently exists in Canvas
    pending_deletion = Column(Boolean, nullable=False, default=False)   # Awaiting user deletion approval
    removed_date = Column(DateTime, nullable=True)                      # When enrollment disappeared from Canvas
    last_seen_sync = Column(DateTime, nullable=True)                    # Last sync where enrollment was present
    
    # Enrollment-specific metadata
    removal_reason = Column(String(255), nullable=True)                 # Why enrollment was removed
    historical_data_exists = Column(Boolean, nullable=False, default=False)  # Has grade history data
    
    def __init__(self, **kwargs):
        """Initialize EnrollmentStatus with proper boolean defaults."""
        # Set defaults for boolean fields if not provided
        if 'active' not in kwargs:
            kwargs['active'] = True
        if 'pending_deletion' not in kwargs:
            kwargs['pending_deletion'] = False
        if 'historical_data_exists' not in kwargs:
            kwargs['historical_data_exists'] = False
        
        super().__init__(**kwargs)
    
    # Composite unique constraint on student_id + course_id  
    __table_args__ = (
        {'sqlite_autoincrement': True},  # For SQLite compatibility
    )
    
    def __repr__(self):
        """String representation showing enrollment identification and status."""
        status = "active" if self.active else "inactive"
        pending = " (pending deletion)" if self.pending_deletion else ""
        return f"<EnrollmentStatus(student:{self.student_id}, course:{self.course_id}, {status}{pending})>"
    
    def mark_active(self, sync_timestamp=None):
        """
        Mark enrollment as active and present in Canvas.
        
        Args:
            sync_timestamp (datetime, optional): Timestamp of sync. Defaults to now.
        """
        if sync_timestamp is None:
            sync_timestamp = datetime.now(timezone.utc)
            
        self.active = True
        self.pending_deletion = False
        self.last_seen_sync = sync_timestamp
        self.removed_date = None
        self.removal_reason = None
    
    def mark_removed(self, sync_timestamp=None, reason=None):
        """
        Mark enrollment as removed from Canvas.
        
        Args:
            sync_timestamp (datetime, optional): Timestamp of sync. Defaults to now.
            reason (str, optional): Reason for removal
        """
        if sync_timestamp is None:
            sync_timestamp = datetime.now(timezone.utc)
            
        self.removed_date = sync_timestamp
        self.removal_reason = reason
        
        # If enrollment has historical data, mark as pending deletion
        if self.historical_data_exists:
            self.pending_deletion = True
            self.active = True  # Keep active until user confirms deletion
        else:
            self.active = False
            self.pending_deletion = False
    
    def mark_for_deletion(self, reason=None):
        """
        Manually mark enrollment for deletion.
        
        Args:
            reason (str, optional): Reason for deletion request
        """
        self.pending_deletion = True
        if reason:
            self.removal_reason = reason
    
    def approve_deletion(self):
        """Approve pending deletion and mark enrollment as inactive."""
        self.active = False
        self.pending_deletion = False
        if not self.removed_date:
            self.removed_date = datetime.now(timezone.utc)
    
    def cancel_deletion(self):
        """Cancel pending deletion and keep enrollment active."""
        self.pending_deletion = False
        self.removal_reason = None
    
    def has_dependencies(self):
        """
        Check if enrollment has dependencies that prevent automatic deletion.
        
        Returns:
            bool: True if enrollment has historical data
        """
        return self.historical_data_exists
    
    def update_dependency_status(self, has_historical_data=None):
        """
        Update the historical data dependency flag.
        
        Args:
            has_historical_data (bool, optional): Whether enrollment has grade history
        """
        if has_historical_data is not None:
            self.historical_data_exists = has_historical_data
    
    @classmethod
    def get_student_enrollments(cls, session, student_id, active_only=True):
        """
        Get all enrollment statuses for a specific student.
        
        Args:
            session: Database session
            student_id (int): Canvas student ID
            active_only (bool): Whether to return only active enrollments
            
        Returns:
            list: List of EnrollmentStatus records
        """
        query = session.query(cls).filter(cls.student_id == student_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()
    
    @classmethod
    def get_course_enrollments(cls, session, course_id, active_only=True):
        """
        Get all enrollment statuses for a specific course.
        
        Args:
            session: Database session
            course_id (int): Canvas course ID
            active_only (bool): Whether to return only active enrollments
            
        Returns:
            list: List of EnrollmentStatus records
        """
        query = session.query(cls).filter(cls.course_id == course_id)
        if active_only:
            query = query.filter(cls.active == True)
        return query.all()
    
    @classmethod
    def get_pending_deletions(cls, session, student_id=None, course_id=None):
        """
        Get enrollments pending deletion approval.
        
        Args:
            session: Database session
            student_id (int, optional): Filter by specific student
            course_id (int, optional): Filter by specific course
            
        Returns:
            list: List of EnrollmentStatus records pending deletion
        """
        query = session.query(cls).filter(cls.pending_deletion == True)
        if student_id:
            query = query.filter(cls.student_id == student_id)
        if course_id:
            query = query.filter(cls.course_id == course_id)
        return query.order_by(cls.removed_date.desc()).all()