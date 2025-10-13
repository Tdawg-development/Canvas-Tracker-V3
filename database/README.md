# Canvas Tracker V3 - Database Module

## Overview
This module contains all database-related functionality for the Canvas Tracker V3 application, organized by architectural layers and functionality.

## File Structure

```
database/
├── __init__.py                 # Main database exports
├── config.py                   # Database connection config
├── base.py                     # SQLAlchemy Base, common mixins
├── session.py                  # Session management, connection handling
├── migrations/                 # Database schema migrations
│   ├── __init__.py
│   └── versions/
├── models/                     # SQLAlchemy models by layer
│   ├── __init__.py            # Import all models
│   ├── layer1_canvas.py       # Canvas data models
│   ├── layer2_historical.py   # Grade/assignment history models  
│   ├── layer3_metadata.py     # User metadata models
│   └── (later) layer0_lifecycle.py
├── operations/                # Database operations by layer
│   ├── __init__.py
│   ├── canvas_ops.py          # Layer 1 CRUD operations
│   ├── historical_ops.py      # Layer 2 operations
│   ├── metadata_ops.py        # Layer 3 operations
│   └── sync_ops.py            # Cross-layer sync operations
├── queries/                   # Reusable query builders
│   ├── __init__.py
│   ├── curriculum_queries.py  # Frontend curriculum filtering
│   ├── student_queries.py     # Student-focused queries
│   └── reporting_queries.py   # Analytics/reporting queries
└── utils/                     # Shared utilities
    ├── __init__.py
    ├── validators.py          # Data validation helpers
    ├── transformers.py        # Canvas API → DB transformations
    └── exceptions.py          # Custom database exceptions
```

## Layer Architecture

### Layer 1: Canvas Data (Pure Sync)
- **Location**: `models/layer1_canvas.py`, `operations/canvas_ops.py`
- **Purpose**: Core entities fetched from Canvas API exactly as provided
- **Sync Behavior**: Completely replaced during full sync operations
- **Models**: `CanvasCourse`, `CanvasStudent`, `CanvasAssignment`, `CanvasEnrollment`

### Layer 2: Historical Data (Sync-Generated)
- **Location**: `models/layer2_historical.py`, `operations/historical_ops.py`
- **Purpose**: Time-series data generated from Canvas sync operations
- **Sync Behavior**: Append-only tables that accumulate over time
- **Models**: `GradeHistory`, `AssignmentScore`

### Layer 3: User Data (Persistent)
- **Location**: `models/layer3_metadata.py`, `operations/metadata_ops.py`
- **Purpose**: User-generated metadata that persists across all operations
- **Sync Behavior**: Never touched by sync operations
- **Models**: `StudentMetadata`, `AssignmentMetadata`, `CourseMetadata`

### Layer 0: Object Lifecycle (Future Implementation)
- **Location**: `models/layer0_lifecycle.py`, `operations/lifecycle_ops.py`
- **Purpose**: Tracks existence and status of Canvas objects
- **Sync Behavior**: Updated after each sync to track active/inactive status

## Key Design Principles

### Modular Organization
- **Layer Separation**: Each layer has its own model and operations files
- **Clean Imports**: Layers can import from each other when needed
- **Independent Evolution**: Each layer can evolve without affecting others

### Shared Functionality
- **`base.py`**: Common table mixins (timestamps, IDs, common fields)
- **`session.py`**: Unified session management across all layers
- **`queries/`**: Cross-layer query builders and complex joins
- **`utils/`**: Data transformation, validation, and utility functions

### Sync Orchestration
- **`sync_ops.py`**: Coordinates operations across multiple layers
- **Cross-layer logic**: Handles data flow between layers during sync
- **Transaction management**: Ensures data consistency across layer updates

## Usage Examples

### Basic Model Imports
```python
# Layer-specific model imports
from database.models.layer1_canvas import CanvasStudent, CanvasCourse
from database.models.layer2_historical import GradeHistory
from database.models.layer3_metadata import StudentMetadata

# All models at once
from database.models import CanvasStudent, GradeHistory, StudentMetadata
```

### Operations
```python
# Layer-specific operations
from database.operations.canvas_ops import create_student, update_student
from database.operations.metadata_ops import add_student_note
from database.operations.sync_ops import full_canvas_sync

# Typical sync workflow
from database.operations.sync_ops import full_canvas_sync
result = full_canvas_sync(canvas_api_data)
```

### Queries
```python
# Curriculum-based queries
from database.queries.curriculum_queries import get_curriculum_students
students = get_curriculum_students(["web_dev", "data_science"])

# Complex student analytics
from database.queries.student_queries import get_student_progress_history
progress = get_student_progress_history(student_id=12345)
```

### Session Management
```python
# Database session handling
from database.session import get_session, DatabaseManager

# Context manager approach
with get_session() as session:
    student = session.query(CanvasStudent).filter_by(student_id=12345).first()
    
# Manager approach
db = DatabaseManager()
session = db.get_session()
```

## Development Workflow

### Phase 1: Layer 1-3 Implementation
1. **Layer 1**: Canvas data models and basic sync
2. **Layer 2**: Historical tracking during sync operations
3. **Layer 3**: User metadata persistence and UI integration

### Phase 2: Layer 0 Addition (Future)
4. **Layer 0**: Object lifecycle management
5. **Enhanced sync**: Soft delete and reactivation workflows
6. **User confirmations**: Deletion approval interfaces

### Testing Strategy
- **Unit tests**: Each layer's operations tested independently
- **Integration tests**: Cross-layer sync workflows
- **Mock data**: Canvas API response fixtures for testing

## Configuration

### Database Connection
```python
# config.py contains
DATABASE_URL = "sqlite:///canvas_tracker.db"  # Development
# DATABASE_URL = "postgresql://..." # Production
```

### Migration Management
```bash
# Create new migration
alembic revision --autogenerate -m "Add Layer 1 Canvas tables"

# Apply migrations
alembic upgrade head
```

## Best Practices

### Data Access Patterns
- **Use operations modules** for complex business logic
- **Use query modules** for reusable query patterns
- **Use models directly** only for simple CRUD operations

### Cross-Layer Dependencies
- **Layer 3 → Layer 1**: User metadata references Canvas objects
- **Layer 2 → Layer 1**: Historical data references Canvas objects
- **Sync operations**: Coordinate updates across multiple layers

### Error Handling
```python
from database.utils.exceptions import SyncError, DataValidationError

try:
    full_canvas_sync(data)
except SyncError as e:
    logger.error(f"Sync failed: {e}")
    # Handle sync-specific errors
except DataValidationError as e:
    logger.error(f"Invalid data: {e}")
    # Handle validation errors
```