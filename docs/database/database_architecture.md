# Canvas Tracker V3 - Database Architecture

## Overview
Multi-layer SQLite database architecture designed to separate Canvas-synced data from persistent user data, with object lifecycle management and historical tracking capabilities for student progress analysis.

## Database Layers

### Layer 0: Object Lifecycle Management
Tracks the existence and status of Canvas objects across sync operations. Maintains active/inactive state and handles removal detection without interfering with Canvas sync processes.

### Layer 1: Canvas Data (Pure Sync)
Core entities fetched from Canvas API exactly as provided. These tables are completely replaced during full sync operations with no lifecycle tracking mixed in.

### Layer 2: Historical Data (Sync-Generated)
Time-series data generated from Canvas sync operations. Append-only tables that accumulate student progress and grade changes over time.

### Layer 3: User Data (Persistent)
User-generated metadata that persists across all sync operations. Contains frontend-specific customizations and notes.

---

## Table Definitions

### Layer 0: Object Lifecycle Tables

#### `object_status`
Tracks the lifecycle status of all Canvas objects across sync operations.

```sql
id                     INTEGER PRIMARY KEY    -- Auto-incrementing primary key
object_type            TEXT NOT NULL           -- 'student', 'course', 'assignment'
object_id              INTEGER NOT NULL        -- Canvas ID
active                 BOOLEAN DEFAULT TRUE
pending_deletion       BOOLEAN DEFAULT FALSE
removed_date           TIMESTAMP NULL
last_seen_sync         TIMESTAMP               -- Last sync where object was present
removal_reason         TEXT NULL               -- Why object was marked for removal
user_data_exists       BOOLEAN DEFAULT FALSE   -- Has associated user metadata
historical_data_exists BOOLEAN DEFAULT FALSE   -- Has historical data
created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

#### `enrollment_status`
Tracks student-course enrollment lifecycle separately from Canvas enrollment data.

```sql
id                     INTEGER PRIMARY KEY    -- Auto-incrementing primary key
student_id             INTEGER NOT NULL        -- Canvas student ID
course_id              INTEGER NOT NULL        -- Canvas course ID
active                 BOOLEAN DEFAULT TRUE
pending_deletion       BOOLEAN DEFAULT FALSE
removed_date           TIMESTAMP NULL
last_seen_sync         TIMESTAMP               -- Last sync where enrollment was present
removal_reason         TEXT NULL               -- Why enrollment was removed
historical_data_exists BOOLEAN DEFAULT FALSE   -- Has grade history data
created_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at             TIMESTAMP DEFAULT CURRENT_TIMESTAMP
```

### Layer 1: Canvas Data Tables

#### `canvas_courses`
```sql
id                      INTEGER PRIMARY KEY    -- Canvas course ID
name                    TEXT NOT NULL
total_students          REAL
total_modules           REAL
total_assignments       REAL
published_assignments   REAL
total_points            INT NOT NULL
course_code             TEXT
calendar_ics            TEXT
last_synced             TIMESTAMP
```

#### `canvas_students`
```sql
student_id        INTEGER PRIMARY KEY    -- Canvas student ID (enrollment ID)
user_id           INTEGER
name              TEXT NOT NULL
login_id          TEXT NOT NULL
email             TEXT                   -- Student email address
current_score     INTEGER NOT NULL DEFAULT 0  -- percentage based progress
final_score       INTEGER NOT NULL DEFAULT 0  -- percentage based final score
enrollment_date   TIMESTAMP              -- tracks student course enrollment date
last_activity     TIMESTAMP
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
last_synced       TIMESTAMP
```
```

#### `canvas_assignments`
```sql
id                INTEGER PRIMARY KEY    -- Canvas assignment ID
course_id         INTEGER NOT NULL       -- FK to canvas_courses
module_id         INTEGER NOT NULL       -- links to a module
module_position   REAL                   -- links to position in a module
url               TEXT                   
name              TEXT NOT NULL
type              TEXT                   -- Assignment type --> ASSIGNMENT || QUIZ
published         BOOLEAN
points_possible   REAL
assignment_type   TEXT
last_synced       TIMESTAMP

FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
```

#### `canvas_enrollments`
```sql
student_id        INTEGER NOT NULL       -- FK to canvas_students
course_id         INTEGER NOT NULL       -- FK to canvas_courses
enrollment_date   TIMESTAMP NOT NULL     -- Enrollment creation date
enrollment_status TEXT                   -- 'active', 'inactive', etc.
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
last_synced       TIMESTAMP

PRIMARY KEY (student_id, course_id, enrollment_date)
FOREIGN KEY (student_id) REFERENCES canvas_students(student_id)
FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
```

### Layer 2: Historical Data Tables

#### `grade_history`
Historical record of student grade changes over time.

```sql
id                INTEGER PRIMARY KEY
student_id        INTEGER NOT NULL       -- Canvas student ID
course_id         INTEGER NOT NULL       -- Canvas course ID
assignment_id     INTEGER NULL           -- Canvas assignment ID (null for course grades)
current_score     INTEGER NULL           -- Student's current score (percentage)
final_score       INTEGER NULL           -- Student's potential final score (percentage)
points_earned     REAL NULL              -- Actual points earned on assignment
points_possible   REAL NULL              -- Total points possible for assignment
grade_type        TEXT NOT NULL DEFAULT 'assignment'  -- 'assignment', 'course_current', 'course_final'
submission_status TEXT NULL              -- 'submitted', 'missing', 'late', etc.
previous_score    INTEGER NULL           -- Previous score for change detection
score_change      INTEGER NULL           -- Change since last sync (positive/negative)
recorded_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (student_id) REFERENCES canvas_students(student_id)
FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
FOREIGN KEY (assignment_id) REFERENCES canvas_assignments(id)
```

#### `assignment_scores`
Historical record of individual assignment score changes.

```sql
id                INTEGER PRIMARY KEY
student_id        INTEGER NOT NULL       -- Canvas student ID
course_id         INTEGER NOT NULL       -- Canvas course ID
assignment_id     INTEGER NOT NULL       -- Canvas assignment ID
score             REAL NULL              -- Points earned on assignment
points_possible   REAL NULL              -- Total points possible
percentage        INTEGER NULL           -- Score as percentage (0-100)
submitted_at      TIMESTAMP NULL         -- When assignment was submitted
due_at            TIMESTAMP NULL         -- Assignment due date
submission_status TEXT NOT NULL DEFAULT 'missing'  -- 'submitted', 'missing', 'late', 'on_time'
graded_at         TIMESTAMP NULL         -- When assignment was graded
grade_changed     BOOLEAN NOT NULL DEFAULT FALSE  -- Whether grade changed this sync
previous_score    REAL NULL              -- Previous score for change detection
score_change      REAL NULL              -- Change in points since last sync
submission_type   TEXT NULL              -- 'online_text_entry', 'online_upload', etc.
attempt_number    INTEGER NULL           -- Submission attempt number
recorded_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (student_id) REFERENCES canvas_students(student_id)
FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
FOREIGN KEY (assignment_id) REFERENCES canvas_assignments(id)
```

#### `course_snapshots`
Historical snapshot of course-level statistics and metrics.

```sql
id                    INTEGER PRIMARY KEY
course_id             INTEGER NOT NULL       -- Canvas course ID
total_students        INTEGER NOT NULL DEFAULT 0      -- Total enrolled students
active_students       INTEGER NOT NULL DEFAULT 0      -- Currently active students
total_assignments     INTEGER NOT NULL DEFAULT 0      -- Total assignments in course
published_assignments INTEGER NOT NULL DEFAULT 0      -- Published assignments
graded_assignments    INTEGER NOT NULL DEFAULT 0      -- Assignments with grades
average_score         REAL NULL              -- Course average score
median_score          REAL NULL              -- Course median score
passing_rate          REAL NULL              -- Percentage of passing students
recent_submissions    INTEGER NOT NULL DEFAULT 0      -- Submissions in last 7 days
pending_grading       INTEGER NOT NULL DEFAULT 0      -- Ungraded submissions
sync_duration         REAL NULL              -- How long sync took (seconds)
objects_synced        INTEGER NULL           -- Number of objects synced
recorded_at           TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
```

### Layer 3: User Metadata Tables

#### `student_metadata`
Persistent user-defined data for students.

```sql
student_id        INTEGER PRIMARY KEY                   -- FK to canvas_students
notes             TEXT NULL                             -- User notes about student
custom_tags       TEXT NULL                             -- JSON array of custom tags
custom_group_id   TEXT NULL                             -- Custom group assignment
enrollment_date   TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- User-tracked enrollment date
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (student_id) REFERENCES canvas_students(student_id)
```

#### `assignment_metadata`
Persistent user-defined data for assignments.

```sql
assignment_id     INTEGER PRIMARY KEY     -- FK to canvas_assignments
notes             TEXT NULL               -- User notes about assignment
custom_tags       TEXT NULL               -- JSON array of custom tags
difficulty_rating INTEGER NULL            -- User difficulty rating (1-5)
estimated_hours   REAL NULL               -- Estimated completion time
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (assignment_id) REFERENCES canvas_assignments(id)
```

#### `course_metadata`
Persistent user-defined data for courses.

```sql
course_id         INTEGER PRIMARY KEY     -- FK to canvas_courses
notes             TEXT NULL               -- User notes about course
custom_tags       TEXT NULL               -- JSON array of custom tags
custom_color      TEXT NULL               -- Custom color for course display
course_hours      INTEGER NULL            -- Expected total course hours
tracking_enabled  BOOLEAN NOT NULL DEFAULT TRUE  -- Whether course is actively tracked
created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP

FOREIGN KEY (course_id) REFERENCES canvas_courses(id)
```

---

## Data Flow & Sync Operations

### Full Canvas Sync Process
1. **Replace Layer 1**: Create snapshot of current tables, then complete replacement of Canvas data tables
   - Replace `canvas_courses`
   - Replace `canvas_students` 
   - Replace `canvas_assignments`
   - Replace `canvas_enrollments`
2. **Update Layer 0**: Object lifecycle management
   - Compare new Canvas data with existing `object_status` records
   - Mark objects present in Canvas as `active = TRUE`, update `last_seen_sync`
   - Detect missing objects and classify for removal handling
   - Update `enrollment_status` based on current Canvas enrollments
3. **Append to Layer 2**: Historical data updates
   - Compare current grades with last `grade_history` entries
   - Insert new `grade_history` records where overall grades changed
   - Insert corresponding `assignment_scores` records for changed assignments
4. **Preserve Layer 3**: All user metadata tables remain completely untouched

### Targeted Student Sync Process
1. **Update Layer 1**: Fetch and update specific Canvas data records
2. **Update Layer 0**: Update object lifecycle status for target objects
3. **Append to Layer 2**: Add historical records if changes detected
4. **Preserve Layer 3**: User metadata remains unchanged

### Change Detection Logic
```python
# Grade change detection for course-level tracking
def detect_course_grade_changes(student_id, course_id, current_scores):
    # Get last course-level grade record
    last_record = session.query(GradeHistory).filter(
        GradeHistory.student_id == student_id,
        GradeHistory.course_id == course_id,
        GradeHistory.grade_type.in_(['course_current', 'course_final'])
    ).order_by(GradeHistory.recorded_at.desc()).first()
    
    # Check for current score changes
    current_changed = (not last_record or 
                      last_record.current_score != current_scores['current_score'])
    
    # Check for final score changes
    final_changed = (not last_record or 
                    last_record.final_score != current_scores['final_score'])
    
    return current_changed or final_changed

# Assignment-level change detection
def detect_assignment_score_changes(student_id, assignment_id, new_score_data):
    # Get last assignment score record
    last_score = session.query(AssignmentScore).filter(
        AssignmentScore.student_id == student_id,
        AssignmentScore.assignment_id == assignment_id
    ).order_by(AssignmentScore.recorded_at.desc()).first()
    
    # Compare current score
    score_changed = (not last_score or 
                    last_score.score != new_score_data.get('score'))
    
    # Check submission status change
    status_changed = (not last_score or 
                     last_score.submission_status != new_score_data.get('submission_status'))
    
    return score_changed or status_changed
```

---

## Curriculum Implementation

### Frontend Configuration Approach
Curricula are defined in frontend configuration files, not database tables.

**Example Configuration:**
```json
{
  "curricula": {
    "web_dev_bootcamp": {
      "name": "Web Development Bootcamp",
      "course_ids": [101, 102, 103],
      "color": "#3498db",
      "description": "Full-stack web development track"
      "start_date" : "10/13/2025"
    },
    "data_science_track": {
      "name": "Data Science Track", 
      "course_ids": [201, 202, 301],
      "color": "#e74c3c",
      "description": "Analytics and machine learning focus"
      "start_date" : "09/22/2024"
    }
  }
}
```

### Curriculum Query Pattern
```sql
-- Example: Get all students in Web Dev Bootcamp curriculum
SELECT DISTINCT cs.*, sm.notes, sm.custom_group_id
FROM canvas_students cs
JOIN canvas_enrollments ce ON cs.student_id = ce.student_id
LEFT JOIN student_metadata sm ON cs.student_id = sm.student_id
WHERE ce.course_id IN (101, 102, 103)  -- Web Dev course IDs
```

---

## Data Lifecycle Management

### Handling Removed Objects
Since students, courses, and assignments may be temporarily removed from Canvas but could return later, we implement a soft-delete strategy using Layer 0 object lifecycle tracking with user confirmation for permanent deletion.

#### Layer 0 Lifecycle Implementation
Object lifecycle status is managed entirely in Layer 0 tables, keeping Layer 1 Canvas data pure:

- **`object_status`**: Tracks individual object lifecycle (students, courses, assignments)
- **`enrollment_status`**: Tracks student-course enrollment lifecycle separately
- **Layer 1 remains pure**: Canvas tables contain only current Canvas data
- **Sync separation**: Lifecycle management never interferes with Canvas sync operations

### Removal Detection Process

#### During Layer 0 Updates (After Layer 1 Sync):
1. **Identify Missing Objects**: Compare fresh Canvas data (Layer 1) with existing `object_status` records
2. **Check Dependencies**: Query for associated user metadata (Layer 3) and historical data (Layer 2)
3. **Update Object Status**:
   - Objects with user/historical data → Mark as `pending_deletion = TRUE` in `object_status`
   - Objects without dependencies → Mark as `active = FALSE` immediately
   - Objects still present in Canvas → Update `last_seen_sync`, ensure `active = TRUE`

#### Layer 0 Update Workflow:
```python
def update_object_lifecycle(fresh_canvas_data, sync_timestamp):
    # Get all Canvas object IDs from Layer 1
    current_canvas_objects = extract_object_ids(fresh_canvas_data)
    
    # Update objects present in Canvas
    for obj_type, obj_id in current_canvas_objects:
        update_object_status(obj_type, obj_id, 
                           active=True, 
                           last_seen_sync=sync_timestamp)
    
    # Handle missing objects
    missing_objects = find_missing_objects(current_canvas_objects)
    for obj_type, obj_id in missing_objects:
        if has_dependencies(obj_type, obj_id):
            mark_pending_deletion(obj_type, obj_id, sync_timestamp)
            create_user_notification(obj_type, obj_id)
        else:
            mark_inactive(obj_type, obj_id, sync_timestamp)
```

### User Confirmation Interface

#### Frontend Notifications:
```json
{
  "pending_deletions": [
    {
      "type": "student",
      "name": "John Smith",
      "id": 12345,
      "removed_date": "2025-01-15",
      "user_data": {
        "has_notes": true,
        "has_custom_tags": true,
        "has_group_assignment": true
      },
      "historical_data": {
        "grade_records": 45,
        "assignment_scores": 127,
        "date_range": "2024-09-01 to 2025-01-10"
      },
      "actions": ["keep_inactive", "archive", "delete_permanently"]
    }
  ]
}
```

### Archive Strategy

#### Archive Tables (Optional Long-term Storage):
```sql
CREATE TABLE archived_students AS SELECT * FROM canvas_students WHERE 1=0;
CREATE TABLE archived_student_metadata AS SELECT * FROM student_metadata WHERE 1=0;
CREATE TABLE archived_grade_history AS SELECT * FROM grade_history WHERE 1=0;
CREATE TABLE archived_assignment_scores AS SELECT * FROM assignment_scores WHERE 1=0;
```

#### Archive Process:
```python
def archive_student(student_id, user_decision):
    if user_decision == 'archive':
        # Move to archive tables
        move_to_archive(student_id)
        # Clean up main tables
        cascade_delete(student_id)
    elif user_decision == 'keep_inactive':
        # Keep in main tables but marked inactive
        update_status(student_id, active=False, pending_deletion=False)
    elif user_decision == 'delete_permanently':
        # Full cascade delete
        cascade_delete(student_id)
```

### Re-enrollment Handling

#### Reactivation Process with Layer 0:
```python
def handle_returning_objects(canvas_obj_type, canvas_obj_id, sync_timestamp):
    # Check Layer 0 for existing inactive object
    existing_status = find_object_status(canvas_obj_type, canvas_obj_id)
    
    if existing_status and not existing_status.active:
        # Reactivate in Layer 0
        reactivate_object_status(canvas_obj_type, canvas_obj_id, sync_timestamp)
        # Layer 1 Canvas data gets fresh data automatically
        # Layer 2 Historical data preserved
        # Layer 3 User metadata preserved
        log_reactivation(canvas_obj_type, canvas_obj_id, existing_status.removed_date)
        
    elif not existing_status:
        # Completely new object - create Layer 0 entry
        create_object_status(canvas_obj_type, canvas_obj_id, sync_timestamp)
        # Layer 1 gets the Canvas data
        # Layer 2/3 will accumulate over time
```

#### Benefits of Layer 0 Reactivation:
- **Seamless restoration**: All historical data and user metadata instantly reconnected
- **Audit trail**: Track when objects left and returned to Canvas
- **Data integrity**: No risk of duplicate records or lost connections
- **Performance**: Simple status flag update rather than complex data migration

### Cleanup Automation

#### Automatic Cleanup Rules:
```python
CLEANUP_RULES = {
    'auto_delete_after_days': 90,  # Auto-delete objects inactive for 90+ days with no user data
    'archive_after_days': 365,     # Auto-archive objects inactive for 1+ year
    'notification_frequency': 30   # Remind user of pending deletions every 30 days
}
```

#### Scheduled Cleanup Process:
1. **Daily**: Check for objects past auto-delete threshold without user data
2. **Weekly**: Notify users of pending deletions requiring attention
3. **Monthly**: Archive old inactive records per retention policy

### Application Layer Queries with Layer 0

#### Active Objects Only:
```sql
-- Get all active students with their Canvas data
SELECT cs.*, os.created_at as first_seen, os.last_seen_sync
FROM canvas_students cs
JOIN object_status os ON os.object_type = 'student' AND os.object_id = cs.student_id
WHERE os.active = TRUE;
```

#### Include Inactive Objects:
```sql
-- Get all students (active and inactive) for admin view
SELECT cs.*, os.active, os.removed_date, os.pending_deletion
FROM canvas_students cs
RIGHT JOIN object_status os ON os.object_type = 'student' AND os.object_id = cs.student_id
WHERE os.object_type = 'student';
```

#### Active Enrollments:
```sql
-- Get active student-course relationships
SELECT cs.name as student_name, cc.name as course_name, ce.enrollment_date
FROM canvas_enrollments ce
JOIN canvas_students cs ON ce.student_id = cs.student_id
JOIN canvas_courses cc ON ce.course_id = cc.id
JOIN enrollment_status es ON es.student_id = ce.student_id AND es.course_id = ce.course_id
WHERE es.active = TRUE;
```

#### Pending Deletion Review:
```sql
-- Get objects requiring user review for deletion
SELECT os.object_type, os.object_id, os.removed_date, os.removal_reason,
       CASE os.object_type 
           WHEN 'student' THEN (SELECT name FROM canvas_students WHERE student_id = os.object_id LIMIT 1)
           WHEN 'course' THEN (SELECT name FROM canvas_courses WHERE id = os.object_id LIMIT 1)  
           WHEN 'assignment' THEN (SELECT name FROM canvas_assignments WHERE id = os.object_id LIMIT 1)
       END as object_name,
       os.user_data_exists,
       os.historical_data_exists
FROM object_status os
WHERE os.pending_deletion = TRUE
ORDER BY os.removed_date DESC;
```

---

## Key Design Decisions

### Data Separation Benefits
- **Sync Safety**: Canvas operations never affect user customizations
- **Rollback Capability**: Can restore Canvas data without losing user work
- **Independent Development**: Frontend features can evolve without sync changes

### Historical Tracking Strategy
- **Append-Only**: Never update historical records, always insert new ones
- **Snapshot Integrity**: grade_history_id links assignment scores to specific snapshots
- **Change-Based**: Only record data when actual changes occur (efficient storage)

### Query Optimization
- **Indexes**: Foreign keys, timestamp columns, and curriculum query patterns
- **Views**: Create unified views joining Canvas + metadata for application layer
- **JSON Handling**: Use JSON columns for flexible tagging systems

### Scalability Considerations
- **Target Scale**: 50-100 students, 10-15 courses, ~200 assignments
- **Performance**: Single SQLite database adequate for this scale
- **Growth Path**: Architecture supports migration to PostgreSQL if needed

---

## Implementation Notes

### SQLAlchemy Models
- Use declarative base with relationship mappings
- Implement soft foreign key constraints for data integrity
- Add convenience methods for common query patterns

### Frontend Integration
- Create unified data access layer that joins Canvas + metadata
- Implement caching for curriculum-based queries
- Build change notification system for real-time updates

### Monitoring & Maintenance
- Track sync operation success/failure rates
- Monitor historical table growth patterns
- Implement cleanup procedures for orphaned metadata