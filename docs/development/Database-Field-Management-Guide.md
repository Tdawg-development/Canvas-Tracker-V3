# Canvas Tracker V3: Database Field Management Guide

> **Complete guide for adding and removing fields in the database pipeline from transformer output to database tables**

## Overview

This guide covers field management in the modernized database-side pipeline with entity transformers and modular architecture. The database pipeline now follows this flow:

```
Field Mapper Output → Entity Transformers → Canvas Bridge → Sync Coordinator → Canvas Operations → Database Models → Database Tables
```

### Key Architectural Changes
- **Entity-specific transformers** in `database/operations/transformers/` for modular field handling
- **TransformerRegistry** system for automatic discovery and extensibility  
- **Configuration-driven transformation** with `TransformationContext`
- **Validation and error handling** built into base transformer classes

## Table of Contents

1. [Database Pipeline Architecture](#database-pipeline-architecture)
2. [Adding New Fields](#adding-new-fields)
3. [Concrete Example: Adding Course `created_at`](#concrete-example-adding-course-created_at)
4. [Removing Fields](#removing-fields)
5. [Database Migrations](#database-migrations)
6. [Testing and Validation](#testing-and-validation)
7. [Advanced Field Types](#advanced-field-types)
8. [Troubleshooting](#troubleshooting)

## Database Pipeline Architecture

### Data Flow Overview

```mermaid
graph TD
    A[Field Mapper Output] --> B[Entity Transformers]
    B --> C[Transformer Registry]
    C --> D[Canvas Data Bridge]
    D --> E[Sync Coordinator]
    E --> F[Canvas Operations]
    F --> G[Database Models]
    G --> H[Database Tables]
    
    I[Migration Scripts] --> H
    J[Transformation Context] --> B
    K[Validation Logic] --> B
    L[Transaction Manager] --> E
```

### Key Components by Stage

| Stage | Files | Purpose |
|-------|-------|---------|
| **Entity Transformers** | `database/operations/transformers/*.py` | Modular transformation by entity type |
| **Transformer Registry** | `database/operations/transformers/base.py` | Discovery and management of transformers |
| **Canvas Bridge** | `database/operations/canvas_bridge.py` | Orchestrates field mapping → Database sync |
| **Sync Coordinator** | `database/operations/layer1/sync_coordinator.py` | Manages full sync operations with conflict resolution |
| **Canvas Operations** | `database/operations/layer1/canvas_ops.py` | CRUD operations with change detection |
| **Database Models** | `database/models/layer1_canvas.py` | SQLAlchemy model definitions |
| **Migration Scripts** | `database/migrations/versions/*.py` | Alembic database migrations |

### Data Processing Layers

1. **Canvas Bridge** - Receives transformer output and coordinates sync
2. **Sync Coordinator** - Handles transaction management and conflict resolution
3. **Canvas Operations** - Performs model-specific CRUD operations
4. **Database Models** - SQLAlchemy models with field definitions
5. **Database Tables** - Physical database storage

## Adding New Fields

### Modern Entity Transformer Process

With the new entity transformer architecture, adding fields is streamlined and modular:

#### Step 1: Update Entity Transformer

**File:** `database/operations/transformers/courses.py` (or appropriate entity transformer)

Add the field to the transformer's optional fields and transformation logic:

```python
class CourseTransformer(EntityTransformer):
    @property
    def optional_fields(self) -> Set[str]:
        return {
            'workflow_state',
            'start_at',
            'end_at',
            'calendar',
            # ADD NEW FIELD HERE
            'created_at',
            # ... other optional fields
        }
    
    def transform_entity(self, entity_data: Dict[str, Any], context: TransformationContext) -> Optional[Dict[str, Any]]:
        # ... existing transformation logic ...
        
        # ADD FIELD TRANSFORMATION
        self._add_optional_field(entity_data, transformed_course, 'created_at', self._parse_canvas_datetime)
        
        return transformed_course
```

#### Step 2: Update Database Model

**File:** `database/models/layer1_canvas.py`

Add the field to the appropriate SQLAlchemy model:

```python
class CanvasCourse(CanvasEntityModel):
    __tablename__ = 'canvas_courses'
    
    # Existing fields...
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, default='')
    course_code = Column(String(100), nullable=True)
    
    # Canvas timestamps - ADD NEW FIELD HERE
    created_at = Column(DateTime, nullable=True)
    start_at = Column(DateTime, nullable=True)
    end_at = Column(DateTime, nullable=True)
```

#### Step 3: Create Database Migration

```bash
# From database/ directory
alembic revision --autogenerate -m "Add created_at field to canvas_courses"
alembic upgrade head
```

### Benefits of the New Entity Transformer Architecture

- **Modular transformation**: Each entity type has its own transformer
- **Built-in validation**: Field type validation and error handling
- **Configuration-driven**: Field filtering based on sync configuration
- **Extensible**: Easy to add new entity types or field transformations
- **Automatic handling**: Canvas Operations layer handles CRUD operations automatically
- **Less manual code**: No need to manually update create/update methods

## Concrete Example: Adding Course `created_at`

Let's walk through the complete process for adding `created_at` to course tracking:

### 1. Update Course Entity Transformer

```python
# database/operations/transformers/courses.py
class CourseTransformer(EntityTransformer):
    @property
    def optional_fields(self) -> Set[str]:
        return {
            'workflow_state',
            'start_at',
            'end_at',
            'calendar',
            'created_at',  # ADD NEW FIELD HERE
            'updated_at',
            # ... other optional fields
        }
    
    def transform_entity(self, entity_data: Dict[str, Any], context: TransformationContext):
        # Build base transformed course
        transformed_course = {
            'id': int(entity_data['id']),
            'name': entity_data.get('name', ''),
            'course_code': entity_data.get('course_code', ''),
            'workflow_state': entity_data.get('workflow_state', 'available'),
            'last_synced': datetime.now(timezone.utc)
        }
        
        # Add optional fields with transformation
        self._add_optional_field(entity_data, transformed_course, 'start_at', self._parse_canvas_datetime)
        self._add_optional_field(entity_data, transformed_course, 'end_at', self._parse_canvas_datetime)
        # ADD NEW FIELD TRANSFORMATION
        self._add_optional_field(entity_data, transformed_course, 'created_at', self._parse_canvas_datetime)
        
        return transformed_course
```

### 2. Update Database Model

```python
# database/models/layer1_canvas.py
class CanvasCourse(CanvasEntityModel):
    __tablename__ = 'canvas_courses'
    
    # Canvas course ID as primary key
    id = Column(Integer, primary_key=True)
    
    # Basic course information
    course_code = Column(String(100), nullable=True)
    calendar_ics = Column(Text, nullable=True)
    
    # Canvas timestamps - ADD NEW FIELD HERE
    created_at = Column(DateTime, nullable=True)     # NEW FIELD
    start_at = Column(DateTime, nullable=True)       # Existing
    end_at = Column(DateTime, nullable=True)         # Existing
    
    # Course statistics
    total_students = Column(Float, nullable=True)
    # ... other fields
```

### 3. Create Database Migration

```bash
# Generate migration
alembic revision --autogenerate -m "Add created_at timestamp to canvas_courses"

# Review the generated migration file
# Then apply it
alembic upgrade head
```

The migration file will look like:

```python
# migrations/versions/add_created_at_to_courses.py
def upgrade():
    op.add_column('canvas_courses', sa.Column('created_at', sa.DateTime(), nullable=True))

def downgrade():
    op.drop_column('canvas_courses', 'created_at')
```

## Removing Fields

### Modern Step-by-Step Process

#### Step 1: Remove from Entity Transformer

**File:** `database/operations/transformers/courses.py` (or appropriate transformer)

Remove field from optional_fields and transformation logic:

```python
class CourseTransformer(EntityTransformer):
    @property
    def optional_fields(self) -> Set[str]:
        return {
            'workflow_state',
            'start_at',
            'end_at',
            # REMOVE THIS FIELD
            # 'deprecated_field',
        }
    
    def transform_entity(self, entity_data, context):
        # ... existing transformation logic ...
        
        # REMOVE ANY TRANSFORMATION CALLS
        # self._add_optional_field(entity_data, transformed_course, 'deprecated_field')
```

#### Step 2: Remove from Database Model

**File:** `database/models/layer1_canvas.py`

Remove the field definition:

```python
class CanvasCourse(CanvasEntityModel):
    __tablename__ = 'canvas_courses'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, default='')
    course_code = Column(String(100), nullable=True)
    
    # REMOVE OR COMMENT OUT
    # deprecated_field = Column(String(255), nullable=True)
```

#### Step 3: Create Migration

```bash
alembic revision --autogenerate -m "Remove deprecated_field from canvas_courses"
alembic upgrade head
```

### Safe Removal Process

1. **Test without the field first** - Remove from operations but keep in model
2. **Run integration tests** - Ensure sync operations work
3. **Remove from database model** - Create migration to drop column
4. **Deploy and monitor** - Watch for any issues

## Database Migrations

### Creating Migrations

```bash
# Auto-generate migration based on model changes
alembic revision --autogenerate -m "Description of changes"

# Create empty migration for manual changes
alembic revision -m "Manual migration description"

# Apply migrations
alembic upgrade head

# Rollback migrations
alembic downgrade -1  # Go back one migration
alembic downgrade base  # Go back to beginning
```

### Migration Best Practices

#### 1. Always Review Generated Migrations

```python
# Generated migration - always review before applying
def upgrade():
    # Check that this matches your intent
    op.add_column('canvas_courses', sa.Column('created_at', sa.DateTime(), nullable=True))

def downgrade():
    # Ensure downgrade works correctly
    op.drop_column('canvas_courses', 'created_at')
```

#### 2. Handle Data Migrations

For complex changes, separate schema and data migrations:

```python
def upgrade():
    # Step 1: Add new column
    op.add_column('canvas_courses', sa.Column('formatted_code', sa.String(150), nullable=True))
    
    # Step 2: Populate data
    connection = op.get_bind()
    connection.execute("""
        UPDATE canvas_courses 
        SET formatted_code = UPPER(course_code) 
        WHERE course_code IS NOT NULL
    """)
    
    # Step 3: Make non-nullable if desired
    op.alter_column('canvas_courses', 'formatted_code', nullable=False)
```

#### 3. Test Migrations

```python
# Test both upgrade and downgrade
def test_migration():
    # Apply migration
    alembic upgrade head
    
    # Test data integrity
    # Test application functionality
    
    # Test rollback
    alembic downgrade -1
    
    # Verify rollback worked
```

## Testing and Validation

### 1. Unit Tests for Operations

```python
# database/tests/test_canvas_ops.py
def test_course_with_created_at():
    canvas_data = {
        'id': 12345,
        'name': 'Test Course',
        'course_code': 'TEST101',
        'created_at': '2024-01-01T10:00:00Z'  # NEW FIELD
    }
    
    manager = CanvasDataManager(session)
    course = manager.sync_course(canvas_data)
    
    assert course.id == 12345
    assert course.created_at is not None
    assert course.created_at.year == 2024
```

### 2. Integration Tests

```python
# database/tests/test_integration.py
def test_full_sync_with_new_field():
    transformer_output = {
        'courses': [{
            'id': 12345,
            'name': 'Test Course',
            'created_at': datetime(2024, 1, 1, tzinfo=timezone.utc)
        }]
    }
    
    coordinator = SyncCoordinator(session)
    result = coordinator.execute_full_sync(transformer_output)
    
    assert result.success
    assert result.objects_created['courses'] == 1
    
    # Verify field was saved
    course = session.query(CanvasCourse).filter_by(id=12345).first()
    assert course.created_at == datetime(2024, 1, 1, tzinfo=timezone.utc)
```

### 3. Validation Tests

```python
# Test field validation
def test_created_at_validation():
    # Test valid timestamp
    canvas_data = {'id': 1, 'created_at': '2024-01-01T10:00:00Z'}
    course = manager.sync_course(canvas_data)
    assert course.created_at is not None
    
    # Test invalid timestamp (should not crash)
    canvas_data = {'id': 2, 'created_at': 'invalid-date'}
    course = manager.sync_course(canvas_data)
    assert course.created_at is not None  # Should use fallback
    
    # Test missing timestamp
    canvas_data = {'id': 3}
    course = manager.sync_course(canvas_data)
    assert course.created_at is not None  # Should use default
```

### 4. Database Schema Tests

```python
def test_database_schema():
    """Test that database schema matches model definitions."""
    from sqlalchemy import inspect
    
    inspector = inspect(engine)
    columns = inspector.get_columns('canvas_courses')
    
    column_names = [col['name'] for col in columns]
    assert 'created_at' in column_names
    
    # Check column type
    created_at_col = next(col for col in columns if col['name'] == 'created_at')
    assert 'DATETIME' in str(created_at_col['type']).upper()
    assert created_at_col['nullable'] == True
```

### Running Tests

```bash
# Run specific test files
pytest database/tests/test_canvas_ops.py -v
pytest database/tests/test_integration.py -v

# Run all database tests
pytest database/tests/ -v

# Run tests with coverage
pytest database/tests/ --cov=database/operations --cov-report=html
```

## Advanced Field Types

### 1. JSON Fields

For complex nested data:

```python
# Database model
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy import JSON as GenericJSON

class CanvasCourse(CanvasEntityModel):
    # Use JSON field for complex data
    metadata_json = Column(JSON, nullable=True)  # PostgreSQL
    # or
    metadata_json = Column(GenericJSON, nullable=True)  # Cross-database

# Canvas operations
def _create_course_from_data(self, canvas_data: Dict[str, Any]) -> CanvasCourse:
    import json
    
    metadata = {}
    if canvas_data.get('custom_fields'):
        metadata = canvas_data['custom_fields']
    
    return CanvasCourse(
        id=canvas_data['id'],
        metadata_json=metadata if metadata else None
    )
```

### 2. Enum Fields

For controlled vocabulary:

```python
from enum import Enum
from sqlalchemy import Enum as SQLEnum

class CourseStatus(Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"

class CanvasCourse(CanvasEntityModel):
    status = Column(SQLEnum(CourseStatus), default=CourseStatus.ACTIVE)

# Canvas operations
def _create_course_from_data(self, canvas_data: Dict[str, Any]) -> CanvasCourse:
    status = CourseStatus.ACTIVE  # default
    if canvas_data.get('workflow_state'):
        state_mapping = {
            'available': CourseStatus.ACTIVE,
            'unpublished': CourseStatus.INACTIVE,
            'completed': CourseStatus.ARCHIVED
        }
        status = state_mapping.get(canvas_data['workflow_state'], CourseStatus.ACTIVE)
    
    return CanvasCourse(
        id=canvas_data['id'],
        status=status
    )
```

### 3. Relationship Fields

For related data:

```python
# Database models
class CanvasCourse(CanvasEntityModel):
    # One-to-many relationship
    assignments = relationship("CanvasAssignment", back_populates="course")
    
class CanvasAssignment(CanvasEntityModel):
    course_id = Column(Integer, ForeignKey('canvas_courses.id'))
    course = relationship("CanvasCourse", back_populates="assignments")

# Canvas operations - relationships are handled automatically
# Just ensure foreign keys are populated correctly
def _create_assignment_from_data(self, canvas_data: Dict[str, Any], course_id: int):
    return CanvasAssignment(
        id=canvas_data['id'],
        course_id=course_id,  # Ensure foreign key is set
        name=canvas_data.get('name', '')
    )
```

## Troubleshooting

### Common Issues and Solutions

#### 1. "Column doesn't exist" Error

```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) no such column: canvas_courses.created_at
```

**Solution:**
```bash
# Check migration status
alembic current
alembic history

# Apply missing migrations
alembic upgrade head

# If migration doesn't exist, create it
alembic revision --autogenerate -m "Add missing created_at field"
```

#### 2. "Invalid datetime format" Error

```
ValueError: Invalid isoformat string: 'invalid-date'
```

**Solution:**
```python
def _parse_datetime_safely(self, date_string):
    """Safe datetime parsing with fallback."""
    if not date_string:
        return None
    
    try:
        if isinstance(date_string, datetime):
            return date_string
        return datetime.fromisoformat(date_string.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        self.logger.warning(f"Failed to parse datetime '{date_string}': {e}")
        return None  # or datetime.now(timezone.utc) for required fields
```

#### 3. "Foreign key constraint failed" Error

```
sqlite3.IntegrityError: FOREIGN KEY constraint failed
```

**Solution:**
```python
# Ensure parent records exist before creating children
def sync_assignment(self, canvas_data: Dict[str, Any], course_id: int):
    # Verify course exists first
    course = self.session.query(CanvasCourse).filter_by(id=course_id).first()
    if not course:
        raise CanvasOperationError(f"Cannot create assignment: course {course_id} not found")
    
    # Now create assignment
    return self._create_assignment_from_data(canvas_data, course_id)
```

#### 4. "Transaction rollback" Error

```
sqlalchemy.exc.InvalidRequestError: This Session's transaction has been rolled back
```

**Solution:**
```python
# Use transaction management
from database.operations.base.transaction_manager import TransactionManager

def sync_with_transaction(self, canvas_data):
    transaction_manager = TransactionManager(self.session)
    
    try:
        with transaction_manager.begin_nested_transaction():
            # Perform operations
            self._sync_courses(canvas_data['courses'])
            self._sync_students(canvas_data['students'])
            # Transaction commits automatically if successful
    except Exception as e:
        # Transaction rolls back automatically on exception
        self.logger.error(f"Sync failed: {e}")
        raise
```

### Debugging Tools

#### 1. SQL Query Logging

```python
# Enable SQL logging
import logging
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Or in your operations
def debug_query(self, model_class, filters=None):
    query = self.session.query(model_class)
    if filters:
        query = query.filter_by(**filters)
    
    # Print the SQL
    print("SQL Query:", str(query))
    
    return query.all()
```

#### 2. Model Inspection

```python
def inspect_model_changes(self, instance):
    """Debug what fields changed on a model instance."""
    from sqlalchemy import inspect
    
    inspector = inspect(instance)
    
    print("Dirty fields:", inspector.attrs.keys())
    for attr in inspector.attrs:
        hist = inspector.attrs[attr].history
        if hist.has_changes():
            print(f"  {attr}: {hist.deleted} -> {hist.added}")
```

#### 3. Transaction State Checking

```python
def check_transaction_state(self):
    """Debug current transaction state."""
    print(f"Transaction active: {self.session.is_active}")
    print(f"Session dirty: {len(self.session.dirty)}")
    print(f"Session new: {len(self.session.new)}")
    print(f"Session deleted: {len(self.session.deleted)}")
```

## Best Practices

### 1. Field Naming Convention

- Use snake_case for database fields
- Match Canvas API field names when possible
- Use descriptive names for calculated fields

```python
# Good
created_at = Column(DateTime, nullable=True)           # Matches Canvas
enrollment_status = Column(String(50), nullable=True)  # Descriptive
last_synced = Column(DateTime, nullable=False)         # Clear purpose

# Avoid
dt_created = Column(DateTime, nullable=True)           # Cryptic
status = Column(String(50), nullable=True)             # Too generic
```

### 2. Default Values and Nullability

- Make new fields nullable initially
- Provide sensible defaults in application code
- Consider database-level defaults for required fields

```python
# Good approach
created_at = Column(DateTime, nullable=True)  # Nullable for existing records

def _create_course_from_data(self, canvas_data):
    return CanvasCourse(
        created_at=canvas_data.get('created_at') or datetime.now(timezone.utc)
    )

# With database default
last_synced = Column(DateTime, nullable=False, default=datetime.now)
```

### 3. Change Detection Optimization

- Only check fields that can actually change
- Use efficient comparison methods
- Consider change significance

```python
def _course_needs_update(self, existing: CanvasCourse, canvas_data: Dict[str, Any]) -> bool:
    # Skip fields that rarely change
    if existing.created_at and not canvas_data.get('created_at'):
        # Don't update if we have created_at but Canvas doesn't provide it
        pass
    
    # Focus on fields that change frequently
    return (
        existing.name != canvas_data.get('name', existing.name) or
        existing.current_score != canvas_data.get('current_score', existing.current_score)
    )
```

### 4. Error Handling

- Always handle datetime parsing errors
- Provide meaningful error messages
- Use fallback values appropriately

```python
def _safe_datetime_parse(self, value, field_name="datetime"):
    """Safely parse datetime with detailed error handling."""
    if not value:
        return None
    
    try:
        if isinstance(value, datetime):
            return value
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except (ValueError, AttributeError) as e:
        self.logger.warning(
            f"Failed to parse {field_name} '{value}': {e}. Using None."
        )
        return None
```

---

**Need Help?**

- Check existing field implementations in the codebase
- Review test files for examples: `database/tests/test_canvas_ops.py`
- Use integration tests to validate full pipeline: `database/tests/test_integration.py`
- Test changes with small datasets first using the Canvas bridge