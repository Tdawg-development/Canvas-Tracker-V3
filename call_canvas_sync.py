#!/usr/bin/env python3
"""
Call the Canvas sync pipeline in production mode.

Usage:
  python call_canvas_sync.py                    # Sync all courses
  python call_canvas_sync.py --all             # Sync all courses
  python call_canvas_sync.py --course 12972117 # Sync specific course
  python call_canvas_sync.py --help            # Show help
"""

import sys
import argparse
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import the production sync functions
from database.operations.canvas_sync_pipeline import run_bulk_canvas_sync, run_single_course_sync

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def sync_all_courses():
    """Sync all Canvas courses."""
    print("🚀 SYNCING ALL CANVAS COURSES")
    print("=" * 50)
    
    try:
        print("Starting bulk Canvas sync...")
        result = run_bulk_canvas_sync()
        
        print("\n✅ BULK SYNC COMPLETED!")
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
        print(f"❌ Bulk sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def sync_single_course(course_id):
    """Sync a single Canvas course."""
    print(f"🚀 SYNCING SINGLE COURSE: {course_id}")
    print("=" * 50)
    
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
        print(f"❌ Single course sync failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(
        description='Canvas Sync Pipeline - Sync Canvas courses to database',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        '--all', 
        action='store_true',
        help='Sync all Canvas courses (default behavior)'
    )
    group.add_argument(
        '--course', 
        type=int,
        metavar='COURSE_ID',
        help='Sync a specific course by ID (e.g., --course 12972117)'
    )
    
    args = parser.parse_args()
    
    # Determine what to sync
    if args.course:
        success = sync_single_course(args.course)
    else:
        # Default to sync all courses
        success = sync_all_courses()
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)