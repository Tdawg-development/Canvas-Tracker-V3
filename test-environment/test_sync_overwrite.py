#!/usr/bin/env python3
"""
Test Sync Overwrite Behavior

Verifies that running a Canvas sync multiple times properly updates/overwrites
data rather than creating duplicates.
"""

import sys
import os
import logging
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ['DATABASE_ENV'] = 'test'

from database.operations.canvas_bridge import CanvasDataBridge
from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
from database.session import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def test_sync_overwrite():
    """Test that multiple syncs properly overwrite data."""
    
    print("🔄 Testing Canvas Sync Overwrite Behavior")
    print("=" * 50)
    
    course_id = 7982015
    
    try:
        # Initialize Canvas bridge
        canvas_interface_path = "C:\\Users\\tyler\\Documents\\Canvas-Tracker-V3\\canvas-interface"
        
        sync_config = {
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
        
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        bridge = CanvasDataBridge(canvas_interface_path, session, sync_configuration=sync_config)
        
        # Get initial counts
        print("📊 BEFORE SECOND SYNC:")
        print("-" * 30)
        
        initial_counts = {
            'courses': session.query(CanvasCourse).count(),
            'students': session.query(CanvasStudent).count(),
            'assignments': session.query(CanvasAssignment).count(),
            'enrollments': session.query(CanvasEnrollment).count()
        }
        
        print(f"  Courses: {initial_counts['courses']}")
        print(f"  Students: {initial_counts['students']}")
        print(f"  Assignments: {initial_counts['assignments']}")
        print(f"  Enrollments: {initial_counts['enrollments']}")
        
        # Get some specific records with their last_synced timestamps
        course_before = session.query(CanvasCourse).filter_by(id=course_id).first()
        student_before = session.query(CanvasStudent).first()
        assignment_before = session.query(CanvasAssignment).first()
        
        before_timestamps = {
            'course_last_synced': course_before.last_synced if course_before else None,
            'student_last_synced': student_before.last_synced if student_before else None,
            'assignment_last_synced': assignment_before.last_synced if assignment_before else None
        }
        
        print(f"\n📅 Sample Last Synced Timestamps (Before):")
        print(f"  Course: {before_timestamps['course_last_synced']}")
        print(f"  Student: {before_timestamps['student_last_synced']}")
        print(f"  Assignment: {before_timestamps['assignment_last_synced']}")
        
        # Run second sync
        print(f"\n🔄 Running SECOND sync for course {course_id}...")
        import asyncio
        result = asyncio.run(bridge.initialize_canvas_course_sync(course_id))
        
        if not result.success:
            print(f"❌ Second sync failed: {'; '.join(result.errors)}")
            return False
        
        print("✅ Second sync completed successfully")
        print(f"   Processing time: {result.total_time:.2f}s")
        print(f"   Objects synced: {result.objects_synced}")
        
        # Get counts after second sync
        print("\n📊 AFTER SECOND SYNC:")
        print("-" * 30)
        
        final_counts = {
            'courses': session.query(CanvasCourse).count(),
            'students': session.query(CanvasStudent).count(),
            'assignments': session.query(CanvasAssignment).count(),
            'enrollments': session.query(CanvasEnrollment).count()
        }
        
        print(f"  Courses: {final_counts['courses']}")
        print(f"  Students: {final_counts['students']}")
        print(f"  Assignments: {final_counts['assignments']}")
        print(f"  Enrollments: {final_counts['enrollments']}")
        
        # Get the same records after sync to check timestamps
        course_after = session.query(CanvasCourse).filter_by(id=course_id).first()
        student_after = session.query(CanvasStudent).first()
        assignment_after = session.query(CanvasAssignment).first()
        
        after_timestamps = {
            'course_last_synced': course_after.last_synced if course_after else None,
            'student_last_synced': student_after.last_synced if student_after else None,
            'assignment_last_synced': assignment_after.last_synced if assignment_after else None
        }
        
        print(f"\n📅 Sample Last Synced Timestamps (After):")
        print(f"  Course: {after_timestamps['course_last_synced']}")
        print(f"  Student: {after_timestamps['student_last_synced']}")
        print(f"  Assignment: {after_timestamps['assignment_last_synced']}")
        
        # Analysis
        print(f"\n📊 SYNC OVERWRITE ANALYSIS:")
        print("=" * 35)
        
        # Check if counts remained the same (no duplicates)
        counts_unchanged = all(
            initial_counts[entity] == final_counts[entity] 
            for entity in initial_counts.keys()
        )
        
        # Check if timestamps were updated (indicating overwrites)
        # Handle timezone comparison by converting to UTC
        def to_utc(dt):
            if dt and dt.tzinfo is None:
                # Naive datetime, assume UTC
                from datetime import timezone
                return dt.replace(tzinfo=timezone.utc)
            return dt
        
        timestamps_updated = all(
            to_utc(after_timestamps[key]) > to_utc(before_timestamps[key])
            for key in before_timestamps.keys()
            if before_timestamps[key] and after_timestamps[key]
        )
        
        print(f"✅ Record Counts Unchanged: {counts_unchanged}")
        print(f"   (No duplicates created)")
        
        print(f"✅ Timestamps Updated: {timestamps_updated}")
        print(f"   (Records were overwritten/updated)")
        
        # Show the sync operation details
        if result.objects_synced:
            created_count = sum(1 for v in result.objects_synced.values() if v > 0)
            print(f"\n🔧 Sync Operation Details:")
            print(f"   Courses: {'updated' if result.objects_synced.get('courses', 0) > 0 else 'unchanged'}")
            print(f"   Students: {'updated' if result.objects_synced.get('students', 0) > 0 else 'unchanged'}")  
            print(f"   Assignments: {'updated' if result.objects_synced.get('assignments', 0) > 0 else 'unchanged'}")
            print(f"   Enrollments: {'updated' if result.objects_synced.get('enrollments', 0) > 0 else 'unchanged'}")
        
        # Overall assessment
        if counts_unchanged and timestamps_updated:
            print(f"\n🎉 SYNC OVERWRITE TEST PASSED!")
            print(f"   ✅ No duplicate records created")
            print(f"   ✅ Existing records properly updated")  
            print(f"   ✅ Sync behavior working correctly")
            return True
        else:
            print(f"\n❌ SYNC OVERWRITE TEST ISSUES:")
            if not counts_unchanged:
                print(f"   ❌ Record counts changed (duplicates created?)")
                for entity in initial_counts:
                    if initial_counts[entity] != final_counts[entity]:
                        print(f"      {entity}: {initial_counts[entity]} -> {final_counts[entity]}")
            if not timestamps_updated:
                print(f"   ❌ Timestamps not updated (records not overwritten?)")
            return False
            
        session.close()
        
    except Exception as e:
        print(f"❌ Sync overwrite test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_sync_overwrite()
    if success:
        print(f"\n✅ Sync overwrite test completed successfully!")
    else:
        print(f"\n❌ Sync overwrite test failed!")
        exit(1)