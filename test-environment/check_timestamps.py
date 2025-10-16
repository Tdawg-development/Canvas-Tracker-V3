import sys
import os
from datetime import datetime

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ['DATABASE_ENV'] = 'test'

from database.session import DatabaseManager
from database.models.layer1_canvas import CanvasCourse, CanvasAssignment

dm = DatabaseManager()
session = dm.get_session()

print("🕒 Canvas Timestamp Verification")
print("=" * 40)

# Check course timestamps
course = session.query(CanvasCourse).first()
if course:
    print(f"📋 Course Timestamps:")
    print(f"  Created At: {course.created_at}")
    print(f"  Updated At: {course.updated_at}")
    print(f"  Last Synced: {course.last_synced}")
    
    # Check if created_at/updated_at are from today (indicating overwrite)
    today = datetime.now().date()
    created_today = course.created_at and course.created_at.date() == today
    updated_today = course.updated_at and course.updated_at.date() == today
    
    print(f"  Created today? {created_today}")
    print(f"  Updated today? {updated_today}")

# Check assignment timestamps
assignments = session.query(CanvasAssignment).limit(3).all()
print(f"\n📝 Assignment Timestamps (first 3):")
for i, assignment in enumerate(assignments, 1):
    print(f"  Assignment {i}:")
    print(f"    Created At: {assignment.created_at}")
    print(f"    Updated At: {assignment.updated_at}")
    print(f"    Last Synced: {assignment.last_synced}")
    
    # Check if timestamps are from today
    today = datetime.now().date()
    created_today = assignment.created_at and assignment.created_at.date() == today
    updated_today = assignment.updated_at and assignment.updated_at.date() == today
    
    print(f"    Created today? {created_today}")
    print(f"    Updated today? {updated_today}")
    print()

# Overall assessment
print("📊 TIMESTAMP ASSESSMENT:")
print("-" * 30)

# Count assignments with today's timestamps
assignments_created_today = sum(1 for a in assignments if a.created_at and a.created_at.date() == today)
assignments_updated_today = sum(1 for a in assignments if a.updated_at and a.updated_at.date() == today)

if course:
    course_created_today = course.created_at and course.created_at.date() == today
    course_updated_today = course.updated_at and course.updated_at.date() == today
    
    if course_created_today or assignments_created_today > 0:
        print("❌ TIMESTAMPS OVERWRITTEN WITH TODAY'S DATE")
        print("   Canvas created_at timestamps should be preserved")
        if course_created_today:
            print("   - Course created_at shows today's date")
        if assignments_created_today > 0:
            print(f"   - {assignments_created_today} assignments show today's created_at")
    else:
        print("✅ CANVAS TIMESTAMPS PRESERVED")
        print("   created_at and updated_at properly reflect Canvas data")

session.close()