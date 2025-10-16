#!/usr/bin/env python3
"""
Production Canvas Sync Pipeline

This module provides production-ready callable functions that mimic the functionality
of the test_bulk_canvas_integration.py test. It leverages the existing Canvas-Database
integration infrastructure to provide clean, callable sync operations.

Key Functions:
- sync_all_canvas_courses(): Complete bulk sync of all Canvas courses
- sync_canvas_course(): Sync a single Canvas course
- verify_canvas_data(): Verify synced Canvas data in database

These functions are designed for production use and provide the same functionality
as the integration test without the test-specific elements.
"""

import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime

from sqlalchemy.orm import Session

from .canvas_bridge import CanvasDataBridge, CanvasBridgeResult
from .layer1.sync_coordinator import SyncPriority
from ..session import get_session
from ..config import get_config
from ..models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment


@dataclass
class CanvasSyncResult:
    """Result container for Canvas sync operations."""
    success: bool
    total_time: float
    courses_synced: int
    total_students: int
    total_assignments: int
    total_enrollments: int
    errors: List[str]
    warnings: List[str]
    ready_for_frontend: bool
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary format."""
        return asdict(self)


@dataclass  
class CanvasDataSummary:
    """Summary of Canvas data in the database."""
    courses_count: int
    students_count: int
    assignments_count: int
    enrollments_count: int
    course_details: List[Dict[str, Any]]


# Default analytics configuration that enables all necessary fields
DEFAULT_ANALYTICS_CONFIG = {
    'courseInfo': True,
    'students': True,
    'assignments': True,
    'modules': True,
    'grades': True,
    'studentFields': {
        'basicInfo': True,
        'scores': True,
        'analytics': True,
        'enrollmentDetails': True
    },
    'assignmentFields': {
        'basicInfo': True,
        'timestamps': True,
        'submissions': True,
        'urls': False,
        'moduleInfo': True
    },
    'processing': {
        'enhanceWithTimestamps': True,
        'filterUngradedQuizzes': False,
        'resolveQuizAssignments': True,
        'includeUnpublished': True
    }
}


def get_canvas_interface_path() -> str:
    """Get the Canvas interface path, auto-detecting if needed."""
    default_path = Path(__file__).parent.parent.parent / "canvas-interface"
    return str(default_path)


async def sync_all_canvas_courses(
    session: Optional[Session] = None,
    canvas_interface_path: Optional[str] = None,
    priority: SyncPriority = SyncPriority.HIGH,
    sync_configuration: Optional[Dict[str, Any]] = None,
    validate_environment: bool = True
) -> CanvasSyncResult:
    """
    Sync all available Canvas courses to the database.
    
    This function provides the core functionality from test_bulk_canvas_integration.py
    as a callable production function. It performs a complete bulk sync of all
    Canvas courses using the existing Canvas-Database integration infrastructure.
    
    Args:
        session: Optional database session. Creates new session if None.
        canvas_interface_path: Path to canvas-interface directory. Auto-detected if None.
        priority: Sync operation priority level.
        sync_configuration: Sync configuration. Uses analytics config if None.
        validate_environment: Whether to validate environment before starting.
        
    Returns:
        CanvasSyncResult with comprehensive sync results and data summary.
        
    Raises:
        Exception: If sync operation fails.
    """
    # Setup defaults
    if canvas_interface_path is None:
        canvas_interface_path = get_canvas_interface_path()
    
    if sync_configuration is None:
        sync_configuration = DEFAULT_ANALYTICS_CONFIG.copy()
    
    # Session management
    session_provided = session is not None
    if session is None:
        # Import here to avoid circular imports
        from ..session import get_db_manager
        db_manager = get_db_manager()
        session = db_manager.get_session()
    
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    try:
        logger.info("Starting Canvas bulk course synchronization")
        
        # Ensure database tables exist
        try:
            from ..session import initialize_database
            initialize_database()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.warning(f"Database initialization warning: {e}")
        
        # Initialize Canvas Data Bridge
        bridge = CanvasDataBridge(
            canvas_interface_path=canvas_interface_path,
            session=session,
            sync_configuration=sync_configuration
        )
        
        # Execute bulk sync
        bridge_result = await bridge.initialize_bulk_canvas_courses_sync(
            priority=priority,
            validate_environment=validate_environment
        )
        
        # Verify synced data
        data_summary = get_canvas_data_summary(session)
        
        # Calculate total time
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Create result
        result = CanvasSyncResult(
            success=bridge_result.success,
            total_time=total_time,
            courses_synced=bridge_result.objects_synced.get('courses', 0),
            total_students=data_summary.students_count,
            total_assignments=data_summary.assignments_count,
            total_enrollments=data_summary.enrollments_count,
            errors=bridge_result.errors,
            warnings=bridge_result.warnings,
            ready_for_frontend=bridge_result.ready_for_frontend
        )
        
        if result.success:
            logger.info(f"Canvas bulk sync completed successfully in {total_time:.2f}s")
            logger.info(f"Synced {result.courses_synced} courses with {result.total_students} students")
        else:
            logger.error(f"Canvas bulk sync failed: {'; '.join(result.errors)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Canvas sync pipeline failed: {str(e)}")
        raise
    finally:
        # Only close session if we created it
        if not session_provided:
            session.close()


async def sync_canvas_course(
    course_id: int,
    session: Optional[Session] = None,
    canvas_interface_path: Optional[str] = None,
    priority: SyncPriority = SyncPriority.HIGH,
    sync_configuration: Optional[Dict[str, Any]] = None,
    validate_environment: bool = True
) -> CanvasSyncResult:
    """
    Sync a single Canvas course to the database.
    
    Args:
        course_id: Canvas course ID to sync.
        session: Optional database session. Creates new session if None.
        canvas_interface_path: Path to canvas-interface directory. Auto-detected if None.
        priority: Sync operation priority level.
        sync_configuration: Sync configuration. Uses analytics config if None.
        validate_environment: Whether to validate environment before starting.
        
    Returns:
        CanvasSyncResult with sync results for the single course.
        
    Raises:
        Exception: If sync operation fails.
    """
    # Setup defaults
    if canvas_interface_path is None:
        canvas_interface_path = get_canvas_interface_path()
    
    if sync_configuration is None:
        sync_configuration = DEFAULT_ANALYTICS_CONFIG.copy()
    
    # Session management
    session_provided = session is not None
    if session is None:
        # Import here to avoid circular imports
        from ..session import get_db_manager
        db_manager = get_db_manager()
        session = db_manager.get_session()
    
    logger = logging.getLogger(__name__)
    start_time = datetime.now()
    
    try:
        logger.info(f"Starting Canvas course sync for course {course_id}")
        
        # Ensure database tables exist  
        try:
            from ..session import initialize_database
            initialize_database()
            logger.info("Database tables initialized")
        except Exception as e:
            logger.warning(f"Database initialization warning: {e}")
        
        # Initialize Canvas Data Bridge
        bridge = CanvasDataBridge(
            canvas_interface_path=canvas_interface_path,
            session=session,
            sync_configuration=sync_configuration
        )
        
        # Execute single course sync
        bridge_result = await bridge.initialize_canvas_course_sync(
            course_id=course_id,
            priority=priority,
            validate_environment=validate_environment
        )
        
        # Get updated data summary
        data_summary = get_canvas_data_summary(session)
        
        # Calculate total time
        end_time = datetime.now()
        total_time = (end_time - start_time).total_seconds()
        
        # Create result
        result = CanvasSyncResult(
            success=bridge_result.success,
            total_time=total_time,
            courses_synced=1 if bridge_result.success else 0,
            total_students=bridge_result.objects_synced.get('students', 0),
            total_assignments=bridge_result.objects_synced.get('assignments', 0),
            total_enrollments=bridge_result.objects_synced.get('enrollments', 0),
            errors=bridge_result.errors,
            warnings=bridge_result.warnings,
            ready_for_frontend=bridge_result.ready_for_frontend
        )
        
        if result.success:
            logger.info(f"Canvas course sync completed successfully in {total_time:.2f}s")
        else:
            logger.error(f"Canvas course sync failed: {'; '.join(result.errors)}")
        
        return result
        
    except Exception as e:
        logger.error(f"Canvas course sync failed: {str(e)}")
        raise
    finally:
        # Only close session if we created it
        if not session_provided:
            session.close()


def get_canvas_data_summary(session: Session) -> CanvasDataSummary:
    """
    Get summary of Canvas data in the database.
    
    Args:
        session: Database session to use for queries.
        
    Returns:
        CanvasDataSummary with counts and details of all Canvas data.
    """
    # Get counts
    courses = session.query(CanvasCourse).all()
    students = session.query(CanvasStudent).all()
    assignments = session.query(CanvasAssignment).all()
    enrollments = session.query(CanvasEnrollment).all()
    
    # Build course details
    course_details = []
    for course in courses:
        # Count related data for this course
        course_enrollments = session.query(CanvasEnrollment).filter_by(course_id=course.id).all()
        course_assignments = session.query(CanvasAssignment).filter_by(course_id=course.id).all()
        
        # Get student IDs from enrollments
        student_ids = [e.student_id for e in course_enrollments]
        course_students = session.query(CanvasStudent).filter(
            CanvasStudent.student_id.in_(student_ids)
        ).all() if student_ids else []
        
        course_details.append({
            'id': course.id,
            'name': course.name,
            'course_code': course.course_code,
            'students_count': len(course_students),
            'assignments_count': len(course_assignments),
            'enrollments_count': len(course_enrollments)
        })
    
    return CanvasDataSummary(
        courses_count=len(courses),
        students_count=len(students),
        assignments_count=len(assignments),
        enrollments_count=len(enrollments),
        course_details=course_details
    )


def verify_canvas_data(session: Optional[Session] = None) -> Dict[str, Any]:
    """
    Verify Canvas data in the database and return comprehensive summary.
    
    Args:
        session: Optional database session. Creates new session if None.
        
    Returns:
        Dictionary with verification results and data summary.
    """
    # Session management
    session_provided = session is not None
    if session is None:
        # Import here to avoid circular imports
        from ..session import get_db_manager
        db_manager = get_db_manager()
        session = db_manager.get_session()
    
    try:
        data_summary = get_canvas_data_summary(session)
        
        verification_result = {
            'success': data_summary.courses_count > 0,
            'courses_found': data_summary.courses_count,
            'total_students': data_summary.students_count,
            'total_assignments': data_summary.assignments_count,
            'total_enrollments': data_summary.enrollments_count,
            'course_details': data_summary.course_details
        }
        
        return verification_result
        
    finally:
        # Only close session if we created it
        if not session_provided:
            session.close()


# Convenience functions for easy integration
def run_bulk_canvas_sync(
    sync_configuration: Optional[Dict[str, Any]] = None,
    priority: SyncPriority = SyncPriority.HIGH
) -> CanvasSyncResult:
    """
    Convenience function to run bulk Canvas sync synchronously.
    
    Args:
        sync_configuration: Optional sync configuration.
        priority: Sync operation priority.
        
    Returns:
        CanvasSyncResult with sync results.
    """
    return asyncio.run(sync_all_canvas_courses(
        sync_configuration=sync_configuration,
        priority=priority
    ))


def run_single_course_sync(
    course_id: int,
    sync_configuration: Optional[Dict[str, Any]] = None,
    priority: SyncPriority = SyncPriority.HIGH
) -> CanvasSyncResult:
    """
    Convenience function to run single course sync synchronously.
    
    Args:
        course_id: Canvas course ID to sync.
        sync_configuration: Optional sync configuration.
        priority: Sync operation priority.
        
    Returns:
        CanvasSyncResult with sync results.
    """
    return asyncio.run(sync_canvas_course(
        course_id=course_id,
        sync_configuration=sync_configuration,
        priority=priority
    ))


if __name__ == "__main__":
    # Example usage
    import logging
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("Canvas Sync Pipeline - Production Function")
    print("=" * 50)
    
    try:
        # Run bulk sync
        result = run_bulk_canvas_sync()
        
        print(f"Sync completed: {result.success}")
        print(f"Courses synced: {result.courses_synced}")
        print(f"Total students: {result.total_students}")
        print(f"Total assignments: {result.total_assignments}")
        print(f"Total time: {result.total_time:.2f}s")
        
        if result.errors:
            print(f"Errors: {result.errors}")
        
        if result.warnings:
            print(f"Warnings: {result.warnings}")
            
    except Exception as e:
        print(f"Sync failed: {e}")