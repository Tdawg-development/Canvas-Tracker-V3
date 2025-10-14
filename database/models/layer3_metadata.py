"""
Layer 3: User Metadata Models

These models store persistent user-generated data that survives Canvas sync
operations. They contain customizations, notes, tags, and preferences that
users add to enhance their Canvas data experience.

Key Characteristics:
- Persistent across all sync operations
- User-generated content only
- Never modified or deleted by sync processes
- Linked to Canvas objects by ID (soft foreign keys)
- Support for JSON-based flexible data storage

Model definitions follow the exact specification in database_architecture.md
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, Text, Boolean, DateTime
from sqlalchemy.sql import func

from ..base import MetadataEntityModel


class StudentMetadata(MetadataEntityModel):
    """
    Persistent user-defined data for students.
    
    Stores custom notes, grouping, tags, and enrollment tracking
    as specified in the database architecture documentation.
    """
    
    __tablename__ = 'student_metadata'
    
    # Reference to Canvas student (soft FK - no constraint)
    student_id = Column(Integer, primary_key=True)  # FK to canvas_students
    
    # User-defined fields as per architecture
    custom_group_id = Column(Text, nullable=True)
    enrollment_date = Column(DateTime, nullable=True, default=func.now())
    
    # Notes and tags inherited from MetadataEntityModel (via MetadataMixin):
    # - notes (Text, nullable=True)  
    # - custom_tags (Text, nullable=True)  # JSON array
    
    def __repr__(self):
        """String representation showing student ID and group."""
        group = f"group:{self.custom_group_id}" if self.custom_group_id else "no group"
        return f"<StudentMetadata(student_id={self.student_id}, {group})>"
    
    @classmethod
    def get_by_student_id(cls, session, student_id):
        """
        Get metadata for a specific student.
        
        Args:
            session: Database session
            student_id: Canvas student ID
            
        Returns:
            StudentMetadata instance or None if not found
        """
        return session.query(cls).filter_by(student_id=student_id).first()
    
    @classmethod
    def get_by_group(cls, session, group_id):
        """
        Get all student metadata for a custom group.
        
        Args:
            session: Database session
            group_id: Custom group identifier
            
        Returns:
            List of StudentMetadata instances
        """
        return session.query(cls).filter_by(custom_group_id=group_id).all()


class AssignmentMetadata(MetadataEntityModel):
    """
    Persistent user-defined data for assignments.
    
    Stores user notes, tags, difficulty rating, and time estimates
    as specified in the database architecture documentation.
    """
    
    __tablename__ = 'assignment_metadata'
    
    # Reference to Canvas assignment (soft FK - no constraint)
    assignment_id = Column(Integer, primary_key=True)  # FK to canvas_assignments
    
    # User-defined fields as per architecture (notes and custom_tags inherited from MetadataMixin)
    difficulty_rating = Column(Integer, nullable=True)
    estimated_hours = Column(Float, nullable=True)
    
    def __repr__(self):
        """String representation showing assignment ID and difficulty."""
        difficulty = f"diff:{self.difficulty_rating}" if self.difficulty_rating else "no difficulty"
        return f"<AssignmentMetadata(assignment_id={self.assignment_id}, {difficulty})>"
    
    def set_difficulty(self, difficulty):
        """
        Set difficulty rating with validation.
        
        Args:
            difficulty (int): Difficulty level (1-5, where 5 is most difficult)
        """
        if difficulty is not None and (difficulty < 1 or difficulty > 5):
            raise ValueError("Difficulty must be between 1 and 5")
        self.difficulty_rating = difficulty
    
    def set_estimated_hours(self, hours):
        """
        Set estimated completion time with validation.
        
        Args:
            hours (float): Estimated hours to complete
        """
        if hours is not None and hours < 0:
            raise ValueError("Estimated hours cannot be negative")
        self.estimated_hours = hours
    
    def is_difficult(self):
        """Check if assignment is marked as difficult (4-5)."""
        return self.difficulty_rating is not None and self.difficulty_rating >= 4
    
    def is_time_consuming(self, threshold_hours=5.0):
        """
        Check if assignment is estimated to be time consuming.
        
        Args:
            threshold_hours (float): Hour threshold for "time consuming"
            
        Returns:
            bool: True if estimated hours exceed threshold
        """
        return self.estimated_hours is not None and self.estimated_hours >= threshold_hours
    
    @classmethod
    def get_by_assignment_id(cls, session, assignment_id):
        """
        Get metadata for a specific assignment.
        
        Args:
            session: Database session
            assignment_id: Canvas assignment ID
            
        Returns:
            AssignmentMetadata instance or None if not found
        """
        return session.query(cls).filter_by(assignment_id=assignment_id).first()
    
    @classmethod
    def get_by_difficulty(cls, session, min_difficulty=4):
        """
        Get assignments by difficulty level.
        
        Args:
            session: Database session
            min_difficulty: Minimum difficulty level to return
            
        Returns:
            List of AssignmentMetadata instances
        """
        return session.query(cls).filter(cls.difficulty_rating >= min_difficulty).all()
    
    @classmethod
    def get_time_consuming(cls, session, min_hours=5.0):
        """
        Get assignments estimated to take significant time.
        
        Args:
            session: Database session
            min_hours: Minimum estimated hours threshold
            
        Returns:
            List of AssignmentMetadata instances
        """
        return session.query(cls).filter(cls.estimated_hours >= min_hours).all()


class CourseMetadata(MetadataEntityModel):
    """
    Persistent user-defined data for courses.
    
    Stores user notes, custom color, course hours, and tracking settings
    as specified in the database architecture documentation.
    """
    
    __tablename__ = 'course_metadata'
    
    # Reference to Canvas course (soft FK - no constraint)
    course_id = Column(Integer, primary_key=True)  # FK to canvas_courses
    
    # User-defined fields as per architecture (notes and custom_tags inherited from MetadataMixin)
    custom_color = Column(Text, nullable=True)
    course_hours = Column(Integer, nullable=True)
    tracking_enabled = Column(Boolean, nullable=False, default=True)
    
    def __repr__(self):
        """String representation showing course ID and tracking status."""
        tracking = "tracked" if self.tracking_enabled else "not tracked"
        color = f"color:{self.custom_color}" if self.custom_color else "no color"
        return f"<CourseMetadata(course_id={self.course_id}, {tracking}, {color})>"
    
    def set_color(self, color_code):
        """
        Set custom color with basic validation.
        
        Args:
            color_code (str): Color code (should be hex format like #FF0000)
        """
        if color_code is not None:
            # Basic validation for hex color format
            if not (color_code.startswith('#') and len(color_code) == 7):
                raise ValueError("Color must be in hex format like #FF0000")
            # Check that the hex characters are valid
            hex_chars = color_code[1:]  # Remove the #
            if not all(c in '0123456789ABCDEFabcdef' for c in hex_chars):
                raise ValueError("Color must be in hex format like #FF0000")
        self.custom_color = color_code
    
    def set_course_hours(self, hours):
        """
        Set expected course hours with validation.
        
        Args:
            hours (int): Expected total hours for the course
        """
        if hours is not None and hours < 0:
            raise ValueError("Course hours cannot be negative")
        self.course_hours = hours
    
    def is_high_workload(self):
        """Check if course has high hour commitment (>40 hours total)."""
        return self.course_hours is not None and self.course_hours > 40
    
    @classmethod
    def get_by_course_id(cls, session, course_id):
        """
        Get metadata for a specific course.
        
        Args:
            session: Database session
            course_id: Canvas course ID
            
        Returns:
            CourseMetadata instance or None if not found
        """
        return session.query(cls).filter_by(course_id=course_id).first()
    
    @classmethod
    def get_tracked_courses(cls, session):
        """
        Get all courses with tracking enabled.
        
        Args:
            session: Database session
            
        Returns:
            List of CourseMetadata instances where tracking_enabled=True
        """
        return session.query(cls).filter_by(tracking_enabled=True).all()
    
    @classmethod
    def get_high_workload_courses(cls, session, min_hours=40):
        """
        Get courses with high hour commitment.
        
        Args:
            session: Database session
            min_hours: Minimum hours threshold
            
        Returns:
            List of CourseMetadata instances
        """
        return session.query(cls).filter(cls.course_hours >= min_hours).all()