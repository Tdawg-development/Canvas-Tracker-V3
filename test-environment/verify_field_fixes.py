#!/usr/bin/env python3
"""
Field Fix Verification Test

Specifically verifies that the missing data fields have been resolved:
1. last_activity_at for students (should now be populated)
2. calendar_ics for courses (should now be populated)
"""

import os
import sys
import logging
from datetime import datetime

# Add the project paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'database'))

# Configure test environment
os.environ['DATABASE_ENV'] = 'test'

from database.operations.canvas_bridge import CanvasDataBridge
from database.models.layer1_canvas import CanvasCourse, CanvasStudent
from database.session import DatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def verify_field_fixes():
    """Test the fixes for missing last_activity and calendar_ics fields."""
    
    print("🔍 Field Fix Verification Test")
    print("=" * 50)
    
    # Test course ID (from previous successful tests)
    course_id = 7982015
    
    try:
        # Initialize the Canvas bridge with analytics configuration
        print("📋 Initializing Canvas Data Bridge...")
        canvas_interface_path = "C:\\Users\\tyler\\Documents\\Canvas-Tracker-V3\\canvas-interface"
        
        # Configuration that enables analytics (needed for last_activity field)
        sync_config = {
            'courseInfo': True,
            'students': True,
            'assignments': True,
            'modules': True,
            'grades': True,
            'studentFields': {
                'basicInfo': True,
                'scores': True,
                'analytics': True,  # This should enable last_activity field
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
        
        # Sync the course data
        print(f"🔄 Syncing course {course_id} data...")
        import asyncio
        result = asyncio.run(bridge.initialize_canvas_course_sync(course_id))
        
        if not result.success:
            print(f"❌ Course sync failed: {'; '.join(result.errors)}")
            return False
        
        print("✅ Course sync completed successfully")
        
        try:
            print("\n🔍 FIELD VERIFICATION RESULTS")
            print("=" * 40)
            
            # 1. Verify course calendar_ics field
            print("\n1. Course Calendar ICS Field:")
            print("-" * 30)
            
            course = session.query(CanvasCourse).filter_by(id=course_id).first()
            if course:
                if course.calendar_ics and course.calendar_ics.strip():
                    print(f"✅ calendar_ics: POPULATED")
                    print(f"   Value: {course.calendar_ics[:80]}...")
                else:
                    print(f"❌ calendar_ics: NULL or EMPTY")
                    print(f"   Value: {repr(course.calendar_ics)}")
            else:
                print("❌ Course not found in database")
            
            # 2. Verify student last_activity field
            print("\n2. Student Last Activity Field:")
            print("-" * 35)
            
            students = session.query(CanvasStudent).limit(5).all()
            populated_count = 0
            null_count = 0
            
            for student in students:
                if student.last_activity and student.last_activity != "":
                    populated_count += 1
                    print(f"✅ Student {student.name}: {student.last_activity}")
                else:
                    null_count += 1
                    print(f"❌ Student {student.name}: NULL/EMPTY")
            
            print(f"\nSummary: {populated_count} populated, {null_count} null/empty")
            
            # 3. Overall assessment
            print("\n📊 OVERALL ASSESSMENT")
            print("=" * 25)
            
            calendar_fixed = course and course.calendar_ics and course.calendar_ics.strip()
            activity_fixed = populated_count > 0
            
            if calendar_fixed and activity_fixed:
                print("🎉 ALL FIXES SUCCESSFUL!")
                print("   ✅ calendar_ics field populated")
                print("   ✅ last_activity field populated")
                return True
            elif calendar_fixed:
                print("🔧 PARTIAL SUCCESS")
                print("   ✅ calendar_ics field populated")
                print("   ❌ last_activity field still missing")
                return False
            elif activity_fixed:
                print("🔧 PARTIAL SUCCESS")  
                print("   ❌ calendar_ics field still missing")
                print("   ✅ last_activity field populated")
                return False
            else:
                print("❌ FIXES NOT WORKING")
                print("   ❌ calendar_ics field still missing")
                print("   ❌ last_activity field still missing")
                return False
        
        finally:
            session.close()
    
    except Exception as e:
        logger.error(f"Field verification test failed: {str(e)}")
        print(f"❌ Test failed with error: {str(e)}")
        return False

def main():
    """Run the field fix verification test."""
    print("Starting field fix verification test...")
    
    success = verify_field_fixes()
    
    if success:
        print("\n✅ Field fix verification PASSED")
        sys.exit(0)
    else:
        print("\n❌ Field fix verification FAILED")
        sys.exit(1)

if __name__ == "__main__":
    main()