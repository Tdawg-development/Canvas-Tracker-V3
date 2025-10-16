#!/usr/bin/env python3
"""
Test script for the Canvas sync pipeline production functions.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Set test environment
import os
os.environ['DATABASE_ENV'] = 'test'

# Import the production sync functions
from database.operations.canvas_sync_pipeline import (
    run_bulk_canvas_sync, 
    run_single_course_sync,
    verify_canvas_data
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_canvas_sync_pipeline():
    """Test the Canvas sync pipeline functions."""
    print("=" * 60)
    print("TESTING CANVAS SYNC PIPELINE")
    print("=" * 60)
    
    # Setup test database
    print("\n0. Setting up test database...")
    try:
        # Import test database setup
        test_env_path = project_root / "test-environment"
        sys.path.insert(0, str(test_env_path))
        
        from test_helpers import ensure_test_database
        ensure_test_database()
        print("✅ Test database initialized")
    except Exception as e:
        print(f"❌ Failed to setup test database: {e}")
        # Try to initialize database directly
        try:
            from database.session import initialize_database
            initialize_database()
            print("✅ Database tables created directly")
        except Exception as e2:
            print(f"❌ Failed to create database tables: {e2}")
            return False
    
    try:
        print("\n1. Testing bulk Canvas sync...")
        result = run_bulk_canvas_sync()
        
        print(f"\nBulk Sync Results:")
        print(f"  Success: {result.success}")
        print(f"  Total Time: {result.total_time:.2f}s")
        print(f"  Courses Synced: {result.courses_synced}")
        print(f"  Total Students: {result.total_students}")
        print(f"  Total Assignments: {result.total_assignments}")
        print(f"  Total Enrollments: {result.total_enrollments}")
        print(f"  Ready for Frontend: {result.ready_for_frontend}")
        
        if result.errors:
            print(f"  Errors: {result.errors}")
        
        if result.warnings:
            print(f"  Warnings: {result.warnings}")
        
        print("\n2. Verifying Canvas data in database...")
        verification = verify_canvas_data()
        
        print(f"\nData Verification:")
        print(f"  Success: {verification['success']}")
        print(f"  Courses Found: {verification['courses_found']}")
        print(f"  Total Students: {verification['total_students']}")
        print(f"  Total Assignments: {verification['total_assignments']}")
        print(f"  Total Enrollments: {verification['total_enrollments']}")
        
        if verification['course_details']:
            print(f"\n  Course Details:")
            for i, course in enumerate(verification['course_details'][:5], 1):
                print(f"    {i}. {course['name']} ({course['course_code']})")
                print(f"       Students: {course['students_count']}, Assignments: {course['assignments_count']}")
            
            if len(verification['course_details']) > 5:
                print(f"    ... and {len(verification['course_details']) - 5} more courses")
        
        print(f"\n🎉 CANVAS SYNC PIPELINE TEST COMPLETE!")
        
        if result.success and verification['success']:
            print("✅ All tests passed! Canvas sync pipeline is working correctly.")
        else:
            print("❌ Some tests failed. Check the output above for details.")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return result.success if 'result' in locals() else False

if __name__ == "__main__":
    success = test_canvas_sync_pipeline()
    sys.exit(0 if success else 1)