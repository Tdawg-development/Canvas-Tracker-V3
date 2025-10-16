#!/usr/bin/env python3
"""
Debug Calendar Field
Check what data is being passed through the transformation pipeline for the calendar_ics field.
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
from database.session import DatabaseManager

# Configure logging to see debug messages
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def debug_calendar_field():
    """Debug the calendar_ics field transformation and sync."""
    
    print("🔍 Calendar Field Debug")
    print("=" * 40)
    
    # Test course ID
    course_id = 7982015
    
    try:
        # Initialize the Canvas bridge
        canvas_interface_path = "C:\\Users\\tyler\\Documents\\Canvas-Tracker-V3\\canvas-interface"
        
        # Use a simplified configuration that definitely enables courses
        sync_config = {
            'courseInfo': True,
            'students': False,  # Disable to focus on course data
            'assignments': False,
            'modules': False
        }
        
        db_manager = DatabaseManager()
        session = db_manager.get_session()
        bridge = CanvasDataBridge(canvas_interface_path, session, sync_configuration=sync_config)
        
        # Override the _convert_transformation_results method to intercept data
        original_convert = bridge._convert_transformation_results
        def debug_convert(transformation_results):
            print("\n🔍 TRANSFORMATION RESULTS DEBUG:")
            print("=" * 50)
            for entity_type, result in transformation_results.items():
                if entity_type == 'courses' and result.transformed_data:
                    course_data = result.transformed_data[0]
                    print(f"Course data keys: {list(course_data.keys())}")
                    if 'calendar_ics' in course_data:
                        print(f"✅ calendar_ics found: {course_data['calendar_ics'][:80]}...")
                    else:
                        print("❌ calendar_ics NOT found in transformed data")
                    print(f"Full course data: {course_data}")
            return original_convert(transformation_results)
        
        bridge._convert_transformation_results = debug_convert
        
        # Execute sync with debug
        print(f"🔄 Executing sync for course {course_id}...")
        result = await bridge.initialize_canvas_course_sync(course_id)
        
        if not result.success:
            print(f"❌ Sync failed: {'; '.join(result.errors)}")
            return
        
        print("✅ Sync completed")
        
        # Check what's actually in the database
        from database.models.layer1_canvas import CanvasCourse
        course = session.query(CanvasCourse).filter_by(id=course_id).first()
        if course:
            print(f"\n🗃️ DATABASE RESULT:")
            print(f"  calendar_ics: {repr(course.calendar_ics)}")
            print(f"  name: {course.name}")
            print(f"  course_code: {course.course_code}")
        else:
            print("❌ Course not found in database")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Debug failed: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import asyncio
    asyncio.run(debug_calendar_field())