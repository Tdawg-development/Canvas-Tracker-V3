#!/usr/bin/env python3
"""Quick check for canvas_students table schema and data"""

import sqlite3

def check_students_table():
    conn = sqlite3.connect('test-environment/canvas_tracker_test.db')
    cursor = conn.cursor()
    
    # Get schema
    cursor.execute('SELECT sql FROM sqlite_master WHERE type="table" AND name="canvas_students"')
    schema = cursor.fetchone()
    if schema:
        print('Canvas Students Table Schema:')
        print(schema[0])
        print()
    else:
        print('Table not found')
        return
    
    # Get column info
    cursor.execute('PRAGMA table_info(canvas_students)')
    columns = cursor.fetchall()
    print('Columns:')
    for col in columns:
        print(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL allowed'}")
    print()
    
    # Check sample data focusing on last_activity
    cursor.execute('SELECT student_id, name, last_activity FROM canvas_students LIMIT 5')
    rows = cursor.fetchall()
    print('Sample data (student_id, name, last_activity):')
    for row in rows:
        print(f"  ID: {row[0]}, Name: {row[1]}, Last Activity: {row[2]}")
    
    # Check how many have null last_activity
    cursor.execute('SELECT COUNT(*) FROM canvas_students WHERE last_activity IS NULL')
    null_count = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM canvas_students')
    total_count = cursor.fetchone()[0]
    
    print(f"\nLast Activity Statistics:")
    print(f"  Total students: {total_count}")
    print(f"  NULL last_activity: {null_count}")
    print(f"  Non-NULL last_activity: {total_count - null_count}")
    
    conn.close()

if __name__ == '__main__':
    check_students_table()