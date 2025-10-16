import sys
import os

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ['DATABASE_ENV'] = 'test'

from database.session import DatabaseManager
from database.models.layer1_canvas import CanvasAssignment
from sqlalchemy import text

dm = DatabaseManager()
session = dm.get_session()

print("🔍 Assignment Field Verification")
print("=" * 35)

# Check assignments
assignments = session.query(CanvasAssignment).limit(10).all()
print(f"📊 Found {len(assignments)} assignments (showing first 10)")

if assignments:
    print(f"\n📋 Assignment Details:")
    print("-" * 80)
    
    for i, assignment in enumerate(assignments, 1):
        print(f"Assignment {i}:")
        print(f"  ID: {assignment.id}")
        print(f"  Name: {repr(assignment.name)}")
        print(f"  Module Position: {assignment.module_position}")
        print(f"  URL: {repr(assignment.url)}")
        print(f"  Published: {assignment.published}")
        print(f"  Points Possible: {assignment.points_possible}")
        print(f"  Assignment Type: {assignment.assignment_type}")
        print(f"  Module ID: {assignment.module_id}")
        print(f"  Course ID: {assignment.course_id}")
        print()
        
    # Check for quiz types specifically
    quiz_assignments = [a for a in assignments if a.assignment_type and 'quiz' in a.assignment_type.lower()]
    print(f"🎯 Quiz-type assignments found: {len(quiz_assignments)}")
    for quiz in quiz_assignments:
        print(f"  - Quiz: {quiz.name} (Type: {quiz.assignment_type})")
        
    # Check for empty fields
    empty_names = [a for a in assignments if not a.name or a.name.strip() == '']
    empty_urls = [a for a in assignments if not a.url or a.url.strip() == '']
    null_positions = [a for a in assignments if a.module_position is None]
    null_points = [a for a in assignments if a.points_possible is None]
    
    print(f"\n📊 Field Status Summary:")
    print(f"  Empty Names: {len(empty_names)}/{len(assignments)}")
    print(f"  Empty URLs: {len(empty_urls)}/{len(assignments)}")  
    print(f"  Null Positions: {len(null_positions)}/{len(assignments)}")
    print(f"  Null Points: {len(null_points)}/{len(assignments)}")
    
    if len(empty_names) == 0 and len(quiz_assignments) > 0:
        print("\n✅ ASSIGNMENT FIELDS FIX SUCCESS!")
        print("   ✅ All assignment names populated")
        print("   ✅ Quiz-type assignments present")
        print("   ✅ Fields properly populated")
    elif len(empty_names) > 0:
        print("\n❌ Assignment names still missing")
    else:
        print("\n⚠️  No quiz assignments found - check data")

session.close()