import sys
import os

# Add paths
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set test environment
os.environ['DATABASE_ENV'] = 'test'

from database.session import DatabaseManager
from sqlalchemy import text

dm = DatabaseManager()
conn = dm.engine.connect()

# Get all tables
result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
tables = [r[0] for r in result]

print(f"Tables in database: {tables}")

# Check canvas_courses specifically
if 'canvas_courses' in tables:
    columns = conn.execute(text("PRAGMA table_info(canvas_courses)")).fetchall()
    print(f"\ncanvas_courses columns: {[row[1] for row in columns]}")

conn.close()