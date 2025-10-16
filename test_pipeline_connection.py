#!/usr/bin/env python3
"""
Canvas Pipeline Connection Test

This script tests the complete Canvas-to-Database pipeline:
1. Validates environment prerequisites
2. Initializes database tables
3. Executes TypeScript Canvas data retrieval
4. Transforms data using the transformer registry
5. Loads data into Layer 1 database tables

Usage:
    python test_pipeline_connection.py <course_id>

Example:
    python test_pipeline_connection.py 12345
"""

import sys
import os
import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    # Database imports
    from database.session import get_db_manager, get_session, initialize_database
    from database.config import get_config
    from database.operations.canvas_bridge import initialize_canvas_course
    from database.operations.typescript_interface import validate_typescript_environment
    from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
    
except ImportError as e:
    print(f"Failed to import required modules: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('pipeline_test.log')
    ]
)

logger = logging.getLogger(__name__)


def validate_environment() -> bool:
    """Validate that all prerequisites are met."""
    logger.info("🔍 Validating environment prerequisites...")
    
    # Check TypeScript environment
    try:
        ts_validation = validate_typescript_environment()
        if not ts_validation['valid']:
            logger.error("❌ TypeScript environment validation failed:")
            for error in ts_validation['errors']:
                logger.error(f"  - {error}")
            return False
        
        logger.info("✅ TypeScript environment validated")
        logger.info(f"  - Node.js: {ts_validation['node_version']}")
        logger.info(f"  - NPX available: {ts_validation['npx_available']}")
        logger.info(f"  - TSX available: {ts_validation['tsx_available']}")
        
    except Exception as e:
        logger.error(f"❌ Failed to validate TypeScript environment: {e}")
        return False
    
    # Check canvas-interface directory
    canvas_path = project_root / "canvas-interface"
    if not canvas_path.exists():
        logger.error(f"❌ Canvas interface directory not found: {canvas_path}")
        return False
    
    # Check required files
    required_files = [
        "staging/canvas-data-constructor.ts",
        "package.json"
    ]
    
    for file_path in required_files:
        full_path = canvas_path / file_path
        if not full_path.exists():
            logger.error(f"❌ Required file not found: {file_path}")
            return False
    
    logger.info("✅ Canvas interface files validated")
    
    return True


def initialize_test_database() -> bool:
    """Initialize database with Layer 1 tables."""
    logger.info("🗄️ Initializing test database...")
    
    try:
        # Use test environment
        config = get_config('test')
        logger.info(f"Using test database: {config.database_url}")
        
        # Initialize database tables
        initialize_database(config)
        
        logger.info("✅ Test database initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        return False


def test_canvas_data_retrieval(course_id: int) -> Dict[str, Any]:
    """Test Canvas data retrieval via TypeScript interface."""
    logger.info(f"📡 Testing Canvas data retrieval for course {course_id}...")
    
    try:
        from database.operations.typescript_interface import execute_canvas_course_data
        
        # Execute Canvas data constructor
        canvas_data = execute_canvas_course_data(course_id)
        
        if not canvas_data.get('success', False):
            error_info = canvas_data.get('error', {})
            logger.error(f"❌ Canvas data retrieval failed: {error_info.get('message', 'Unknown error')}")
            return canvas_data
        
        logger.info("✅ Canvas data retrieved successfully")
        logger.info(f"  - Course: {canvas_data.get('course', {}).get('name', 'Unknown')}")
        logger.info(f"  - Students: {len(canvas_data.get('students', []))}")
        logger.info(f"  - Modules: {len(canvas_data.get('modules', []))}")
        
        return canvas_data
        
    except Exception as e:
        logger.error(f"❌ Canvas data retrieval failed: {e}")
        return {'success': False, 'error': {'message': str(e)}}


async def test_full_pipeline(course_id: int) -> bool:
    """Test the complete Canvas-to-Database pipeline."""
    logger.info(f"🚀 Testing full pipeline for course {course_id}...")
    
    try:
        # Use test configuration
        config = get_config('test')
        
        with get_session(config) as session:
            # Execute full pipeline using canvas bridge
            result = await initialize_canvas_course(
                course_id=course_id,
                session=session
            )
            
            if not result.success:
                logger.error("❌ Pipeline execution failed:")
                for error in result.errors:
                    logger.error(f"  - {error}")
                return False
            
            logger.info("✅ Pipeline execution successful")
            logger.info(f"  - Total time: {result.total_time:.2f}s")
            logger.info(f"  - TypeScript execution: {result.typescript_execution_time:.2f}s")
            logger.info(f"  - Data transformation: {result.data_transformation_time:.2f}s")
            logger.info(f"  - Database sync: {result.database_sync_time:.2f}s")
            
            # Verify data was loaded
            courses_count = session.query(CanvasCourse).count()
            students_count = session.query(CanvasStudent).count()
            assignments_count = session.query(CanvasAssignment).count()
            enrollments_count = session.query(CanvasEnrollment).count()
            
            logger.info("📊 Data loaded into Layer 1:")
            logger.info(f"  - Courses: {courses_count}")
            logger.info(f"  - Students: {students_count}")
            logger.info(f"  - Assignments: {assignments_count}")
            logger.info(f"  - Enrollments: {enrollments_count}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Full pipeline test failed: {e}")
        return False


def display_loaded_data(course_id: int) -> None:
    """Display a summary of loaded data for verification."""
    logger.info(f"📋 Displaying loaded data for course {course_id}...")
    
    try:
        config = get_config('test')
        
        with get_session(config) as session:
            # Get course info
            course = session.query(CanvasCourse).filter_by(id=course_id).first()
            if course:
                logger.info(f"📚 Course: {course.name} ({course.course_code})")
                logger.info(f"  - Total Students: {course.total_students}")
                logger.info(f"  - Total Assignments: {course.total_assignments}")
                logger.info(f"  - Last Synced: {course.last_synced}")
            
            # Get student sample
            students = session.query(CanvasStudent).limit(5).all()
            if students:
                logger.info(f"👥 Sample Students:")
                for student in students:
                    logger.info(f"  - {student.name} (Current: {student.current_score}%, Final: {student.final_score}%)")
            
            # Get assignment sample
            assignments = session.query(CanvasAssignment).filter_by(course_id=course_id).limit(5).all()
            if assignments:
                logger.info(f"📝 Sample Assignments:")
                for assignment in assignments:
                    points = f"{assignment.points_possible}pts" if assignment.points_possible else "no points"
                    logger.info(f"  - {assignment.name} ({points})")
            
    except Exception as e:
        logger.error(f"❌ Failed to display loaded data: {e}")


async def main():
    """Main test execution."""
    if len(sys.argv) != 2:
        print("Usage: python test_pipeline_connection.py <course_id>")
        print("Example: python test_pipeline_connection.py 12345")
        sys.exit(1)
    
    try:
        course_id = int(sys.argv[1])
    except ValueError:
        logger.error("❌ Course ID must be a valid integer")
        sys.exit(1)
    
    logger.info("🎯 Starting Canvas Pipeline Connection Test")
    logger.info(f"Target Course ID: {course_id}")
    logger.info("=" * 60)
    
    # Step 1: Validate environment
    if not validate_environment():
        logger.error("❌ Environment validation failed - cannot proceed")
        sys.exit(1)
    
    # Step 2: Initialize test database
    if not initialize_test_database():
        logger.error("❌ Database initialization failed - cannot proceed")
        sys.exit(1)
    
    # Step 3: Test Canvas data retrieval (standalone)
    canvas_data = test_canvas_data_retrieval(course_id)
    if not canvas_data.get('success', False):
        logger.error("❌ Canvas data retrieval failed - cannot proceed")
        sys.exit(1)
    
    # Step 4: Test full pipeline
    pipeline_success = await test_full_pipeline(course_id)
    if not pipeline_success:
        logger.error("❌ Full pipeline test failed")
        sys.exit(1)
    
    # Step 5: Display loaded data
    display_loaded_data(course_id)
    
    logger.info("=" * 60)
    logger.info("🎉 Canvas Pipeline Connection Test SUCCESSFUL!")
    logger.info("✅ Your Canvas data is now flowing into Layer 1 database tables")
    logger.info(f"✅ Test log saved to: pipeline_test.log")


if __name__ == "__main__":
    asyncio.run(main())