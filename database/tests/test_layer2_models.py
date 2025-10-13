"""
Unit tests for Layer 2 Historical Data Models.

Tests the historical data models that track changes over time:
- GradeHistory: Student grade progression and changes
- AssignmentScore: Detailed assignment score tracking 
- CourseSnapshot: Course-level statistics over time

These models provide append-only historical records that accumulate
during sync operations and enable trend analysis.
"""

import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy.exc import IntegrityError

from database.models.layer2_historical import GradeHistory, AssignmentScore, CourseSnapshot
from database.utils.timezone_handler import CanvasTimezoneHandler, utc_datetime


class TestGradeHistory:
    """Test GradeHistory model functionality."""
    
    def test_grade_history_creation(self, db_session):
        """Test basic grade history record creation."""
        grade_record = GradeHistory(
            student_id=12345,
            course_id=100,
            assignment_id=500,
            current_score=85,
            final_score=90,
            points_earned=85.0,
            points_possible=100.0,
            grade_type='assignment',
            submission_status='submitted'
        )
        
        db_session.add(grade_record)
        db_session.commit()
        
        saved_record = db_session.query(GradeHistory).filter_by(
            student_id=12345, assignment_id=500
        ).first()
        
        assert saved_record is not None
        assert saved_record.current_score == 85
        assert saved_record.final_score == 90
        assert saved_record.points_earned == 85.0
        assert saved_record.points_possible == 100.0
        assert saved_record.grade_type == 'assignment'
        assert saved_record.submission_status == 'submitted'
        assert saved_record.recorded_at is not None  # From HistoricalBaseModel
    
    def test_grade_history_course_level(self, db_session):
        """Test course-level grade history (no assignment_id)."""
        course_grade = GradeHistory(
            student_id=67890,
            course_id=200,
            assignment_id=None,  # Course-level grade
            current_score=88,
            final_score=92,
            grade_type='course_current'
        )
        
        db_session.add(course_grade)
        db_session.commit()
        
        saved_record = db_session.query(GradeHistory).filter_by(
            student_id=67890, course_id=200, assignment_id=None
        ).first()
        
        assert saved_record is not None
        assert saved_record.assignment_id is None
        assert saved_record.grade_type == 'course_current'
        assert saved_record.current_score == 88
    
    def test_grade_history_repr_assignment(self, db_session):
        """Test string representation for assignment grade."""
        record_time = utc_datetime(2024, 10, 13, 15, 30)
        grade_record = GradeHistory(
            student_id=111,
            course_id=222,
            assignment_id=333,
            current_score=75,
            recorded_at=record_time
        )
        
        expected = f"<GradeHistory(student:111, assignment:333, score:75, {record_time})>"
        assert repr(grade_record) == expected
    
    def test_grade_history_repr_course(self, db_session):
        """Test string representation for course grade."""
        record_time = utc_datetime(2024, 10, 13, 15, 30)
        course_grade = GradeHistory(
            student_id=444,
            course_id=555,
            assignment_id=None,
            current_score=82,
            grade_type='course_final',
            recorded_at=record_time
        )
        
        expected = f"<GradeHistory(student:444, course:555, course_final:82, {record_time})>"
        assert repr(course_grade) == expected
    
    def test_calculate_score_change(self, db_session):
        """Test score change calculation."""
        # Previous grade record
        previous_grade = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=70
        )
        
        # Current grade record
        current_grade = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=85
        )
        
        # Test improvement
        change = current_grade.calculate_score_change(previous_grade)
        assert change == 15  # 85 - 70
        
        # Test decline
        decline_grade = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=65
        )
        
        change = decline_grade.calculate_score_change(previous_grade)
        assert change == -5  # 65 - 70
    
    def test_calculate_score_change_edge_cases(self, db_session):
        """Test score change calculation edge cases."""
        current_grade = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=85
        )
        
        # No previous record
        assert current_grade.calculate_score_change(None) is None
        
        # Previous record with no score
        previous_no_score = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=None
        )
        assert current_grade.calculate_score_change(previous_no_score) is None
        
        # Current record with no score
        current_no_score = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=None
        )
        previous_with_score = GradeHistory(current_score=80)
        assert current_no_score.calculate_score_change(previous_with_score) is None
    
    def test_is_improvement_and_decline(self, db_session):
        """Test improvement and decline detection."""
        # Test improvement
        improvement_grade = GradeHistory(
            student_id=123,
            course_id=100,
            assignment_id=200,
            current_score=85,
            score_change=10  # Positive change
        )
        assert improvement_grade.is_improvement() is True
        assert improvement_grade.is_decline() is False
        
        # Test decline
        decline_grade = GradeHistory(
            student_id=124,
            course_id=100,
            assignment_id=200,
            current_score=70,
            score_change=-5  # Negative change
        )
        assert decline_grade.is_improvement() is False
        assert decline_grade.is_decline() is True
        
        # Test no change
        no_change_grade = GradeHistory(
            student_id=125,
            course_id=100,
            assignment_id=200,
            current_score=75,
            score_change=0
        )
        assert no_change_grade.is_improvement() is False
        assert no_change_grade.is_decline() is False
    
    def test_get_student_grade_history(self, db_session):
        """Test querying student grade history."""
        now = datetime.now(timezone.utc)
        
        # Create test records
        grades = [
            GradeHistory(student_id=1001, course_id=100, assignment_id=1, current_score=80,
                        recorded_at=now - timedelta(days=3)),
            GradeHistory(student_id=1001, course_id=100, assignment_id=2, current_score=85,
                        recorded_at=now - timedelta(days=2)),
            GradeHistory(student_id=1001, course_id=200, assignment_id=3, current_score=75,
                        recorded_at=now - timedelta(days=1)),
            GradeHistory(student_id=1002, course_id=100, assignment_id=1, current_score=90,
                        recorded_at=now),
        ]
        
        db_session.add_all(grades)
        db_session.commit()
        
        # Test get all grades for student
        all_grades = GradeHistory.get_student_grade_history(db_session, 1001)
        assert len(all_grades) == 3
        # Should be ordered by recorded_at desc (most recent first)
        assert all_grades[0].assignment_id == 3  # Most recent
        
        # Test filter by course
        course_grades = GradeHistory.get_student_grade_history(db_session, 1001, course_id=100)
        assert len(course_grades) == 2
        
        # Test filter by assignment
        assignment_grades = GradeHistory.get_student_grade_history(db_session, 1001, assignment_id=1)
        assert len(assignment_grades) == 1
        assert assignment_grades[0].current_score == 80
        
        # Test limit
        limited_grades = GradeHistory.get_student_grade_history(db_session, 1001, limit=2)
        assert len(limited_grades) == 2
    
    def test_get_grade_trends(self, db_session):
        """Test grade trend analysis."""
        now = datetime.now(timezone.utc)
        
        # Create grade records over time
        grades = [
            GradeHistory(student_id=2001, course_id=300, current_score=70,
                        recorded_at=now - timedelta(days=45)),  # Outside range
            GradeHistory(student_id=2001, course_id=300, current_score=75,
                        recorded_at=now - timedelta(days=25)),  # Within range
            GradeHistory(student_id=2001, course_id=300, current_score=80,
                        recorded_at=now - timedelta(days=15)),  # Within range
            GradeHistory(student_id=2001, course_id=300, current_score=85,
                        recorded_at=now - timedelta(days=5)),   # Within range
            GradeHistory(student_id=2001, course_id=400, current_score=95,
                        recorded_at=now - timedelta(days=10)),  # Different course
        ]
        
        db_session.add_all(grades)
        db_session.commit()
        
        # Get trends for last 30 days
        trends = GradeHistory.get_grade_trends(db_session, 2001, 300, days_back=30)
        assert len(trends) == 3  # Only records within 30 days for course 300
        
        # Should be ordered by recorded_at asc (chronological for trend analysis)
        assert trends[0].current_score == 75  # Oldest in range
        assert trends[1].current_score == 80  # Middle
        assert trends[2].current_score == 85  # Most recent


class TestAssignmentScore:
    """Test AssignmentScore model functionality."""
    
    def test_assignment_score_creation(self, db_session):
        """Test basic assignment score creation."""
        score_record = AssignmentScore(
            student_id=5001,
            course_id=600,
            assignment_id=700,
            score=45.0,
            points_possible=50.0,
            percentage=90,
            submitted_at=utc_datetime(2024, 10, 10, 14, 30),
            due_at=utc_datetime(2024, 10, 10, 16, 0),
            submission_status='on_time',
            graded_at=utc_datetime(2024, 10, 11, 9, 0),
            submission_type='online_text_entry'
        )
        
        db_session.add(score_record)
        db_session.commit()
        
        saved_record = db_session.query(AssignmentScore).filter_by(
            student_id=5001, assignment_id=700
        ).first()
        
        assert saved_record is not None
        assert saved_record.score == 45.0
        assert saved_record.points_possible == 50.0
        assert saved_record.percentage == 90
        assert saved_record.submission_status == 'on_time'
        assert saved_record.submission_type == 'online_text_entry'
        assert saved_record.recorded_at is not None
    
    def test_assignment_score_repr(self, db_session):
        """Test string representation of assignment score."""
        record_time = utc_datetime(2024, 10, 13, 10, 0)
        
        # Test with submitted status
        submitted_score = AssignmentScore(
            student_id=111,
            assignment_id=222,
            score=40.0,
            points_possible=50.0,
            submission_status='submitted',
            recorded_at=record_time
        )
        expected_submitted = f"<AssignmentScore(student:111, assignment:222, score:40.0/50.0 , {record_time})>"
        assert repr(submitted_score) == expected_submitted
        
        # Test with missing status
        missing_score = AssignmentScore(
            student_id=333,
            assignment_id=444,
            score=None,
            points_possible=50.0,
            submission_status='missing',
            recorded_at=record_time
        )
        expected_missing = f"<AssignmentScore(student:333, assignment:444, score:None/50.0 (missing), {record_time})>"
        assert repr(missing_score) == expected_missing
    
    def test_calculate_percentage(self, db_session):
        """Test percentage calculation."""
        # Normal calculation
        score = AssignmentScore(score=45.0, points_possible=50.0)
        assert score.calculate_percentage() == 90  # 45/50 * 100 = 90
        
        # Zero points possible
        zero_points = AssignmentScore(score=10.0, points_possible=0.0)
        assert zero_points.calculate_percentage() is None
        
        # None values
        none_score = AssignmentScore(score=None, points_possible=50.0)
        assert none_score.calculate_percentage() is None
        
        none_possible = AssignmentScore(score=45.0, points_possible=None)
        assert none_possible.calculate_percentage() is None
    
    def test_late_submission_detection(self, db_session):
        """Test late submission detection."""
        due_date = utc_datetime(2024, 10, 10, 16, 0)
        
        # On-time submission
        on_time = AssignmentScore(
            submitted_at=utc_datetime(2024, 10, 10, 15, 30),
            due_at=due_date
        )
        assert on_time.is_late_submission() is False
        
        # Late submission
        late = AssignmentScore(
            submitted_at=utc_datetime(2024, 10, 10, 17, 0),
            due_at=due_date
        )
        assert late.is_late_submission() is True
        
        # Missing dates
        no_dates = AssignmentScore(submitted_at=None, due_at=None)
        assert no_dates.is_late_submission() is False
    
    def test_missing_assignment_detection(self, db_session):
        """Test missing assignment detection."""
        missing = AssignmentScore(submission_status='missing')
        assert missing.is_missing_assignment() is True
        
        submitted = AssignmentScore(submission_status='submitted')
        assert submitted.is_missing_assignment() is False
    
    def test_days_late_calculation(self, db_session):
        """Test calculation of days late."""
        due_date = utc_datetime(2024, 10, 10, 16, 0)
        
        # On time - 0 days late
        on_time = AssignmentScore(
            submitted_at=utc_datetime(2024, 10, 10, 15, 0),
            due_at=due_date
        )
        assert on_time.days_late() == 0
        
        # 2 days late
        late_2_days = AssignmentScore(
            submitted_at=utc_datetime(2024, 10, 12, 17, 0),
            due_at=due_date
        )
        assert late_2_days.days_late() == 2
    
    def test_get_assignment_scores(self, db_session):
        """Test querying assignment scores."""
        now = datetime.now(timezone.utc)
        
        # Create test scores
        scores = [
            AssignmentScore(student_id=3001, course_id=100, assignment_id=800, score=40.0,
                           recorded_at=now - timedelta(days=3)),
            AssignmentScore(student_id=3002, course_id=100, assignment_id=800, score=45.0,
                           recorded_at=now - timedelta(days=2)),
            AssignmentScore(student_id=3001, course_id=100, assignment_id=801, score=35.0,
                           recorded_at=now - timedelta(days=1)),
        ]
        
        db_session.add_all(scores)
        db_session.commit()
        
        # Get all scores for assignment
        all_scores = AssignmentScore.get_assignment_scores(db_session, 800)
        assert len(all_scores) == 2
        # Should be ordered by recorded_at desc
        assert all_scores[0].student_id == 3002  # Most recent
        
        # Get scores for specific student
        student_scores = AssignmentScore.get_assignment_scores(db_session, 800, student_id=3001)
        assert len(student_scores) == 1
        assert student_scores[0].score == 40.0
    
    def test_get_recent_score_changes(self, db_session):
        """Test querying recent score changes."""
        now = datetime.now(timezone.utc)
        
        # Create test scores with changes
        scores = [
            AssignmentScore(student_id=4001, course_id=100, assignment_id=900, score=40.0, grade_changed=True,
                           recorded_at=now - timedelta(days=2)),   # Within range, changed
            AssignmentScore(student_id=4002, course_id=100, assignment_id=900, score=45.0, grade_changed=False,
                           recorded_at=now - timedelta(days=1)),   # Within range, not changed
            AssignmentScore(student_id=4003, course_id=100, assignment_id=900, score=50.0, grade_changed=True,
                           recorded_at=now - timedelta(days=10)),  # Outside range, changed
        ]
        
        db_session.add_all(scores)
        db_session.commit()
        
        # Get recent changes (last 7 days)
        recent_changes = AssignmentScore.get_recent_score_changes(db_session, days_back=7)
        assert len(recent_changes) == 1  # Only one within range that changed
        assert recent_changes[0].student_id == 4001
        
        # Filter by student
        student_changes = AssignmentScore.get_recent_score_changes(db_session, student_id=4001, days_back=7)
        assert len(student_changes) == 1
        assert student_changes[0].student_id == 4001
    
    def test_get_missing_assignments(self, db_session):
        """Test querying missing assignments."""
        # Create test scores
        scores = [
            AssignmentScore(student_id=5001, course_id=100, assignment_id=1000, 
                           submission_status='missing', due_at=utc_datetime(2024, 10, 15)),
            AssignmentScore(student_id=5001, course_id=100, assignment_id=1001,
                           submission_status='submitted'),
            AssignmentScore(student_id=5001, course_id=200, assignment_id=1002,
                           submission_status='missing', due_at=utc_datetime(2024, 10, 10)),
        ]
        
        db_session.add_all(scores)
        db_session.commit()
        
        # Get all missing assignments for student
        all_missing = AssignmentScore.get_missing_assignments(db_session, 5001)
        assert len(all_missing) == 2
        # Should be ordered by due_at desc
        assert all_missing[0].assignment_id == 1000  # More recent due date
        
        # Filter by course
        course_missing = AssignmentScore.get_missing_assignments(db_session, 5001, course_id=100)
        assert len(course_missing) == 1
        assert course_missing[0].assignment_id == 1000


class TestCourseSnapshot:
    """Test CourseSnapshot model functionality."""
    
    def test_course_snapshot_creation(self, db_session):
        """Test basic course snapshot creation."""
        snapshot = CourseSnapshot(
            course_id=1000,
            total_students=25,
            active_students=23,
            total_assignments=15,
            published_assignments=12,
            graded_assignments=10,
            average_score=82.5,
            median_score=85.0,
            passing_rate=92.0,
            recent_submissions=45,
            pending_grading=8,
            sync_duration=15.7,
            objects_synced=150
        )
        
        db_session.add(snapshot)
        db_session.commit()
        
        saved_snapshot = db_session.query(CourseSnapshot).filter_by(course_id=1000).first()
        
        assert saved_snapshot is not None
        assert saved_snapshot.total_students == 25
        assert saved_snapshot.active_students == 23
        assert saved_snapshot.average_score == 82.5
        assert saved_snapshot.passing_rate == 92.0
        assert saved_snapshot.sync_duration == 15.7
        assert saved_snapshot.recorded_at is not None
    
    def test_course_snapshot_repr(self, db_session):
        """Test string representation of course snapshot."""
        record_time = utc_datetime(2024, 10, 13, 12, 0)
        
        snapshot = CourseSnapshot(
            course_id=2000,
            active_students=30,
            average_score=87.5,
            recorded_at=record_time
        )
        
        expected = f"<CourseSnapshot(course:2000, students:30, avg:87.5, {record_time})>"
        assert repr(snapshot) == expected
    
    def test_calculate_completion_rate(self, db_session):
        """Test assignment completion rate calculation."""
        # Normal calculation
        snapshot = CourseSnapshot(total_assignments=20, graded_assignments=15)
        assert snapshot.calculate_completion_rate() == 75.0  # 15/20 * 100
        
        # No assignments
        no_assignments = CourseSnapshot(total_assignments=0, graded_assignments=0)
        assert no_assignments.calculate_completion_rate() == 0.0
    
    def test_is_healthy_course(self, db_session):
        """Test course health check."""
        # Healthy course
        healthy = CourseSnapshot(
            active_students=20,
            recent_submissions=15,
            average_score=75.0
        )
        assert healthy.is_healthy_course() is True
        
        # No active students
        no_students = CourseSnapshot(
            active_students=0,
            recent_submissions=15,
            average_score=75.0
        )
        assert no_students.is_healthy_course() is False
        
        # No recent activity
        no_activity = CourseSnapshot(
            active_students=20,
            recent_submissions=0,
            average_score=75.0
        )
        assert no_activity.is_healthy_course() is False
        
        # Low average score
        low_scores = CourseSnapshot(
            active_students=20,
            recent_submissions=15,
            average_score=40.0
        )
        assert low_scores.is_healthy_course() is False
        
        # Missing average score
        no_average = CourseSnapshot(
            active_students=20,
            recent_submissions=15,
            average_score=None
        )
        assert no_average.is_healthy_course() is False
    
    def test_get_course_history(self, db_session):
        """Test querying course history."""
        now = datetime.now(timezone.utc)
        
        # Create historical snapshots
        snapshots = [
            CourseSnapshot(course_id=3000, average_score=80.0,
                          recorded_at=now - timedelta(days=10)),
            CourseSnapshot(course_id=3000, average_score=82.0,
                          recorded_at=now - timedelta(days=5)),
            CourseSnapshot(course_id=3000, average_score=85.0,
                          recorded_at=now),
            CourseSnapshot(course_id=3001, average_score=90.0,
                          recorded_at=now - timedelta(days=3)),  # Different course
        ]
        
        db_session.add_all(snapshots)
        db_session.commit()
        
        # Get history for specific course
        history = CourseSnapshot.get_course_history(db_session, 3000)
        assert len(history) == 3
        # Should be ordered by recorded_at desc (most recent first)
        assert history[0].average_score == 85.0  # Most recent
        assert history[1].average_score == 82.0
        assert history[2].average_score == 80.0
        
        # Test limit
        limited_history = CourseSnapshot.get_course_history(db_session, 3000, limit=2)
        assert len(limited_history) == 2
    
    def test_get_trend_data(self, db_session):
        """Test getting trend data for course."""
        now = datetime.now(timezone.utc)
        
        # Create snapshots over time
        snapshots = [
            CourseSnapshot(course_id=4000, average_score=75.0,
                          recorded_at=now - timedelta(days=45)),  # Outside range
            CourseSnapshot(course_id=4000, average_score=78.0,
                          recorded_at=now - timedelta(days=25)),  # Within range
            CourseSnapshot(course_id=4000, average_score=82.0,
                          recorded_at=now - timedelta(days=15)),  # Within range
            CourseSnapshot(course_id=4000, average_score=85.0,
                          recorded_at=now - timedelta(days=5)),   # Within range
        ]
        
        db_session.add_all(snapshots)
        db_session.commit()
        
        # Get trend data for last 30 days
        trends = CourseSnapshot.get_trend_data(db_session, 4000, days_back=30)
        assert len(trends) == 3  # Only records within 30 days
        
        # Should be ordered by recorded_at asc (chronological for trend analysis)
        assert trends[0].average_score == 78.0  # Oldest in range
        assert trends[1].average_score == 82.0  # Middle
        assert trends[2].average_score == 85.0  # Most recent


class TestLayer2Integration:
    """Test integration scenarios between Layer 2 models."""
    
    def test_historical_data_consistency(self, db_session):
        """Test consistency of historical data across models."""
        now = datetime.now(timezone.utc)
        
        # Create related historical records
        grade_record = GradeHistory(
            student_id=9001,
            course_id=5000,
            assignment_id=6000,
            current_score=88,
            points_earned=44.0,
            points_possible=50.0,
            recorded_at=now
        )
        
        score_record = AssignmentScore(
            student_id=9001,
            course_id=5000,
            assignment_id=6000,
            score=44.0,
            points_possible=50.0,
            percentage=88,
            submission_status='submitted',
            recorded_at=now
        )
        
        course_snapshot = CourseSnapshot(
            course_id=5000,
            total_students=1,
            active_students=1,
            average_score=88.0,
            recorded_at=now
        )
        
        db_session.add_all([grade_record, score_record, course_snapshot])
        db_session.commit()
        
        # Verify data consistency
        assert grade_record.points_earned == score_record.score
        assert grade_record.points_possible == score_record.points_possible
        assert grade_record.current_score == score_record.percentage
        assert course_snapshot.average_score == grade_record.current_score
    
    def test_append_only_behavior(self, db_session):
        """Test that historical models support append-only operations."""
        # Create initial records
        grade1 = GradeHistory(
            student_id=8001,
            course_id=4000,
            assignment_id=5000,
            current_score=75,
            recorded_at=utc_datetime(2024, 10, 1, 10, 0)
        )
        
        grade2 = GradeHistory(
            student_id=8001,
            course_id=4000,
            assignment_id=5000,
            current_score=85,  # Updated score
            recorded_at=utc_datetime(2024, 10, 2, 10, 0)  # Later time
        )
        
        db_session.add_all([grade1, grade2])
        db_session.commit()
        
        # Both records should exist (append-only)
        all_grades = db_session.query(GradeHistory).filter_by(
            student_id=8001, assignment_id=5000
        ).order_by(GradeHistory.recorded_at).all()
        
        assert len(all_grades) == 2
        assert all_grades[0].current_score == 75  # Original record unchanged
        assert all_grades[1].current_score == 85  # New record added
    
    def test_trend_analysis_workflow(self, db_session):
        """Test a complete trend analysis workflow."""
        now = datetime.now(timezone.utc)
        student_id = 7001
        course_id = 3000
        
        # Create grade progression over time
        grade_progression = [
            (now - timedelta(days=20), 65),
            (now - timedelta(days=15), 70),
            (now - timedelta(days=10), 75),
            (now - timedelta(days=5), 80),
            (now, 85)
        ]
        
        for record_time, score in grade_progression:
            grade = GradeHistory(
                student_id=student_id,
                course_id=course_id,
                current_score=score,
                grade_type='course_current',
                recorded_at=record_time
            )
            db_session.add(grade)
        
        db_session.commit()
        
        # Analyze trends
        trends = GradeHistory.get_grade_trends(db_session, student_id, course_id, days_back=30)
        
        assert len(trends) == 5
        # Verify chronological order and improvement
        for i in range(1, len(trends)):
            assert trends[i].current_score >= trends[i-1].current_score  # Improving grades
            # Use timezone handler for proper datetime comparison
            assert CanvasTimezoneHandler.compare_datetimes(
                trends[i-1].recorded_at, trends[i].recorded_at
            ) is False  # Different times
            # Convert both to UTC for direct comparison
            prev_utc = CanvasTimezoneHandler.to_utc(trends[i-1].recorded_at)
            curr_utc = CanvasTimezoneHandler.to_utc(trends[i].recorded_at)
            assert curr_utc > prev_utc  # Chronological order
