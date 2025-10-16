#!/usr/bin/env python3
"""
Bulk Canvas Integration Test - Full Pipeline

This script tests the complete Canvas-to-Database integration pipeline for ALL available courses:
1. Sets up test database environment
2. Runs Canvas Data Bridge to sync ALL Canvas courses
3. Verifies data was properly synced to database
4. Shows results for manual inspection

This is an end-to-end bulk integration test that validates the entire
Canvas API → TypeScript → Python → Database workflow for multiple courses.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, List

# Use standardized test database setup (from same directory)
from test_helpers import ensure_test_database, get_test_session
from database.config import get_config
from database.operations.canvas_bridge import CanvasDataBridge
from database.operations.layer1.sync_coordinator import SyncPriority


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('bulk_canvas_integration_test.log')
    ]
)

logger = logging.getLogger(__name__)


async def test_canvas_bridge_status():
    """Test Canvas bridge components and environment."""
    print("=" * 60)
    print("CANVAS BRIDGE STATUS CHECK")
    print("=" * 60)
    
    try:
        with get_test_session() as session:
            # Initialize Canvas bridge
            canvas_interface_path = str(Path(__file__).parent.parent / "canvas-interface")
            bridge = CanvasDataBridge(canvas_interface_path, session)
            
            # Get bridge status
            status = bridge.get_bridge_status()
            
            print(f"Canvas Interface Path: {status['canvas_interface_path']}")
            print(f"Path Exists: {status['path_exists']}")
            print(f"Environment Valid: {status['environment_valid']}")
            
            if status['environment_errors']:
                print(f"Environment Errors:")
                for error in status['environment_errors']:
                    print(f"  - {error}")
                    
            if status['environment_warnings']:
                print(f"Environment Warnings:")
                for warning in status['environment_warnings']:
                    print(f"  - {warning}")
                    
            print(f"\nComponents:")
            for name, component in status.get('components', {}).items():
                print(f"  - {name}: {component}")
                
            return status['environment_valid']
            
    except Exception as e:
        logger.error(f"Bridge status check failed: {e}")
        print(f"ERROR: Bridge status check failed: {e}")
        return False


async def test_bulk_canvas_integration():
    """Test complete bulk Canvas-to-Database integration pipeline."""
    print("=" * 60)
    print("BULK CANVAS INTEGRATION TEST - ALL COURSES")
    print("=" * 60)
    
    try:
        with get_test_session() as session:
            print("Initializing Canvas Data Bridge for bulk sync...")
            
            # Initialize Canvas bridge with ANALYTICS configuration to include last_activity fields
            canvas_interface_path = str(Path(__file__).parent.parent / "canvas-interface")
            
            # Analytics configuration that enables last_activity field
            analytics_config = {
                'courseInfo': True,
                'students': True,
                'assignments': True,
                'modules': True,
                'grades': True,
                'studentFields': {
                    'basicInfo': True,
                    'scores': True,
                    'analytics': True,  # This enables last_activity_at field
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
            
            print("📊 Using ANALYTICS configuration to enable last_activity field...")
            bridge = CanvasDataBridge(canvas_interface_path, session, sync_configuration=analytics_config)
            
            print("Starting Canvas bulk course sync...")
            start_time = asyncio.get_event_loop().time()
            
            # Execute bulk sync
            result = await bridge.initialize_bulk_canvas_courses_sync(
                priority=SyncPriority.HIGH,
                validate_environment=True
            )
            
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time
            
            # Display results
            print(f"\n" + "=" * 40)
            print("BULK SYNC RESULTS")
            print("=" * 40)
            print(f"Success: {result.success}")
            print(f"Total Time: {total_time:.2f}s")
            
            if result.typescript_execution_time:
                print(f"TypeScript Execution: {result.typescript_execution_time:.2f}s")
            if result.data_transformation_time:
                print(f"Data Transformation: {result.data_transformation_time:.2f}s")
            if result.database_sync_time:
                print(f"Database Sync: {result.database_sync_time:.2f}s")
                
            print(f"\nObjects Synced:")
            for obj_type, count in result.objects_synced.items():
                print(f"  - {obj_type}: {count}")
                
            if result.errors:
                print(f"\nErrors:")
                for error in result.errors:
                    print(f"  - {error}")
                    
            if result.warnings:
                print(f"\nWarnings:")
                for warning in result.warnings:
                    print(f"  - {warning}")
                    
            # Check if ready for frontend development
            print(f"\nReady for Frontend: {result.ready_for_frontend}")
            
            return result
            
    except Exception as e:
        logger.error(f"Bulk Canvas integration test failed: {e}")
        print(f"ERROR: Bulk Canvas integration test failed: {e}")
        
        # Enhanced error reporting for TypeScript execution errors
        if hasattr(e, '__cause__') and e.__cause__:
            print(f"\nUnderlying cause: {e.__cause__}")
            if hasattr(e.__cause__, 'stdout') and e.__cause__.stdout:
                print(f"\nTypeScript STDOUT:")
                print(e.__cause__.stdout)
            if hasattr(e.__cause__, 'stderr') and e.__cause__.stderr:
                print(f"\nTypeScript STDERR:")
                print(e.__cause__.stderr)
            if hasattr(e.__cause__, 'exit_code'):
                print(f"\nExit Code: {e.__cause__.exit_code}")
        
        # Direct error attributes
        if hasattr(e, 'stdout') and e.stdout:
            print(f"\nTypeScript STDOUT:")
            print(e.stdout)
        if hasattr(e, 'stderr') and e.stderr:
            print(f"\nTypeScript STDERR:")
            print(e.stderr)
        if hasattr(e, 'exit_code'):
            print(f"\nExit Code: {e.exit_code}")
        return None


async def verify_bulk_synced_data():
    """Verify that Canvas data was properly synced to the database."""
    print("=" * 60)
    print("DATABASE VERIFICATION - BULK SYNC")
    print("=" * 60)
    
    try:
        with get_test_session() as session:
            from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
            
            # Check all courses data
            courses = session.query(CanvasCourse).all()
            print(f"✅ Total Courses Found: {len(courses)}")
            
            if len(courses) > 0:
                # Show sample courses
                print(f"\n📋 Sample Courses:")
                for i, course in enumerate(courses[:5]):
                    print(f"   {i + 1}. ID: {course.id} - \"{course.name}\" ({course.course_code})")
                if len(courses) > 5:
                    print(f"   ... and {len(courses) - 5} more")
                    
                # Check total students across all courses
                all_students = session.query(CanvasStudent).all()
                print(f"\n✅ Total Students Found: {len(all_students)}")
                
                # Check total assignments across all courses
                all_assignments = session.query(CanvasAssignment).all()
                print(f"✅ Total Assignments Found: {len(all_assignments)}")
                
                # Check total enrollments across all courses
                all_enrollments = session.query(CanvasEnrollment).all()
                print(f"✅ Total Enrollments Found: {len(all_enrollments)}")
                
                # Show detailed breakdown by course
                print(f"\n📊 Course-by-Course Breakdown:")
                course_summary = []
                
                for course in courses:
                    # Count students for this course
                    enrollments = session.query(CanvasEnrollment).filter_by(course_id=course.id).all()
                    student_ids = [e.student_id for e in enrollments]
                    students = session.query(CanvasStudent).filter(CanvasStudent.student_id.in_(student_ids)).all() if student_ids else []
                    
                    # Count assignments for this course
                    assignments = session.query(CanvasAssignment).filter_by(course_id=course.id).all()
                    
                    course_info = {
                        'course': course,
                        'students_count': len(students),
                        'assignments_count': len(assignments),
                        'enrollments_count': len(enrollments)
                    }
                    course_summary.append(course_info)
                    
                    print(f"   • {course.name}: {len(students)} students, {len(assignments)} assignments, {len(enrollments)} enrollments")
                
                # IMPORTANT: Check last_activity field specifically
                print(f"\n🔍 LAST ACTIVITY FIELD VERIFICATION:")
                students_with_activity = 0
                students_without_activity = 0
                
                for student in all_students[:10]:  # Check first 10 students
                    if student.last_activity and student.last_activity != "":
                        students_with_activity += 1
                        print(f"   ✅ {student.name}: {student.last_activity}")
                    else:
                        students_without_activity += 1
                        print(f"   ❌ {student.name}: NULL/EMPTY")
                
                total_checked = students_with_activity + students_without_activity
                if total_checked > 0:
                    success_rate = (students_with_activity / total_checked) * 100
                    print(f"\n📊 Last Activity Summary: {students_with_activity}/{total_checked} ({success_rate:.1f}%) have data")
                    
                    if students_with_activity > 0:
                        print(f"🎉 SUCCESS: last_activity field is working! Found data for {students_with_activity} students")
                    else:
                        print(f"⚠️ WARNING: No students have last_activity data - check configuration")
                
                return {
                    'courses_found': len(courses),
                    'total_students': len(all_students),
                    'total_assignments': len(all_assignments),
                    'total_enrollments': len(all_enrollments),
                    'course_details': course_summary,
                    'last_activity_populated': students_with_activity,
                    'last_activity_missing': students_without_activity
                }
            else:
                print(f"❌ No courses found in database")
                return {'courses_found': 0}
                
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        print(f"ERROR: Database verification failed: {e}")
        return None


def confirm_bulk_sync():
    """Ask user to confirm bulk synchronization."""
    print("\n" + "⚠️" * 20 + " WARNING " + "⚠️" * 20)
    print("You are about to perform a BULK synchronization of ALL available Canvas courses.")
    print("This operation will:")
    print("  • Fetch ALL courses from your Canvas instance")
    print("  • Sync ALL students, assignments, and enrollments for each course")
    print("  • Potentially process hundreds of API calls")
    print("  • Take significant time depending on the number of courses")
    print("  • Use substantial Canvas API quota")
    print("\nThis is different from the single-course test and may take much longer.")
    print("=" * 80)
    
    while True:
        response = input("\nDo you want to proceed with bulk synchronization? (yes/no): ").strip().lower()
        if response in ['yes', 'y']:
            return True
        elif response in ['no', 'n']:
            return False
        else:
            print("Please enter 'yes' or 'no'")


async def main():
    """Main bulk integration test function."""
    print("Canvas Tracker V3 - Bulk Integration Test")
    print("=" * 60)
    
    # Ensure test database is set up
    ensure_test_database()
    
    print("Database Configuration:")
    config = get_config()
    print(f"  Environment: {config.environment}")
    print(f"  Database URL: {config.database_url}")
    print(f"  Is SQLite: {config.is_sqlite()}")
    
    if config.is_sqlite():
        db_path = config.get_database_file_path()
        print(f"  Database File: {db_path}")
        
        # Check if database file exists
        if db_path and Path(db_path).exists():
            size = Path(db_path).stat().st_size
            print(f"  File Size: {size:,} bytes")
        else:
            print(f"  File Status: Will be created on first use")
    
    print()
    
    # Step 1: Check Canvas bridge status
    print("Step 1: Checking Canvas Bridge Status...")
    bridge_valid = await test_canvas_bridge_status()
    print()
    
    if not bridge_valid:
        print("❌ Canvas Bridge environment is not valid.")
        print("Please check the errors above and fix them before running integration tests.")
        print("\nCommon issues:")
        print("- Canvas interface directory not found")
        print("- Node.js/npm not installed") 
        print("- .env file missing with Canvas API credentials")
        return
    
    # Step 2: Confirm bulk operation
    print("Step 2: Confirming Bulk Operation...")
    if not confirm_bulk_sync():
        print("Bulk synchronization cancelled by user")
        return
    
    print(f"✅ User confirmed bulk synchronization")
    print()
    
    # Step 3: Run bulk integration test
    print("Step 3: Running Bulk Canvas Integration...")
    result = await test_bulk_canvas_integration()
    print()
    
    if result and result.success:
        # Step 4: Verify synced data
        print("Step 4: Verifying Bulk Synced Data...")
        verification = await verify_bulk_synced_data()
        print()
        
        if verification and verification.get('courses_found', 0) > 0:
            print("🎉 BULK INTEGRATION TEST SUCCESSFUL!")
            print(f"Successfully synced {verification['courses_found']} Canvas courses to the database.")
            print(f"Data includes:")
            print(f"  • {verification['total_students']} total students")
            print(f"  • {verification['total_assignments']} total assignments") 
            print(f"  • {verification['total_enrollments']} total enrollments")
            
            # Show database location for manual inspection
            if config.is_sqlite():
                db_path = config.get_database_file_path()
                print(f"\n📁 Database file for manual inspection: {db_path}")
                print("You can now open this database in any SQLite viewer to inspect all Canvas data.")
                
            # Show performance summary
            if result.total_time:
                courses_count = verification['courses_found']
                avg_time_per_course = result.total_time / courses_count if courses_count > 0 else 0
                print(f"\n⚡ Performance Summary:")
                print(f"  • Total time: {result.total_time:.2f}s")
                print(f"  • Average per course: {avg_time_per_course:.2f}s")
                print(f"  • Courses processed: {courses_count}")
        else:
            print("❌ Data verification failed - synced data not found in database")
    else:
        print("❌ Bulk Canvas integration test failed")
    
    print("\n" + "=" * 60)
    print("Bulk integration test complete. Check the log file for details: bulk_canvas_integration_test.log")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Bulk integration test failed: {e}", exc_info=True)
        print(f"ERROR: Bulk integration test failed: {e}")
        sys.exit(1)