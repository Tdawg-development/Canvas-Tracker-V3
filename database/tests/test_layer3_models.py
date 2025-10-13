"""
Unit tests for Layer 3 User Metadata Models.

Tests the user metadata models that store persistent user-generated data:
- StudentMetadata: Custom notes, grouping, tags, and enrollment tracking
- AssignmentMetadata: User notes, tags, difficulty rating, and time estimates  
- CourseMetadata: User notes, custom color, course hours, and tracking settings

These models provide persistent user customizations that survive all Canvas
sync operations and enable enhanced user experience beyond raw Canvas data.
"""

import pytest
from datetime import datetime, timezone

from database.models.layer3_metadata import StudentMetadata, AssignmentMetadata, CourseMetadata


class TestStudentMetadata:
    """Test StudentMetadata model functionality."""
    
    def test_student_metadata_creation(self, db_session):
        """Test basic student metadata record creation."""
        student_meta = StudentMetadata(
            student_id=12345,
            notes="High-performing student, needs advanced challenges",
            custom_group_id="advanced_group_1",
            enrollment_date=datetime(2024, 9, 1, 10, 0, tzinfo=timezone.utc)
        )
        student_meta.add_tag("high-performer")
        student_meta.add_tag("needs-attention")
        
        db_session.add(student_meta)
        db_session.commit()
        
        saved_record = db_session.query(StudentMetadata).filter_by(student_id=12345).first()
        
        assert saved_record is not None
        assert saved_record.student_id == 12345
        assert saved_record.notes == "High-performing student, needs advanced challenges"
        assert saved_record.custom_group_id == "advanced_group_1"
        assert saved_record.enrollment_date.year == 2024
        assert saved_record.created_at is not None  # From MetadataBaseModel
        assert saved_record.updated_at is not None  # From MetadataBaseModel
        
        # Test tags functionality from MetadataBaseModel
        tags = saved_record.get_tags()
        assert "high-performer" in tags
        assert "needs-attention" in tags
    
    def test_student_metadata_minimal(self, db_session):
        """Test creating student metadata with minimal required fields."""
        student_meta = StudentMetadata(student_id=67890)
        
        db_session.add(student_meta)
        db_session.commit()
        
        saved_record = db_session.query(StudentMetadata).filter_by(student_id=67890).first()
        
        assert saved_record is not None
        assert saved_record.student_id == 67890
        assert saved_record.notes is None
        assert saved_record.custom_group_id is None
        # enrollment_date should have default
        assert saved_record.enrollment_date is not None
    
    def test_student_metadata_repr(self, db_session):
        """Test string representation of student metadata."""
        # With group
        student_with_group = StudentMetadata(
            student_id=111,
            custom_group_id="test_group"
        )
        expected_with_group = "<StudentMetadata(student_id=111, group:test_group)>"
        assert repr(student_with_group) == expected_with_group
        
        # Without group
        student_no_group = StudentMetadata(student_id=222)
        expected_no_group = "<StudentMetadata(student_id=222, no group)>"
        assert repr(student_no_group) == expected_no_group
    
    def test_student_metadata_tags(self, db_session):
        """Test tag management functionality."""
        student_meta = StudentMetadata(student_id=333)
        
        # Test adding tags
        student_meta.add_tag("struggling")
        student_meta.add_tag("math-focused")
        assert len(student_meta.get_tags()) == 2
        assert "struggling" in student_meta.get_tags()
        
        # Test adding duplicate tag
        student_meta.add_tag("struggling")  # Should not duplicate
        assert len(student_meta.get_tags()) == 2
        
        # Test removing tags
        student_meta.remove_tag("struggling")
        assert "struggling" not in student_meta.get_tags()
        assert "math-focused" in student_meta.get_tags()
        
        db_session.add(student_meta)
        db_session.commit()
        
        # Verify persistence
        saved_record = db_session.query(StudentMetadata).filter_by(student_id=333).first()
        assert "math-focused" in saved_record.get_tags()
        assert "struggling" not in saved_record.get_tags()
    
    def test_get_by_student_id(self, db_session):
        """Test querying student metadata by student ID."""
        student_meta = StudentMetadata(
            student_id=444,
            notes="Test student metadata",
            custom_group_id="group_a"
        )
        
        db_session.add(student_meta)
        db_session.commit()
        
        # Test successful lookup
        found = StudentMetadata.get_by_student_id(db_session, 444)
        assert found is not None
        assert found.student_id == 444
        assert found.notes == "Test student metadata"
        
        # Test not found
        not_found = StudentMetadata.get_by_student_id(db_session, 999)
        assert not_found is None
    
    def test_get_by_group(self, db_session):
        """Test querying students by custom group."""
        # Create students in same group
        students = [
            StudentMetadata(student_id=501, custom_group_id="group_b"),
            StudentMetadata(student_id=502, custom_group_id="group_b"),
            StudentMetadata(student_id=503, custom_group_id="group_c"),
        ]
        
        db_session.add_all(students)
        db_session.commit()
        
        # Get students in group_b
        group_b_students = StudentMetadata.get_by_group(db_session, "group_b")
        assert len(group_b_students) == 2
        student_ids = [s.student_id for s in group_b_students]
        assert 501 in student_ids
        assert 502 in student_ids
        
        # Get students in group_c
        group_c_students = StudentMetadata.get_by_group(db_session, "group_c")
        assert len(group_c_students) == 1
        assert group_c_students[0].student_id == 503
        
        # Get students in non-existent group
        empty_group = StudentMetadata.get_by_group(db_session, "group_nonexistent")
        assert len(empty_group) == 0


class TestAssignmentMetadata:
    """Test AssignmentMetadata model functionality."""
    
    def test_assignment_metadata_creation(self, db_session):
        """Test basic assignment metadata record creation."""
        assignment_meta = AssignmentMetadata(
            assignment_id=1001,
            user_notes="This assignment covers advanced Python concepts",
            difficulty_rating=4,
            estimated_hours=8.5
        )
        assignment_meta.add_tag("python")
        assignment_meta.add_tag("advanced")
        
        db_session.add(assignment_meta)
        db_session.commit()
        
        saved_record = db_session.query(AssignmentMetadata).filter_by(assignment_id=1001).first()
        
        assert saved_record is not None
        assert saved_record.assignment_id == 1001
        assert saved_record.user_notes == "This assignment covers advanced Python concepts"
        assert saved_record.difficulty_rating == 4
        assert saved_record.estimated_hours == 8.5
        assert saved_record.created_at is not None
        assert saved_record.updated_at is not None
        
        # Check custom_tags field (not inherited tags)
        assert saved_record.custom_tags is not None
    
    def test_assignment_metadata_minimal(self, db_session):
        """Test creating assignment metadata with minimal fields."""
        assignment_meta = AssignmentMetadata(assignment_id=1002)
        
        db_session.add(assignment_meta)
        db_session.commit()
        
        saved_record = db_session.query(AssignmentMetadata).filter_by(assignment_id=1002).first()
        
        assert saved_record is not None
        assert saved_record.assignment_id == 1002
        assert saved_record.user_notes is None
        assert saved_record.custom_tags is None
        assert saved_record.difficulty_rating is None
        assert saved_record.estimated_hours is None
    
    def test_assignment_metadata_repr(self, db_session):
        """Test string representation of assignment metadata."""
        # With difficulty
        assignment_with_diff = AssignmentMetadata(
            assignment_id=111,
            difficulty_rating=5
        )
        expected_with_diff = "<AssignmentMetadata(assignment_id=111, diff:5)>"
        assert repr(assignment_with_diff) == expected_with_diff
        
        # Without difficulty
        assignment_no_diff = AssignmentMetadata(assignment_id=222)
        expected_no_diff = "<AssignmentMetadata(assignment_id=222, no difficulty)>"
        assert repr(assignment_no_diff) == expected_no_diff
    
    def test_set_difficulty_validation(self, db_session):
        """Test difficulty rating validation."""
        assignment_meta = AssignmentMetadata(assignment_id=1003)
        
        # Valid difficulty ratings
        for valid_rating in [1, 2, 3, 4, 5]:
            assignment_meta.set_difficulty(valid_rating)
            assert assignment_meta.difficulty_rating == valid_rating
        
        # Test None (should be allowed)
        assignment_meta.set_difficulty(None)
        assert assignment_meta.difficulty_rating is None
        
        # Invalid difficulty ratings
        with pytest.raises(ValueError, match="Difficulty must be between 1 and 5"):
            assignment_meta.set_difficulty(0)
        
        with pytest.raises(ValueError, match="Difficulty must be between 1 and 5"):
            assignment_meta.set_difficulty(6)
    
    def test_set_estimated_hours_validation(self, db_session):
        """Test estimated hours validation."""
        assignment_meta = AssignmentMetadata(assignment_id=1004)
        
        # Valid hours
        assignment_meta.set_estimated_hours(5.5)
        assert assignment_meta.estimated_hours == 5.5
        
        assignment_meta.set_estimated_hours(0)  # Zero should be valid
        assert assignment_meta.estimated_hours == 0
        
        # Test None (should be allowed)
        assignment_meta.set_estimated_hours(None)
        assert assignment_meta.estimated_hours is None
        
        # Invalid hours (negative)
        with pytest.raises(ValueError, match="Estimated hours cannot be negative"):
            assignment_meta.set_estimated_hours(-1.0)
    
    def test_is_difficult(self, db_session):
        """Test difficulty detection."""
        assignment_meta = AssignmentMetadata(assignment_id=1005)
        
        # Not difficult
        assignment_meta.difficulty_rating = 3
        assert assignment_meta.is_difficult() is False
        
        # Difficult
        assignment_meta.difficulty_rating = 4
        assert assignment_meta.is_difficult() is True
        
        assignment_meta.difficulty_rating = 5
        assert assignment_meta.is_difficult() is True
        
        # No rating
        assignment_meta.difficulty_rating = None
        assert assignment_meta.is_difficult() is False
    
    def test_is_time_consuming(self, db_session):
        """Test time consuming detection."""
        assignment_meta = AssignmentMetadata(assignment_id=1006)
        
        # Not time consuming (default threshold 5.0)
        assignment_meta.estimated_hours = 4.0
        assert assignment_meta.is_time_consuming() is False
        
        # Time consuming
        assignment_meta.estimated_hours = 5.0
        assert assignment_meta.is_time_consuming() is True
        
        assignment_meta.estimated_hours = 10.0
        assert assignment_meta.is_time_consuming() is True
        
        # Custom threshold
        assignment_meta.estimated_hours = 3.0
        assert assignment_meta.is_time_consuming(threshold_hours=2.0) is True
        assert assignment_meta.is_time_consuming(threshold_hours=4.0) is False
        
        # No estimate
        assignment_meta.estimated_hours = None
        assert assignment_meta.is_time_consuming() is False
    
    def test_get_by_assignment_id(self, db_session):
        """Test querying assignment metadata by assignment ID."""
        assignment_meta = AssignmentMetadata(
            assignment_id=2001,
            user_notes="Test assignment metadata",
            difficulty_rating=3
        )
        
        db_session.add(assignment_meta)
        db_session.commit()
        
        # Test successful lookup
        found = AssignmentMetadata.get_by_assignment_id(db_session, 2001)
        assert found is not None
        assert found.assignment_id == 2001
        assert found.difficulty_rating == 3
        
        # Test not found
        not_found = AssignmentMetadata.get_by_assignment_id(db_session, 9999)
        assert not_found is None
    
    def test_get_by_difficulty(self, db_session):
        """Test querying assignments by difficulty level."""
        assignments = [
            AssignmentMetadata(assignment_id=3001, difficulty_rating=2),
            AssignmentMetadata(assignment_id=3002, difficulty_rating=4),
            AssignmentMetadata(assignment_id=3003, difficulty_rating=5),
            AssignmentMetadata(assignment_id=3004, difficulty_rating=3),
            AssignmentMetadata(assignment_id=3005),  # No rating
        ]
        
        db_session.add_all(assignments)
        db_session.commit()
        
        # Get difficult assignments (default min_difficulty=4)
        difficult = AssignmentMetadata.get_by_difficulty(db_session)
        assert len(difficult) == 2
        assignment_ids = [a.assignment_id for a in difficult]
        assert 3002 in assignment_ids
        assert 3003 in assignment_ids
        
        # Custom difficulty threshold
        moderate_plus = AssignmentMetadata.get_by_difficulty(db_session, min_difficulty=3)
        assert len(moderate_plus) == 3  # 3, 4, 5 difficulty ratings
    
    def test_get_time_consuming(self, db_session):
        """Test querying time-consuming assignments."""
        assignments = [
            AssignmentMetadata(assignment_id=4001, estimated_hours=2.0),
            AssignmentMetadata(assignment_id=4002, estimated_hours=5.0),
            AssignmentMetadata(assignment_id=4003, estimated_hours=8.5),
            AssignmentMetadata(assignment_id=4004, estimated_hours=1.5),
            AssignmentMetadata(assignment_id=4005),  # No estimate
        ]
        
        db_session.add_all(assignments)
        db_session.commit()
        
        # Get time consuming (default min_hours=5.0)
        time_consuming = AssignmentMetadata.get_time_consuming(db_session)
        assert len(time_consuming) == 2
        assignment_ids = [a.assignment_id for a in time_consuming]
        assert 4002 in assignment_ids
        assert 4003 in assignment_ids
        
        # Custom threshold
        moderate_time = AssignmentMetadata.get_time_consuming(db_session, min_hours=2.0)
        assert len(moderate_time) == 3  # 2.0, 5.0, 8.5 hour assignments


class TestCourseMetadata:
    """Test CourseMetadata model functionality."""
    
    def test_course_metadata_creation(self, db_session):
        """Test basic course metadata record creation."""
        course_meta = CourseMetadata(
            course_id=5001,
            user_notes="Advanced programming course, requires significant time commitment",
            custom_color="#3498db",
            course_hours=120,
            tracking_enabled=True
        )
        
        db_session.add(course_meta)
        db_session.commit()
        
        saved_record = db_session.query(CourseMetadata).filter_by(course_id=5001).first()
        
        assert saved_record is not None
        assert saved_record.course_id == 5001
        assert saved_record.user_notes == "Advanced programming course, requires significant time commitment"
        assert saved_record.custom_color == "#3498db"
        assert saved_record.course_hours == 120
        assert saved_record.tracking_enabled is True
        assert saved_record.created_at is not None
        assert saved_record.updated_at is not None
    
    def test_course_metadata_minimal(self, db_session):
        """Test creating course metadata with minimal fields."""
        course_meta = CourseMetadata(course_id=5002)
        
        db_session.add(course_meta)
        db_session.commit()
        
        saved_record = db_session.query(CourseMetadata).filter_by(course_id=5002).first()
        
        assert saved_record is not None
        assert saved_record.course_id == 5002
        assert saved_record.user_notes is None
        assert saved_record.custom_color is None
        assert saved_record.course_hours is None
        assert saved_record.tracking_enabled is True  # Default value
    
    def test_course_metadata_repr(self, db_session):
        """Test string representation of course metadata."""
        # With color and tracking
        course_with_color = CourseMetadata(
            course_id=111,
            custom_color="#FF0000",
            tracking_enabled=True
        )
        expected_with_color = "<CourseMetadata(course_id=111, tracked, color:#FF0000)>"
        assert repr(course_with_color) == expected_with_color
        
        # Without color, not tracked
        course_no_color = CourseMetadata(
            course_id=222,
            tracking_enabled=False
        )
        expected_no_color = "<CourseMetadata(course_id=222, not tracked, no color)>"
        assert repr(course_no_color) == expected_no_color
    
    def test_set_color_validation(self, db_session):
        """Test custom color validation."""
        course_meta = CourseMetadata(course_id=5003)
        
        # Valid hex colors
        valid_colors = ["#FF0000", "#3498db", "#000000", "#FFFFFF"]
        for color in valid_colors:
            course_meta.set_color(color)
            assert course_meta.custom_color == color
        
        # Test None (should be allowed)
        course_meta.set_color(None)
        assert course_meta.custom_color is None
        
        # Invalid color formats
        invalid_colors = ["FF0000", "#FF00", "#GGGGGG", "red", ""]
        for invalid_color in invalid_colors:
            with pytest.raises(ValueError, match="Color must be in hex format like #FF0000"):
                course_meta.set_color(invalid_color)
    
    def test_set_course_hours_validation(self, db_session):
        """Test course hours validation."""
        course_meta = CourseMetadata(course_id=5004)
        
        # Valid hours
        course_meta.set_course_hours(40)
        assert course_meta.course_hours == 40
        
        course_meta.set_course_hours(0)  # Zero should be valid
        assert course_meta.course_hours == 0
        
        # Test None (should be allowed)
        course_meta.set_course_hours(None)
        assert course_meta.course_hours is None
        
        # Invalid hours (negative)
        with pytest.raises(ValueError, match="Course hours cannot be negative"):
            course_meta.set_course_hours(-10)
    
    def test_is_high_workload(self, db_session):
        """Test high workload detection."""
        course_meta = CourseMetadata(course_id=5005)
        
        # Not high workload
        course_meta.course_hours = 30
        assert course_meta.is_high_workload() is False
        
        course_meta.course_hours = 40
        assert course_meta.is_high_workload() is False
        
        # High workload
        course_meta.course_hours = 50
        assert course_meta.is_high_workload() is True
        
        course_meta.course_hours = 100
        assert course_meta.is_high_workload() is True
        
        # No hours set
        course_meta.course_hours = None
        assert course_meta.is_high_workload() is False
    
    def test_get_by_course_id(self, db_session):
        """Test querying course metadata by course ID."""
        course_meta = CourseMetadata(
            course_id=6001,
            user_notes="Test course metadata",
            custom_color="#00FF00"
        )
        
        db_session.add(course_meta)
        db_session.commit()
        
        # Test successful lookup
        found = CourseMetadata.get_by_course_id(db_session, 6001)
        assert found is not None
        assert found.course_id == 6001
        assert found.custom_color == "#00FF00"
        
        # Test not found
        not_found = CourseMetadata.get_by_course_id(db_session, 9999)
        assert not_found is None
    
    def test_get_tracked_courses(self, db_session):
        """Test querying tracked courses."""
        courses = [
            CourseMetadata(course_id=7001, tracking_enabled=True),
            CourseMetadata(course_id=7002, tracking_enabled=False),
            CourseMetadata(course_id=7003, tracking_enabled=True),
            CourseMetadata(course_id=7004),  # Default True
        ]
        
        db_session.add_all(courses)
        db_session.commit()
        
        tracked = CourseMetadata.get_tracked_courses(db_session)
        assert len(tracked) == 3  # 7001, 7003, 7004
        
        course_ids = [c.course_id for c in tracked]
        assert 7001 in course_ids
        assert 7003 in course_ids
        assert 7004 in course_ids
        assert 7002 not in course_ids
    
    def test_get_high_workload_courses(self, db_session):
        """Test querying high workload courses."""
        courses = [
            CourseMetadata(course_id=8001, course_hours=30),
            CourseMetadata(course_id=8002, course_hours=50),
            CourseMetadata(course_id=8003, course_hours=100),
            CourseMetadata(course_id=8004, course_hours=40),  # Equal to default threshold
            CourseMetadata(course_id=8005),  # No hours set
        ]
        
        db_session.add_all(courses)
        db_session.commit()
        
        # Default threshold (40 hours)
        high_workload = CourseMetadata.get_high_workload_courses(db_session)
        assert len(high_workload) == 3  # 50, 100, 40 hours (>=40)
        
        course_ids = [c.course_id for c in high_workload]
        assert 8002 in course_ids
        assert 8003 in course_ids
        assert 8004 in course_ids
        
        # Custom threshold
        very_high_workload = CourseMetadata.get_high_workload_courses(db_session, min_hours=60)
        assert len(very_high_workload) == 1  # Only 100 hours
        assert very_high_workload[0].course_id == 8003


class TestLayer3Integration:
    """Test integration scenarios between Layer 3 models."""
    
    def test_metadata_independence(self, db_session):
        """Test that metadata models can exist independently."""
        # Create metadata without corresponding Canvas objects
        student_meta = StudentMetadata(
            student_id=9001,
            notes="Student metadata without Canvas student",
            custom_group_id="orphan_group"
        )
        
        assignment_meta = AssignmentMetadata(
            assignment_id=9002,
            user_notes="Assignment metadata without Canvas assignment",
            difficulty_rating=5
        )
        
        course_meta = CourseMetadata(
            course_id=9003,
            user_notes="Course metadata without Canvas course",
            tracking_enabled=False
        )
        
        db_session.add_all([student_meta, assignment_meta, course_meta])
        db_session.commit()
        
        # Verify all saved successfully
        assert StudentMetadata.get_by_student_id(db_session, 9001) is not None
        assert AssignmentMetadata.get_by_assignment_id(db_session, 9002) is not None
        assert CourseMetadata.get_by_course_id(db_session, 9003) is not None
    
    def test_metadata_persistence(self, db_session):
        """Test that metadata persists across sessions."""
        # Create initial metadata
        student_meta = StudentMetadata(
            student_id=9004,
            notes="Initial notes",
            custom_group_id="test_group"
        )
        student_meta.add_tag("initial-tag")
        
        db_session.add(student_meta)
        db_session.commit()
        
        # Modify metadata
        saved_meta = StudentMetadata.get_by_student_id(db_session, 9004)
        saved_meta.notes = "Updated notes"
        saved_meta.add_tag("updated-tag")
        saved_meta.custom_group_id = "new_group"
        
        db_session.commit()
        
        # Verify changes persisted
        final_meta = StudentMetadata.get_by_student_id(db_session, 9004)
        assert final_meta.notes == "Updated notes"
        assert final_meta.custom_group_id == "new_group"
        assert "initial-tag" in final_meta.get_tags()
        assert "updated-tag" in final_meta.get_tags()
    
    def test_soft_foreign_key_behavior(self, db_session):
        """Test that metadata uses soft foreign keys (no constraints)."""
        # This test verifies that metadata can reference non-existent Canvas IDs
        # without database constraint violations
        
        # Create metadata with arbitrary Canvas IDs
        arbitrary_ids = [99999, 88888, 77777]
        
        metadata_records = [
            StudentMetadata(student_id=arbitrary_ids[0], notes="Test student"),
            AssignmentMetadata(assignment_id=arbitrary_ids[1], user_notes="Test assignment"),
            CourseMetadata(course_id=arbitrary_ids[2], user_notes="Test course")
        ]
        
        # Should save without foreign key constraint errors
        db_session.add_all(metadata_records)
        db_session.commit()
        
        # Verify all saved
        assert len(db_session.query(StudentMetadata).all()) >= 1
        assert len(db_session.query(AssignmentMetadata).all()) >= 1
        assert len(db_session.query(CourseMetadata).all()) >= 1