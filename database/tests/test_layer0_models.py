"""
Unit tests for Layer 0 Object Lifecycle Models.

Tests the object lifecycle management models that track Canvas object existence:
- ObjectStatus: Individual Canvas object lifecycle tracking
- EnrollmentStatus: Student-course enrollment lifecycle tracking

These models provide soft-delete functionality and handle object removal
detection without interfering with Canvas sync processes.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
from database.models.layer1_canvas import CanvasCourse, CanvasStudent


class TestObjectStatus:
    """Test ObjectStatus model functionality."""
    
    def test_object_status_creation(self, db_session):
        """Test basic object status creation."""
        status = ObjectStatus(
            object_type="course",
            object_id=12345
        )
        
        db_session.add(status)
        db_session.commit()
        
        saved_status = db_session.query(ObjectStatus).filter_by(
            object_type="course", object_id=12345
        ).first()
        
        assert saved_status is not None
        assert saved_status.object_type == "course"
        assert saved_status.object_id == 12345
        assert saved_status.active is True  # Default active
        assert saved_status.pending_deletion is False  # Default not pending
        assert saved_status.user_data_exists is False  # Default no user data
        assert saved_status.historical_data_exists is False  # Default no history
    
    def test_object_status_repr(self, db_session):
        """Test string representation of object status."""
        active_status = ObjectStatus(object_type="student", object_id=98765)
        expected_active = "<ObjectStatus(student:98765, active)>"
        assert repr(active_status) == expected_active
        
        # Test inactive with pending deletion
        pending_status = ObjectStatus(
            object_type="assignment", 
            object_id=5555,
            active=False,
            pending_deletion=True
        )
        expected_pending = "<ObjectStatus(assignment:5555, inactive (pending deletion))>"
        assert repr(pending_status) == expected_pending
    
    def test_mark_active(self, db_session):
        """Test marking object as active."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        status = ObjectStatus(
            object_type="course",
            object_id=123,
            active=False,
            pending_deletion=True,
            removed_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            removal_reason="Test removal"
        )
        
        status.mark_active(sync_time)
        
        assert status.active is True
        assert status.pending_deletion is False
        assert status.last_seen_sync == sync_time
        assert status.removed_date is None
        assert status.removal_reason is None
    
    def test_mark_removed_without_dependencies(self, db_session):
        """Test marking object as removed when it has no dependencies."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        status = ObjectStatus(
            object_type="assignment",
            object_id=456,
            user_data_exists=False,
            historical_data_exists=False
        )
        
        status.mark_removed(sync_time, "No longer in Canvas")
        
        # Object should be marked inactive immediately (no dependencies)
        assert status.active is False
        assert status.pending_deletion is False
        assert status.removed_date == sync_time
        assert status.removal_reason == "No longer in Canvas"
    
    def test_mark_removed_with_dependencies(self, db_session):
        """Test marking object as removed when it has dependencies."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        status = ObjectStatus(
            object_type="student",
            object_id=789,
            user_data_exists=True,  # Has user metadata
            historical_data_exists=True  # Has historical data
        )
        
        status.mark_removed(sync_time, "Student withdrawn")
        
        # Object should be marked for pending deletion (has dependencies)
        assert status.active is True  # Still active until user approves
        assert status.pending_deletion is True
        assert status.removed_date == sync_time
        assert status.removal_reason == "Student withdrawn"
    
    def test_mark_for_deletion(self, db_session):
        """Test manually marking object for deletion."""
        status = ObjectStatus(object_type="course", object_id=111)
        
        status.mark_for_deletion("User requested deletion")
        
        assert status.pending_deletion is True
        assert status.removal_reason == "User requested deletion"
    
    def test_approve_deletion(self, db_session):
        """Test approving pending deletion."""
        status = ObjectStatus(
            object_type="student",
            object_id=222,
            pending_deletion=True
        )
        
        before_approval = datetime.now(timezone.utc)
        status.approve_deletion()
        after_approval = datetime.now(timezone.utc)
        
        assert status.active is False
        assert status.pending_deletion is False
        assert before_approval <= status.removed_date <= after_approval
    
    def test_cancel_deletion(self, db_session):
        """Test canceling pending deletion."""
        status = ObjectStatus(
            object_type="assignment",
            object_id=333,
            pending_deletion=True,
            removal_reason="Scheduled for cleanup"
        )
        
        status.cancel_deletion()
        
        assert status.pending_deletion is False
        assert status.removal_reason is None
    
    def test_has_dependencies(self, db_session):
        """Test dependency detection logic."""
        # No dependencies
        no_deps = ObjectStatus(
            object_type="course",
            object_id=1,
            user_data_exists=False,
            historical_data_exists=False
        )
        assert not no_deps.has_dependencies()
        
        # Has user data only
        user_data_only = ObjectStatus(
            object_type="student",
            object_id=2,
            user_data_exists=True,
            historical_data_exists=False
        )
        assert user_data_only.has_dependencies()
        
        # Has historical data only
        history_only = ObjectStatus(
            object_type="assignment",
            object_id=3,
            user_data_exists=False,
            historical_data_exists=True
        )
        assert history_only.has_dependencies()
        
        # Has both dependencies
        both_deps = ObjectStatus(
            object_type="student",
            object_id=4,
            user_data_exists=True,
            historical_data_exists=True
        )
        assert both_deps.has_dependencies()
    
    def test_update_dependency_status(self, db_session):
        """Test updating dependency status flags."""
        status = ObjectStatus(object_type="course", object_id=555)
        
        # Update user data flag
        status.update_dependency_status(has_user_data=True)
        assert status.user_data_exists is True
        assert status.historical_data_exists is False  # Should remain unchanged
        
        # Update historical data flag
        status.update_dependency_status(has_historical_data=True)
        assert status.user_data_exists is True  # Should remain unchanged
        assert status.historical_data_exists is True
        
        # Update both at once
        status.update_dependency_status(has_user_data=False, has_historical_data=False)
        assert status.user_data_exists is False
        assert status.historical_data_exists is False
    
    def test_is_removal_candidate(self, db_session):
        """Test removal candidate detection based on inactivity."""
        now = datetime.now(timezone.utc)
        
        # Active object should not be removal candidate
        active_status = ObjectStatus(object_type="course", object_id=1, active=True)
        assert not active_status.is_removal_candidate()
        
        # Recently removed object (within threshold)
        recent_removal = ObjectStatus(
            object_type="student",
            object_id=2,
            active=False,
            removed_date=now - timedelta(days=10)  # 10 days ago
        )
        assert not recent_removal.is_removal_candidate(days_threshold=30)
        
        # Old removal (past threshold)
        old_removal = ObjectStatus(
            object_type="assignment",
            object_id=3,
            active=False,
            removed_date=now - timedelta(days=45)  # 45 days ago
        )
        assert old_removal.is_removal_candidate(days_threshold=30)
    
    def test_get_objects_by_type(self, db_session):
        """Test querying objects by type."""
        # Create test objects
        objects = [
            ObjectStatus(object_type="course", object_id=1, active=True),
            ObjectStatus(object_type="course", object_id=2, active=False),
            ObjectStatus(object_type="student", object_id=3, active=True),
            ObjectStatus(object_type="student", object_id=4, active=True),
        ]
        
        db_session.add_all(objects)
        db_session.commit()
        
        # Test getting active courses only
        active_courses = ObjectStatus.get_objects_by_type(db_session, "course", active_only=True)
        assert len(active_courses) == 1
        assert active_courses[0].object_id == 1
        
        # Test getting all courses
        all_courses = ObjectStatus.get_objects_by_type(db_session, "course", active_only=False)
        assert len(all_courses) == 2
        
        # Test getting active students
        active_students = ObjectStatus.get_objects_by_type(db_session, "student", active_only=True)
        assert len(active_students) == 2
    
    def test_get_pending_deletions(self, db_session):
        """Test querying objects pending deletion."""
        now = datetime.now(timezone.utc)
        
        # Create test objects
        objects = [
            ObjectStatus(object_type="course", object_id=1, pending_deletion=True, 
                        removed_date=now - timedelta(days=1)),
            ObjectStatus(object_type="student", object_id=2, pending_deletion=True,
                        removed_date=now - timedelta(days=2)),
            ObjectStatus(object_type="course", object_id=3, pending_deletion=False),
            ObjectStatus(object_type="assignment", object_id=4, pending_deletion=True,
                        removed_date=now - timedelta(days=3)),
        ]
        
        db_session.add_all(objects)
        db_session.commit()
        
        # Test getting all pending deletions
        all_pending = ObjectStatus.get_pending_deletions(db_session)
        assert len(all_pending) == 3
        # Should be ordered by removed_date desc (most recent first)
        assert all_pending[0].object_id == 1  # Most recent removal
        
        # Test getting pending deletions for specific type
        course_pending = ObjectStatus.get_pending_deletions(db_session, object_type="course")
        assert len(course_pending) == 1
        assert course_pending[0].object_id == 1


class TestEnrollmentStatus:
    """Test EnrollmentStatus model functionality."""
    
    def test_enrollment_status_creation(self, db_session):
        """Test basic enrollment status creation."""
        enrollment_status = EnrollmentStatus(
            student_id=12345,
            course_id=67890
        )
        
        db_session.add(enrollment_status)
        db_session.commit()
        
        saved_status = db_session.query(EnrollmentStatus).filter_by(
            student_id=12345, course_id=67890
        ).first()
        
        assert saved_status is not None
        assert saved_status.student_id == 12345
        assert saved_status.course_id == 67890
        assert saved_status.active is True  # Default active
        assert saved_status.pending_deletion is False  # Default not pending
        assert saved_status.historical_data_exists is False  # Default no history
    
    def test_enrollment_status_repr(self, db_session):
        """Test string representation of enrollment status."""
        active_enrollment = EnrollmentStatus(student_id=111, course_id=222)
        expected_active = "<EnrollmentStatus(student:111, course:222, active)>"
        assert repr(active_enrollment) == expected_active
        
        # Test inactive with pending deletion
        pending_enrollment = EnrollmentStatus(
            student_id=333,
            course_id=444,
            active=False,
            pending_deletion=True
        )
        expected_pending = "<EnrollmentStatus(student:333, course:444, inactive (pending deletion))>"
        assert repr(pending_enrollment) == expected_pending
    
    def test_mark_active(self, db_session):
        """Test marking enrollment as active."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        enrollment_status = EnrollmentStatus(
            student_id=555,
            course_id=666,
            active=False,
            pending_deletion=True,
            removed_date=datetime(2024, 10, 1, tzinfo=timezone.utc),
            removal_reason="Student dropped"
        )
        
        enrollment_status.mark_active(sync_time)
        
        assert enrollment_status.active is True
        assert enrollment_status.pending_deletion is False
        assert enrollment_status.last_seen_sync == sync_time
        assert enrollment_status.removed_date is None
        assert enrollment_status.removal_reason is None
    
    def test_mark_removed_without_history(self, db_session):
        """Test marking enrollment as removed when it has no historical data."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        enrollment_status = EnrollmentStatus(
            student_id=777,
            course_id=888,
            historical_data_exists=False
        )
        
        enrollment_status.mark_removed(sync_time, "Course ended")
        
        # Enrollment should be marked inactive immediately (no history)
        assert enrollment_status.active is False
        assert enrollment_status.pending_deletion is False
        assert enrollment_status.removed_date == sync_time
        assert enrollment_status.removal_reason == "Course ended"
    
    def test_mark_removed_with_history(self, db_session):
        """Test marking enrollment as removed when it has historical data."""
        sync_time = datetime(2024, 10, 13, 15, 30, tzinfo=timezone.utc)
        
        enrollment_status = EnrollmentStatus(
            student_id=999,
            course_id=1111,
            historical_data_exists=True  # Has grade history
        )
        
        enrollment_status.mark_removed(sync_time, "Student transferred")
        
        # Enrollment should be marked for pending deletion (has history)
        assert enrollment_status.active is True  # Still active until user approves
        assert enrollment_status.pending_deletion is True
        assert enrollment_status.removed_date == sync_time
        assert enrollment_status.removal_reason == "Student transferred"
    
    def test_approve_deletion(self, db_session):
        """Test approving pending enrollment deletion."""
        enrollment_status = EnrollmentStatus(
            student_id=1212,
            course_id=1313,
            pending_deletion=True
        )
        
        before_approval = datetime.now(timezone.utc)
        enrollment_status.approve_deletion()
        after_approval = datetime.now(timezone.utc)
        
        assert enrollment_status.active is False
        assert enrollment_status.pending_deletion is False
        assert before_approval <= enrollment_status.removed_date <= after_approval
    
    def test_has_dependencies(self, db_session):
        """Test enrollment dependency detection."""
        # No historical data
        no_history = EnrollmentStatus(
            student_id=1,
            course_id=2,
            historical_data_exists=False
        )
        assert not no_history.has_dependencies()
        
        # Has historical data
        with_history = EnrollmentStatus(
            student_id=3,
            course_id=4,
            historical_data_exists=True
        )
        assert with_history.has_dependencies()
    
    def test_update_dependency_status(self, db_session):
        """Test updating enrollment dependency status."""
        enrollment_status = EnrollmentStatus(student_id=1414, course_id=1515)
        
        enrollment_status.update_dependency_status(has_historical_data=True)
        assert enrollment_status.historical_data_exists is True
        
        enrollment_status.update_dependency_status(has_historical_data=False)
        assert enrollment_status.historical_data_exists is False
    
    def test_get_student_enrollments(self, db_session):
        """Test querying enrollments for a specific student."""
        # Create test enrollments
        enrollments = [
            EnrollmentStatus(student_id=2001, course_id=101, active=True),
            EnrollmentStatus(student_id=2001, course_id=102, active=False),
            EnrollmentStatus(student_id=2001, course_id=103, active=True),
            EnrollmentStatus(student_id=2002, course_id=101, active=True),
        ]
        
        db_session.add_all(enrollments)
        db_session.commit()
        
        # Test getting active enrollments only
        active_enrollments = EnrollmentStatus.get_student_enrollments(db_session, 2001, active_only=True)
        assert len(active_enrollments) == 2
        course_ids = [e.course_id for e in active_enrollments]
        assert 101 in course_ids and 103 in course_ids
        
        # Test getting all enrollments
        all_enrollments = EnrollmentStatus.get_student_enrollments(db_session, 2001, active_only=False)
        assert len(all_enrollments) == 3
    
    def test_get_course_enrollments(self, db_session):
        """Test querying enrollments for a specific course."""
        # Create test enrollments
        enrollments = [
            EnrollmentStatus(student_id=3001, course_id=201, active=True),
            EnrollmentStatus(student_id=3002, course_id=201, active=False),
            EnrollmentStatus(student_id=3003, course_id=201, active=True),
            EnrollmentStatus(student_id=3004, course_id=202, active=True),
        ]
        
        db_session.add_all(enrollments)
        db_session.commit()
        
        # Test getting active enrollments only
        active_enrollments = EnrollmentStatus.get_course_enrollments(db_session, 201, active_only=True)
        assert len(active_enrollments) == 2
        student_ids = [e.student_id for e in active_enrollments]
        assert 3001 in student_ids and 3003 in student_ids
        
        # Test getting all enrollments
        all_enrollments = EnrollmentStatus.get_course_enrollments(db_session, 201, active_only=False)
        assert len(all_enrollments) == 3
    
    def test_get_pending_deletions(self, db_session):
        """Test querying enrollments pending deletion."""
        now = datetime.now(timezone.utc)
        
        # Create test enrollments
        enrollments = [
            EnrollmentStatus(student_id=4001, course_id=301, pending_deletion=True,
                           removed_date=now - timedelta(days=1)),
            EnrollmentStatus(student_id=4002, course_id=301, pending_deletion=True,
                           removed_date=now - timedelta(days=2)),
            EnrollmentStatus(student_id=4003, course_id=302, pending_deletion=False),
            EnrollmentStatus(student_id=4001, course_id=302, pending_deletion=True,
                           removed_date=now - timedelta(days=3)),
        ]
        
        db_session.add_all(enrollments)
        db_session.commit()
        
        # Test getting all pending deletions
        all_pending = EnrollmentStatus.get_pending_deletions(db_session)
        assert len(all_pending) == 3
        # Should be ordered by removed_date desc (most recent first)
        assert all_pending[0].student_id == 4001 and all_pending[0].course_id == 301
        
        # Test filtering by student
        student_pending = EnrollmentStatus.get_pending_deletions(db_session, student_id=4001)
        assert len(student_pending) == 2
        
        # Test filtering by course
        course_pending = EnrollmentStatus.get_pending_deletions(db_session, course_id=301)
        assert len(course_pending) == 2


class TestLayer0Integration:
    """Test integration scenarios between Layer 0 models."""
    
    def test_lifecycle_workflow_without_dependencies(self, db_session):
        """Test complete lifecycle workflow for object without dependencies."""
        sync_time = datetime.now(timezone.utc)
        
        # 1. Create object status when first seen in Canvas
        status = ObjectStatus(object_type="assignment", object_id=7001)
        status.mark_active(sync_time)
        
        db_session.add(status)
        db_session.commit()
        
        # Verify initial state
        assert status.active is True
        assert status.pending_deletion is False
        assert status.last_seen_sync == sync_time
        
        # 2. Object disappears from Canvas (no dependencies)
        removal_time = sync_time + timedelta(days=1)
        status.mark_removed(removal_time, "Assignment removed from Canvas")
        
        db_session.commit()
        
        # Should be immediately marked as inactive (no dependencies)
        assert status.active is False
        assert status.pending_deletion is False
        assert status.removed_date == removal_time
    
    def test_lifecycle_workflow_with_dependencies(self, db_session):
        """Test complete lifecycle workflow for object with dependencies."""
        sync_time = datetime.now(timezone.utc)
        
        # 1. Create object status with dependencies
        status = ObjectStatus(object_type="student", object_id=8001)
        status.mark_active(sync_time)
        status.update_dependency_status(has_user_data=True, has_historical_data=True)
        
        db_session.add(status)
        db_session.commit()
        
        # 2. Object disappears from Canvas (has dependencies)
        removal_time = sync_time + timedelta(days=1)
        status.mark_removed(removal_time, "Student no longer enrolled")
        
        db_session.commit()
        
        # Should be marked for pending deletion (has dependencies)
        assert status.active is True  # Still active until approved
        assert status.pending_deletion is True
        assert status.removed_date == removal_time
        
        # 3. User approves deletion
        status.approve_deletion()
        db_session.commit()
        
        # Now should be inactive
        assert status.active is False
        assert status.pending_deletion is False
    
    def test_object_reactivation_workflow(self, db_session):
        """Test object reactivation when it returns to Canvas."""
        sync_time1 = datetime.now(timezone.utc)
        
        # 1. Object initially active
        status = ObjectStatus(object_type="course", object_id=9001)
        status.mark_active(sync_time1)
        
        db_session.add(status)
        db_session.commit()
        
        # 2. Object disappears and is marked for deletion
        removal_time = sync_time1 + timedelta(days=1)
        status.update_dependency_status(has_user_data=True)  # Add dependency
        status.mark_removed(removal_time, "Course suspended")
        
        db_session.commit()
        assert status.pending_deletion is True
        
        # 3. Object reappears in Canvas
        reactivation_time = removal_time + timedelta(days=5)
        status.mark_active(reactivation_time)
        
        db_session.commit()
        
        # Should be fully reactivated
        assert status.active is True
        assert status.pending_deletion is False
        assert status.last_seen_sync == reactivation_time
        assert status.removed_date is None
        assert status.removal_reason is None
    
    def test_dependency_tracking_accuracy(self, db_session):
        """Test that dependency tracking affects deletion behavior correctly."""
        # Test different dependency combinations
        test_cases = [
            # (has_user_data, has_historical_data, should_be_pending)
            (False, False, False),  # No deps → immediate deletion
            (True, False, True),    # User data only → pending
            (False, True, True),    # History only → pending  
            (True, True, True),     # Both → pending
        ]
        
        for i, (has_user_data, has_historical_data, should_be_pending) in enumerate(test_cases):
            status = ObjectStatus(object_type="test", object_id=i)
            status.update_dependency_status(has_user_data, has_historical_data)
            
            status.mark_removed(reason=f"Test case {i}")
            
            if should_be_pending:
                assert status.pending_deletion is True, f"Test case {i} should be pending"
                assert status.active is True, f"Test case {i} should remain active"
            else:
                assert status.pending_deletion is False, f"Test case {i} should not be pending"
                assert status.active is False, f"Test case {i} should be inactive"