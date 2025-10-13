#!/usr/bin/env python3
"""
Create a development database with sample data for manual inspection.

This creates a persistent SQLite database file that can be opened with
DB Browser for SQLite or other database tools.
"""

import sys
import os
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.join(os.path.dirname(__file__), '..')
sys.path.insert(0, project_root)

from database import initialize_database, get_session
from database.config import DatabaseConfig
from database.models.layer1_canvas import (
    CanvasCourse, 
    CanvasStudent, 
    CanvasAssignment, 
    CanvasEnrollment
)


def create_sample_data(session):
    """Create sample Canvas data for inspection."""
    print("Creating sample data...")
    
    # Create sample courses
    courses = [
        CanvasCourse(
            id=12345,
            name="Web Development Bootcamp",
            course_code="WEB-101",
            total_students=25.0,
            total_modules=8.0,
            total_assignments=15.0,
            published_assignments=12.0,
            total_points=1500,
            calendar_ics="https://canvas.example.com/calendar/web101.ics"
        ),
        CanvasCourse(
            id=67890,
            name="Data Science Track", 
            course_code="DS-201",
            total_students=18.0,
            total_modules=10.0,
            total_assignments=20.0,
            published_assignments=18.0,
            total_points=2000,
            calendar_ics="https://canvas.example.com/calendar/ds201.ics"
        )
    ]
    
    session.add_all(courses)
    session.flush()  # Get IDs assigned
    
    # Create sample students
    students = [
        CanvasStudent(
            student_id=98001,
            user_id=54001,
            name="John Smith",
            login_id="john.smith@example.com",
            email="john.smith@example.com",
            current_score=85,
            final_score=90,
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            last_activity=datetime(2024, 10, 13, 14, 30, tzinfo=timezone.utc)
        ),
        CanvasStudent(
            student_id=98002,
            user_id=54002,
            name="Jane Doe",
            login_id="jane.doe@example.com", 
            email="jane.doe@example.com",
            current_score=78,
            final_score=82,
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            last_activity=datetime(2024, 10, 12, 16, 15, tzinfo=timezone.utc)
        ),
        CanvasStudent(
            student_id=98003,
            user_id=54003,
            name="Bob Johnson",
            login_id="bob.johnson@example.com",
            email="bob.johnson@example.com", 
            current_score=92,
            final_score=92,  # No missing assignments
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            last_activity=datetime(2024, 10, 13, 10, 45, tzinfo=timezone.utc)
        )
    ]
    
    session.add_all(students)
    session.flush()
    
    # Create sample assignments
    assignments = [
        CanvasAssignment(
            id=2001,
            course_id=12345,  # Web Development Bootcamp
            module_id=301,
            module_position=1.0,
            name="HTML Basics",
            type="Assignment",
            url="https://canvas.example.com/courses/12345/assignments/2001",
            published=True,
            points_possible=100.0,
            assignment_type="online_text_entry"
        ),
        CanvasAssignment(
            id=2002,
            course_id=12345,  # Web Development Bootcamp
            module_id=301,
            module_position=2.0,
            name="CSS Styling Quiz",
            type="Quiz",
            url="https://canvas.example.com/courses/12345/quizzes/2002",
            published=True,
            points_possible=50.0,
            assignment_type="online_quiz"
        ),
        CanvasAssignment(
            id=2003,
            course_id=67890,  # Data Science Track
            module_id=401,
            module_position=1.0,
            name="Python Data Analysis",
            type="Assignment", 
            url="https://canvas.example.com/courses/67890/assignments/2003",
            published=True,
            points_possible=200.0,
            assignment_type="online_upload"
        )
    ]
    
    session.add_all(assignments)
    session.flush()
    
    # Create sample enrollments
    enrollments = [
        # John Smith enrollments
        CanvasEnrollment(
            student_id=98001,
            course_id=12345,  # Web Development
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            enrollment_status="active"
        ),
        # Jane Doe enrollments  
        CanvasEnrollment(
            student_id=98002,
            course_id=12345,  # Web Development
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            enrollment_status="active"
        ),
        CanvasEnrollment(
            student_id=98002,
            course_id=67890,  # Data Science
            enrollment_date=datetime(2024, 9, 15, tzinfo=timezone.utc),
            enrollment_status="active"
        ),
        # Bob Johnson enrollments
        CanvasEnrollment(
            student_id=98003,
            course_id=67890,  # Data Science  
            enrollment_date=datetime(2024, 9, 1, tzinfo=timezone.utc),
            enrollment_status="active"
        )
    ]
    
    session.add_all(enrollments)
    
    # Mark all objects as recently synced
    sync_time = datetime.now(timezone.utc)
    for course in courses:
        course.mark_synced(sync_time)
    for student in students:
        student.mark_synced(sync_time)
    for assignment in assignments:
        assignment.mark_synced(sync_time)
    for enrollment in enrollments:
        enrollment.mark_synced(sync_time)
    
    session.commit()
    print(f"✓ Created {len(courses)} courses")
    print(f"✓ Created {len(students)} students") 
    print(f"✓ Created {len(assignments)} assignments")
    print(f"✓ Created {len(enrollments)} enrollments")


def main():
    """Create development database with sample data."""
    print("Canvas Tracker V3 - Development Database Creator")
    print("=" * 50)
    
    # Create development database configuration
    dev_config = DatabaseConfig('dev')
    print(f"Database URL: {dev_config.database_url}")
    
    if dev_config.is_sqlite():
        db_path = dev_config.get_database_path()
        print(f"SQLite database file: {os.path.abspath(db_path)}")
    
    # Initialize database
    print("\nInitializing database...")
    initialize_database(dev_config)
    print("✓ Database tables created")
    
    # Create sample data
    with get_session(dev_config) as session:
        create_sample_data(session)
    
    print("\n" + "=" * 50)
    print("✅ Development database created successfully!")
    
    if dev_config.is_sqlite():
        db_path = os.path.abspath(dev_config.get_database_path())
        print(f"\nYou can now open the database file with DB Browser for SQLite:")
        print(f"File: {db_path}")
        print("\nTables created:")
        print("- canvas_courses")
        print("- canvas_students") 
        print("- canvas_assignments")
        print("- canvas_enrollments")


if __name__ == "__main__":
    main()