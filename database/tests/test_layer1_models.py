"""
Unit tests for Layer 1 Canvas Data Models.

Tests the Canvas data models that represent pure Canvas API data:
- CanvasCourse: Course information and statistics
- CanvasStudent: Student enrollment and grade data  
- CanvasAssignment: Assignment/quiz information
- CanvasEnrollment: Student-course relationships

These models are completely replaced during sync operations and contain
exactly what Canvas provides via the CanvasDataConstructor.
"""

import pytest
from datetime import datetime, timezone
from sqlalchemy.exc import IntegrityError

from database.models.layer1_canvas import (
    CanvasCourse, 
    CanvasStudent, 
    CanvasAssignment, 
    CanvasEnrollment
)
from database import initialize_database


class TestCanvasCourse:
    """Test CanvasCourse model functionality."""
    
    def test_canvas_course_creation(self, db_session):
        """Test basic course creation with required fields."""
        course = CanvasCourse(
            id=12345,
            name="Web Development Bootcamp",
            course_code="WEB-101",
            total_points=1000
        )
        
        db_session.add(course)
        db_session.commit()
        
        # Verify course was created
        saved_course = db_session.query(CanvasCourse).filter_by(id=12345).first()
        assert saved_course is not None
        assert saved_course.name == "Web Development Bootcamp"
        assert saved_course.course_code == "WEB-101"
        assert saved_course.total_points == 1000
    
    def test_course_with_statistics(self, db_session):
        """Test course with calculated statistics from CourseSummary."""
        course = CanvasCourse(
            id=67890,
            name="Data Science Track",
            course_code="DS-201",
            total_students=25.0,
            total_modules=8.0,
            total_assignments=45.0,
            published_assignments=40.0,
            total_points=2500,
            calendar_ics="https://canvas.example.com/calendar.ics"
        )
        
        db_session.add(course)
        db_session.commit()
        
        saved_course = db_session.query(CanvasCourse).filter_by(id=67890).first()
        assert saved_course.total_students == 25.0
        assert saved_course.total_modules == 8.0
        assert saved_course.total_assignments == 45.0
        assert saved_course.published_assignments == 40.0
        assert saved_course.calendar_ics == "https://canvas.example.com/calendar.ics"
    
    def test_course_repr(self, db_session):
        """Test string representation of course."""
        course = CanvasCourse(
            id=11111,
            name="Test Course",
            course_code="TEST-001"
        )
        
        expected = "<CanvasCourse(id=11111, name='Test Course', code='TEST-001')>"
        assert repr(course) == expected


class TestCanvasStudent:
    """Test CanvasStudent model functionality."""
    
    def test_canvas_student_creation(self, db_session):
        """Test basic student creation with required fields."""
        student = CanvasStudent(
            student_id=98765,
            user_id=54321,
            name="John Smith",
            login_id="john.smith@example.com",
            current_score=85,
            final_score=90
        )
        
        db_session.add(student)
        db_session.commit()
        
        saved_student = db_session.query(CanvasStudent).filter_by(student_id=98765).first()
        assert saved_student is not None
        assert saved_student.name == "John Smith"
        assert saved_student.login_id == "john.smith@example.com"
        assert saved_student.current_score == 85
        assert saved_student.final_score == 90
    
    def test_has_missing_assignments(self, db_session):
        """Test missing assignments detection logic."""
        # Student with missing assignments (current_score < final_score)
        student_with_missing = CanvasStudent(
            student_id=11111,
            name="Student Missing",
            login_id="missing",
            current_score=75,  # Lower than final score
            final_score=85     # Higher indicates missing assignments
        )
        
        # Student without missing assignments (current_score == final_score)  
        student_complete = CanvasStudent(
            student_id=22222,
            name="Student Complete",
            login_id="complete",
            current_score=90,
            final_score=90     # Same as current score
        )
        
        assert student_with_missing.has_missing_assignments()
        assert not student_complete.has_missing_assignments()
    
    def test_grade_improvement_potential(self, db_session):
        """Test grade improvement calculation."""
        student = CanvasStudent(
            student_id=33333,
            name="Test Student",
            login_id="test",
            current_score=70,
            final_score=85
        )
        
        # Improvement potential should be final_score - current_score
        assert student.get_grade_improvement_potential() == 15


class TestCanvasAssignment:
    """Test CanvasAssignment model functionality."""
    
    def test_assignment_creation(self, db_session):
        """Test basic assignment creation."""
        # First create a course for the assignment
        course = CanvasCourse(id=100, name="Test Course")
        db_session.add(course)
        db_session.flush()  # Ensure course exists before creating assignment
        
        assignment = CanvasAssignment(
            id=2001,
            course_id=100,
            module_id=301,
            name="JavaScript Fundamentals",
            type="Assignment",
            points_possible=100.0,
            published=True
        )
        
        db_session.add(assignment)
        db_session.commit()
        
        saved_assignment = db_session.query(CanvasAssignment).filter_by(id=2001).first()
        assert saved_assignment is not None
        assert saved_assignment.name == "JavaScript Fundamentals"
        assert saved_assignment.type == "Assignment"
        assert saved_assignment.points_possible == 100.0
        assert saved_assignment.published
    
    def test_assignment_type_checking(self, db_session):
        """Test assignment type helper methods."""
        quiz = CanvasAssignment(
            id=3001,
            course_id=102,
            module_id=303,
            name="Test Quiz",
            type="Quiz"
        )
        
        assignment = CanvasAssignment(
            id=3002,
            course_id=102,
            module_id=303,
            name="Test Assignment",
            type="Assignment"
        )
        
        assert quiz.is_quiz()
        assert not assignment.is_quiz()


class TestCanvasEnrollment:
    """Test CanvasEnrollment model functionality."""
    
    def test_enrollment_creation(self, db_session):
        """Test basic enrollment creation."""
        # Create course and student first
        course = CanvasCourse(id=200, name="Test Course")
        student = CanvasStudent(student_id=8001, name="Test Student", login_id="test")
        
        db_session.add(course)
        db_session.add(student)
        db_session.flush()
        
        enrollment_date = datetime(2024, 9, 1, tzinfo=timezone.utc)
        enrollment = CanvasEnrollment(
            student_id=8001,
            course_id=200,
            enrollment_date=enrollment_date,
            enrollment_status="active"
        )
        
        db_session.add(enrollment)
        db_session.commit()
        
        saved_enrollment = db_session.query(CanvasEnrollment).filter_by(
            student_id=8001, course_id=200
        ).first()
        
        assert saved_enrollment is not None
        assert saved_enrollment.enrollment_status == "active"
        assert saved_enrollment.enrollment_date == enrollment_date
    
    def test_enrollment_status_checking(self, db_session):
        """Test enrollment status helper methods."""
        active_enrollment = CanvasEnrollment(
            student_id=8002,
            course_id=201,
            enrollment_date=datetime.now(timezone.utc),
            enrollment_status="active"
        )
        
        inactive_enrollment = CanvasEnrollment(
            student_id=8003,
            course_id=201,
            enrollment_date=datetime.now(timezone.utc),
            enrollment_status="inactive"
        )
        
        assert active_enrollment.is_active()
        assert not inactive_enrollment.is_active()


class TestLayer1ModelRelationships:
    """Test relationships between Layer 1 models."""
    
    def test_course_student_relationship(self, db_session):
        """Test many-to-many relationship between courses and students."""
        # Create course and student
        course = CanvasCourse(id=300, name="Relationship Test Course")
        student = CanvasStudent(student_id=9001, name="Relationship Student", login_id="rel_test")
        
        db_session.add(course)
        db_session.add(student)
        db_session.flush()
        
        # Create enrollment to establish relationship
        enrollment = CanvasEnrollment(
            student_id=9001,
            course_id=300,
            enrollment_date=datetime.now(timezone.utc),
            enrollment_status="active"
        )
        
        db_session.add(enrollment)
        db_session.commit()
        
        # Test relationships
        saved_course = db_session.query(CanvasCourse).filter_by(id=300).first()
        saved_student = db_session.query(CanvasStudent).filter_by(student_id=9001).first()
        
        # Course should have student through enrollment
        assert len(saved_course.students) == 1
        assert saved_course.students[0].student_id == 9001
        
        # Student should have course through enrollment
        assert len(saved_student.courses) == 1
        assert saved_student.courses[0].id == 300
        
        # Both should have enrollment records
        assert len(saved_course.enrollments) == 1
        assert len(saved_student.enrollments) == 1
    
    def test_course_assignment_relationship(self, db_session):
        """Test one-to-many relationship between courses and assignments."""
        course = CanvasCourse(id=301, name="Assignment Test Course")
        db_session.add(course)
        db_session.flush()
        
        # Create multiple assignments for the course
        assignments = [
            CanvasAssignment(
                id=6001,
                course_id=301,
                module_id=401,
                name="Assignment 1"
            ),
            CanvasAssignment(
                id=6002,
                course_id=301,
                module_id=401,
                name="Assignment 2"
            )
        ]
        
        db_session.add_all(assignments)
        db_session.commit()
        
        saved_course = db_session.query(CanvasCourse).filter_by(id=301).first()
        
        # Course should have both assignments
        assert len(saved_course.assignments) == 2
        assignment_names = [a.name for a in saved_course.assignments]
        assert "Assignment 1" in assignment_names
        assert "Assignment 2" in assignment_names