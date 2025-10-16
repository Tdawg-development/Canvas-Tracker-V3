#!/usr/bin/env python3
"""
Call the Canvas sync pipeline for a single course.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the production sync functions
from database.operations.canvas_sync_pipeline import run_single_course_sync

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Call the Canvas sync pipeline for a single course."""
    print("🚀 CALLING SINGLE COURSE CANVAS SYNC")
    print("=" * 50)
    
    # Use the first course ID we know works
    course_id = 12972117  # Inspector Skills Matrix
    
    try:
        print(f"Starting Canvas sync for course {course_id}...")
        result = run_single_course_sync(course_id)
        
        print(f"\n✅ SINGLE COURSE SYNC COMPLETED!")
        print(f"Success: {result.success}")
        print(f"Time: {result.total_time:.2f}s")
        print(f"Courses: {result.courses_synced}")
        print(f"Students: {result.total_students}")
        print(f"Assignments: {result.total_assignments}")
        print(f"Enrollments: {result.total_enrollments}")
        print(f"Ready for Frontend: {result.ready_for_frontend}")
        
        if result.errors:
            print(f"\nErrors: {result.errors}")
        
        if result.warnings:
            print(f"\nWarnings: {result.warnings}")
        
        return result.success
        
    except Exception as e:
        print(f"❌ Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)