#!/usr/bin/env python3
"""
Canvas Integration Test - Full Pipeline

This script tests the complete Canvas-to-Database integration pipeline:
1. Sets up test database environment
2. Runs Canvas Data Bridge to sync real Canvas data
3. Verifies data was properly synced to database
4. Shows results for manual inspection

This is an end-to-end integration test that validates the entire
Canvas API → TypeScript → Python → Database workflow.
"""

import os
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

# Use standardized test database setup (from same directory)
from test_helpers import ensure_test_database, get_test_session
from database.config import get_config
from database.operations.canvas_bridge import CanvasDataBridge, initialize_canvas_course
from database.operations.layer1.sync_coordinator import SyncPriority


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('canvas_integration_test.log')
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


async def test_full_canvas_integration(course_id: int):
    """Test complete Canvas-to-Database integration pipeline."""
    print("=" * 60)
    print(f"FULL CANVAS INTEGRATION TEST - COURSE {course_id}")
    print("=" * 60)
    
    try:
        with get_test_session() as session:
            print("Initializing Canvas Data Bridge...")
            
            # Initialize Canvas bridge
            canvas_interface_path = str(Path(__file__).parent.parent / "canvas-interface")
            bridge = CanvasDataBridge(canvas_interface_path, session)
            
            print("Starting Canvas course sync...")
            start_time = asyncio.get_event_loop().time()
            
            # Execute full sync
            result = await bridge.initialize_canvas_course_sync(
                course_id=course_id,
                priority=SyncPriority.HIGH,
                validate_environment=True
            )
            
            end_time = asyncio.get_event_loop().time()
            total_time = end_time - start_time
            
            # Display results
            print(f"\n" + "=" * 40)
            print("SYNC RESULTS")
            print("=" * 40)
            print(f"Success: {result.success}")
            print(f"Course ID: {result.course_id}")
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
        logger.error(f"Canvas integration test failed: {e}")
        print(f"ERROR: Canvas integration test failed: {e}")
        if hasattr(e, 'stdout') and e.stdout:
            print(f"\nTypeScript STDOUT:")
            print(e.stdout)
        if hasattr(e, 'stderr') and e.stderr:
            print(f"\nTypeScript STDERR:")
            print(e.stderr)
        if hasattr(e, 'exit_code'):
            print(f"\nExit Code: {e.exit_code}")
        return None


async def verify_synced_data(course_id: int):
    """Verify that Canvas data was properly synced to the database."""
    print("=" * 60)
    print("DATABASE VERIFICATION")
    print("=" * 60)
    
    try:
        with get_test_session() as session:
            from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
            
            # Check course data
            course = session.query(CanvasCourse).filter_by(id=course_id).first()
            if course:
                print(f"✅ Course Found: {course.name} ({course.course_code})")
                
                # Check students
                enrollments = session.query(CanvasEnrollment).filter_by(course_id=course_id).all()
                student_ids = [e.student_id for e in enrollments]
                students = session.query(CanvasStudent).filter(CanvasStudent.student_id.in_(student_ids)).all()
                
                print(f"✅ Students Found: {len(students)}")
                for student in students[:5]:  # Show first 5
                    print(f"   - {student.name} ({student.login_id})")
                if len(students) > 5:
                    print(f"   ... and {len(students) - 5} more")
                    
                # Check assignments
                assignments = session.query(CanvasAssignment).filter_by(course_id=course_id).all()
                print(f"✅ Assignments Found: {len(assignments)}")
                for assignment in assignments[:5]:  # Show first 5
                    print(f"   - {assignment.name} ({assignment.points_possible} pts)")
                if len(assignments) > 5:
                    print(f"   ... and {len(assignments) - 5} more")
                    
                # Check enrollments
                print(f"✅ Enrollments Found: {len(enrollments)}")
                
                return {
                    'course_found': True,
                    'students_count': len(students),
                    'assignments_count': len(assignments),
                    'enrollments_count': len(enrollments)
                }
            else:
                print(f"❌ Course {course_id} not found in database")
                return {'course_found': False}
                
    except Exception as e:
        logger.error(f"Database verification failed: {e}")
        print(f"ERROR: Database verification failed: {e}")
        return None


def get_test_course_id() -> int:
    """Get test course ID from environment or user input."""
    # Try environment variable first
    env_course_id = os.getenv('TEST_CANVAS_COURSE_ID')
    if env_course_id:
        try:
            return int(env_course_id)
        except ValueError:
            pass
    
    # Check if we have raw course data file with course IDs
    raw_data_files = list(Path('.').glob('raw-course-data-*.txt'))
    if raw_data_files:
        print(f"Found raw course data files: {[f.name for f in raw_data_files]}")
        print("You can extract course IDs from these files for testing")
    
    # Ask user for course ID
    print("\nTo test the Canvas integration, you need a valid Canvas course ID.")
    print("This should be a course you have access to in your Canvas instance.")
    print("Example: If your course URL is https://canvas.university.edu/courses/12345, use 12345")
    
    while True:
        try:
            course_id = input("\nEnter Canvas Course ID (or 'skip' to skip integration test): ").strip()
            if course_id.lower() == 'skip':
                return None
            return int(course_id)
        except ValueError:
            print("Please enter a valid integer course ID")


async def main():
    """Main integration test function."""
    print("Canvas Tracker V3 - Full Integration Test")
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
    
    # Step 2: Get test course ID
    print("Step 2: Getting Test Course ID...")
    course_id = get_test_course_id()
    
    if course_id is None:
        print("Skipping Canvas integration test")
        return
    
    print(f"Using Course ID: {course_id}")
    print()
    
    # Step 3: Run full integration test
    print("Step 3: Running Full Canvas Integration...")
    result = await test_full_canvas_integration(course_id)
    print()
    
    if result and result.success:
        # Step 4: Verify synced data
        print("Step 4: Verifying Synced Data...")
        verification = await verify_synced_data(course_id)
        print()
        
        if verification and verification.get('course_found'):
            print("🎉 INTEGRATION TEST SUCCESSFUL!")
            print(f"Canvas course {course_id} was successfully synced to the database.")
            print(f"Data includes {verification['students_count']} students, ")
            print(f"{verification['assignments_count']} assignments, and ")
            print(f"{verification['enrollments_count']} enrollments.")
            
            # Show database location for manual inspection
            if config.is_sqlite():
                db_path = config.get_database_file_path()
                print(f"\n📁 Database file for manual inspection: {db_path}")
                print("You can now open this database in any SQLite viewer to inspect the Canvas data.")
        else:
            print("❌ Data verification failed - synced data not found in database")
    else:
        print("❌ Canvas integration test failed")
    
    print("\n" + "=" * 60)
    print("Integration test complete. Check the log file for details: canvas_integration_test.log")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        logger.error(f"Integration test failed: {e}", exc_info=True)
        print(f"ERROR: Integration test failed: {e}")
        sys.exit(1)