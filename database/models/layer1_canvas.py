"""
Layer 1: Canvas Data Models

These models represent pure Canvas data that gets completely replaced during 
full sync operations. They contain exactly what Canvas provides via the
CanvasDataConstructor, with no lifecycle tracking mixed in.

Data Sources (from Canvas-Data-Object-Tree.md):
- CanvasCourseStaging -> CanvasCourse 
- CanvasStudentStaging -> CanvasStudent
- CanvasAssignmentStaging -> CanvasAssignment  
- Enrollment relationships -> CanvasEnrollment

Key Characteristics:
- Completely replaced during full sync operations
- No lifecycle tracking mixed in (that's handled by Layer 0)
- Contains Canvas data exactly as provided by CanvasDataConstructor API
- Includes sync tracking (last_synced) but not object lifecycle
"""

from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship

from ..base import CanvasEntityModel, CanvasRelationshipModel, CommonColumns


class CanvasCourse(CanvasEntityModel):
    """
    Canvas course data model.
    
    Maps from CanvasCourseStaging object to database table.
    Contains core course information and calculated statistics.
    """
    
    __tablename__ = 'canvas_courses'
    
    # Canvas course ID as primary key (from CanvasCourseStaging.id)
    id = Column(Integer, primary_key=True)  # Canvas course ID
    
    # Basic course information (from CanvasCourseStaging)
    # name is provided by CanvasBaseModel via CanvasObjectMixin
    course_code = Column(String(100), nullable=True)  # from CanvasCourseStaging.course_code
    calendar_ics = Column(Text, nullable=True)         # from CanvasCourseStaging.calendar.ics
    
    # Canvas timestamps
    created_at = Column(DateTime, nullable=True)       # from CanvasCourseStaging.created_at
    
    # Course statistics (from CourseSummary - calculated during sync)
    total_students = Column(Float, nullable=True)        # from CourseSummary.students_count
    total_modules = Column(Float, nullable=True)         # from CourseSummary.modules_count
    total_assignments = Column(Float, nullable=True)     # from CourseSummary.total_assignments
    published_assignments = Column(Float, nullable=True) # from CourseSummary.published_assignments
    total_points = Column(Integer, nullable=False, default=0)  # from CourseSummary.total_possible_points
    
    # Relationships to other Canvas models
    assignments = relationship("CanvasAssignment", back_populates="course")
    enrollments = relationship("CanvasEnrollment", back_populates="course")
    
    # Many-to-many relationship with students through enrollments
    students = relationship("CanvasStudent", secondary="canvas_enrollments", back_populates="courses", overlaps="enrollments")
    
    def __repr__(self):
        """String representation showing course name and code."""
        return f"<CanvasCourse(id={self.id}, name='{self.name}', code='{self.course_code}')>"
    
    def get_active_students_count(self):
        """Get count of actively enrolled students."""
        return len([e for e in self.enrollments if e.enrollment_status == 'active'])
    
    def get_published_assignments_count(self):
        """Get count of published assignments."""
        return len([a for a in self.assignments if a.published])


class CanvasStudent(CanvasEntityModel):
    """
    Canvas student data model.
    
    Maps from CanvasStudentStaging object to database table.
    Contains student enrollment information and current grade status.
    """
    
    __tablename__ = 'canvas_students'
    
    # Canvas student ID as primary key (from CanvasStudentStaging.id - enrollment ID)
    # Note: This is actually the enrollment ID, but we use it as student_id per architecture
    student_id = Column(Integer, primary_key=True)  # Canvas enrollment ID (used as student identifier)
    
    # Canvas user information (from CanvasStudentStaging.user)
    user_id = Column(Integer, nullable=True)           # from CanvasStudentStaging.user_id
    # name comes from CanvasStudentStaging.user.name via CanvasBaseModel
    login_id = Column(String(255), nullable=False)    # from CanvasStudentStaging.user.login_id
    email = Column(String(255), nullable=True)        # Not directly in Canvas data, but common
    
    # Current grade information (from CanvasStudentStaging)
    current_score = Column(Float, nullable=False, default=0.0)  # from CanvasStudentStaging.current_score (percentage)
    final_score = Column(Float, nullable=False, default=0.0)    # from CanvasStudentStaging.final_score (percentage)
    
    # Activity tracking (from CanvasStudentStaging)
    enrollment_date = Column(DateTime, nullable=True)    # from CanvasStudentStaging.created_at
    last_activity = Column(DateTime, nullable=True)      # from CanvasStudentStaging.last_activity_at
    
    # Relationships to other Canvas models
    enrollments = relationship("CanvasEnrollment", back_populates="student", overlaps="students")
    
    # Many-to-many relationship with courses through enrollments
    courses = relationship("CanvasCourse", secondary="canvas_enrollments", back_populates="students", overlaps="enrollments")
    
    def __repr__(self):
        """String representation showing student name and current score."""
        return f"<CanvasStudent(student_id={self.student_id}, name='{self.name}', score={self.current_score}%)>"
    
    def has_missing_assignments(self):
        """
        Check if student has missing assignments.
        
        Based on Canvas logic: current_score != final_score indicates missing assignments
        This matches the hasMissingAssignments() method from CanvasStudentStaging.
        """
        return self.current_score != self.final_score
    
    def get_grade_improvement_potential(self):
        """Calculate potential grade improvement if all missing assignments completed."""
        return self.final_score - self.current_score


class CanvasAssignment(CanvasEntityModel):
    """
    Canvas assignment data model.
    
    Maps from CanvasAssignmentStaging object to database table.
    Represents assignments and quizzes within course modules.
    """
    
    __tablename__ = 'canvas_assignments'
    
    # Canvas assignment ID as primary key (from CanvasAssignmentStaging.id)
    id = Column(Integer, primary_key=True)  # Canvas assignment/quiz ID
    
    # Course relationship (assignments belong to courses)
    course_id = Column(Integer, ForeignKey('canvas_courses.id'), nullable=False)
    
    # Module information (from CanvasModuleStaging context)
    module_id = Column(Integer, nullable=False)      # Canvas module ID containing this assignment
    module_position = Column(Float, nullable=True)   # from CanvasAssignmentStaging.position
    
    # Assignment details (from CanvasAssignmentStaging)
    # name comes from CanvasAssignmentStaging.title via CanvasBaseModel
    url = Column(String(500), nullable=True)              # from CanvasAssignmentStaging.url
    published = Column(Boolean, nullable=False, default=False)  # from CanvasAssignmentStaging.published
    
    # Grading information (from CanvasAssignmentStaging.content_details)
    points_possible = Column(Float, nullable=True)       # from CanvasAssignmentStaging.content_details.points_possible
    
    # Additional assignment type field for Canvas internal categorization
    assignment_type = Column(String(50), nullable=True)  # Canvas internal assignment type
    
    # Relationships
    course = relationship("CanvasCourse", back_populates="assignments")
    
    # Note: Historical assignment scores relationship removed to prevent
    # forward dependency to Layer 2. Access via AssignmentScore.assignment_id queries instead.
    
    def __repr__(self):
        """String representation showing assignment name and points."""
        points = f"{self.points_possible}pts" if self.points_possible else "no points"
        return f"<CanvasAssignment(id={self.id}, name='{self.name}', {points})>"
    
    def is_quiz(self):
        """Check if this assignment is a quiz (from CanvasAssignmentStaging.assignment_type)."""
        return self.assignment_type and self.assignment_type.lower() == 'quiz'
    
    def is_published_and_graded(self):
        """Check if assignment is published and has points possible."""
        return self.published and self.points_possible is not None and self.points_possible > 0


class CanvasEnrollment(CanvasRelationshipModel):
    """
    Canvas enrollment relationship model.
    
    Represents student-course enrollment relationships.
    This bridges the relationship between CanvasStudentStaging and CanvasCourseStaging objects.
    
    Uses auto-incrementing ID as primary key for simplicity, with unique constraint on
    student_id + course_id to prevent duplicate enrollments.
    """
    
    __tablename__ = 'canvas_enrollments'
    
    # Auto-incrementing primary key (explicit since CanvasRelationshipModel doesn't inherit from BaseModel)
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key relationships
    student_id = Column(Integer, ForeignKey('canvas_students.student_id'), nullable=False)
    course_id = Column(Integer, ForeignKey('canvas_courses.id'), nullable=False)
    
    # Enrollment metadata  
    enrollment_date = Column(DateTime, nullable=True)  # from CanvasStudentStaging.created_at
    
    # Enrollment details
    enrollment_status = Column(String(50), nullable=True)  # 'active', 'inactive', etc.
    
    # Unique constraint to prevent duplicate enrollments
    __table_args__ = (
        UniqueConstraint('student_id', 'course_id', name='unique_student_course_enrollment'),
    )
    
    # Relationships
    student = relationship("CanvasStudent", back_populates="enrollments", overlaps="courses,students")
    course = relationship("CanvasCourse", back_populates="enrollments", overlaps="courses,students")
    
    def __repr__(self):
        """String representation showing enrollment relationship."""
        return f"<CanvasEnrollment(student_id={self.student_id}, course_id={self.course_id}, status='{self.enrollment_status}')>"
    
    def is_active(self):
        """Check if enrollment is active."""
        return self.enrollment_status == 'active'