# Database Operations Architecture

## Overview

The Database Operations layer provides high-level, business-focused APIs that abstract away the complexities of our 4-layer database model interactions. This layer adopts a **hybrid approach** that balances flexibility, performance, and maintainability.

## Core Philosophy

- **Simple queries** → Direct query building for performance and flexibility
- **Complex analytics** → Operations layer for business logic centralization
- **Clear separation of concerns** across all operational components
- **Transaction-safe operations** with proper rollback strategies

---

## Directory Structure

```
database/operations/
├── __init__.py
├── canvas_bridge.py            # Canvas-Database integration orchestrator
├── canvas_sync_pipeline.py     # Production Canvas sync pipeline
├── typescript_interface.py     # Cross-language TypeScript-Python interface
├── layer1/
│   ├── __init__.py
│   ├── canvas_ops.py          # Canvas data CRUD operations
│   └── sync_coordinator.py    # Canvas sync coordination
└── transformers/
    ├── __init__.py
    ├── base.py                 # Base transformer classes
    ├── assignment_transformer.py
    ├── course_transformer.py
    ├── enrollment_transformer.py
    └── student_transformer.py
```

---

## Component Roles and Responsibilities

### Core Integration Components

#### **canvas_bridge.py**
**Role**: Canvas-Database integration orchestrator
**Responsibilities**:
- Coordinate Canvas API data collection with TypeScript interface
- Transform Canvas staging data for database storage
- Handle Canvas sync operations with transaction management
- Provide comprehensive error handling and rollback capabilities

**Key Operations**:
- `initialize_bulk_canvas_courses_sync()` - Complete bulk Canvas sync
- `initialize_canvas_course_sync()` - Single course sync
- `execute_canvas_data_transformation()` - Data transformation coordination

#### **canvas_sync_pipeline.py**
**Role**: Production Canvas sync pipeline
**Responsibilities**:
- Provide callable production sync functions
- Handle sync result reporting and validation
- Manage Canvas sync configuration and defaults
- Coordinate between Canvas interface and database layers

**Key Functions**:
- `run_bulk_canvas_sync()` - Synchronous bulk Canvas sync
- `run_single_course_sync()` - Single course sync wrapper
- `sync_all_canvas_courses()` - Async bulk Canvas sync
- `sync_canvas_course()` - Async single course sync
- `verify_canvas_data()` - Canvas data validation

#### **typescript_interface.py**
**Role**: Cross-language TypeScript-Python interface
**Responsibilities**:
- Execute TypeScript Canvas interface from Python
- Handle subprocess execution and result parsing
- Provide environment validation for Node.js/TypeScript
- Support Windows PowerShell compatibility

**Key Operations**:
- `execute_typescript_canvas_interface()` - Main interface execution
- `validate_typescript_environment()` - Environment checks
- `parse_typescript_result()` - Result parsing and validation

### Layer-Specific Operations

#### **layer1/canvas_ops.py**
**Role**: Canvas data CRUD operations
**Responsibilities**:
- Canvas-specific database operations and queries
- Sync tracking and timestamp management
- Canvas data validation and transformation
- Handle Canvas model relationships

**Key Features**:
- Canvas timestamp handling and preservation
- Sync status tracking for all Canvas objects
- Efficient Canvas data queries and updates
- Canvas-specific validation rules

#### **layer1/sync_coordinator.py**
**Role**: Canvas sync operation coordination
**Responsibilities**:
- Define sync priority levels and strategies
- Coordinate Canvas sync operations
- Handle sync validation and error management
- Provide sync result reporting

**Key Components**:
- `SyncPriority` enum for sync operation priorities
- Sync validation and integrity checking
- Canvas sync configuration management

### Data Transformation Layer

#### **transformers/** directory
**Role**: Canvas data transformation for database storage
**Responsibilities**:
- Transform Canvas API responses to database format
- Handle Canvas timestamp parsing and preservation
- Validate and normalize Canvas data
- Support modular transformation architecture

**Key Transformers**:
- `assignment_transformer.py` - Canvas assignment data transformation
- `course_transformer.py` - Canvas course data transformation
- `enrollment_transformer.py` - Canvas enrollment data transformation
- `student_transformer.py` - Canvas student data transformation
- `base.py` - Base transformer classes and utilities

## Production Usage Examples

### Canvas Sync Pipeline Usage
```python
from database.operations.canvas_sync_pipeline import run_bulk_canvas_sync, run_single_course_sync

# Sync all Canvas courses
result = run_bulk_canvas_sync()
print(f"Synced {result.courses_synced} courses with {result.total_students} students")

# Sync a specific course
result = run_single_course_sync(course_id=12972117)
print(f"Course sync completed: {result.success}")
```

### Canvas Bridge Usage
```python
from database.operations.canvas_bridge import CanvasDataBridge
from database.session import get_session

session = get_session()
bridge = CanvasDataBridge(
    canvas_interface_path="./canvas-interface",
    session=session
)

# Execute Canvas sync
result = await bridge.initialize_bulk_canvas_courses_sync()
print(f"Sync result: {result.success}")
```
**Role**: Simple, reusable SQL query construction
**Responsibilities**:
- Build optimized queries for common data retrieval patterns
- Provide flexible filtering and sorting capabilities
- Generate performant joins across model relationships
- Support pagination and result limiting

**Usage Pattern**: *Direct frontend/API consumption for simple data needs*

**Key Query Builders**:
- `build_student_grades_query()` - Grade retrieval with filtering
- `build_course_enrollment_query()` - Enrollment data with status filters
- `build_assignment_submissions_query()` - Submission history queries
- `build_recent_activity_query()` - Activity timeline queries

**Example Usage**:
```python
# Frontend/API layer
query_builder = QueryBuilder(session)
grades_query = query_builder.build_grade_history_query(
    student_id=123, 
    course_id=456, 
    date_range=last_30_days
)
raw_data = session.execute(grades_query).fetchall()
# Frontend processes raw data for display
```

#### **utilities/analytics_builder.py** 🧠 **Core Component**
**Role**: Complex analytical computations and insights
**Responsibilities**:
- Perform multi-step analytical calculations
- Generate statistical insights and predictions
- Combine data from multiple sources for complex analysis
- Provide consistent analytical definitions across the application

**Usage Pattern**: *Operations layer for complex business intelligence*

**Key Analytics Methods**:
- `calculate_grade_momentum()` - Trend analysis with statistical modeling
- `predict_final_grade()` - Machine learning-based predictions
- `analyze_at_risk_students()` - Multi-factor risk assessment
- `generate_performance_insights()` - Comprehensive student analysis

**Example Usage**:
```python
# Operations layer
analytics = AnalyticsBuilder(session)
insights = analytics.calculate_performance_trends(student_id=123, course_id=456)
# Returns: { trend: "improving", velocity: 2.3, prediction: { grade: 87.5, confidence: 0.85 } }
```

#### **utilities/bulk_operations.py**
**Role**: Batch processing utilities for large datasets
**Responsibilities**:
- Optimize bulk insert/update operations
- Handle large dataset processing with memory efficiency
- Provide progress tracking for long-running operations
- Implement conflict resolution for bulk operations

#### **utilities/migration_helper.py**
**Role**: Data migration and transformation tools
**Responsibilities**:
- Support database schema migrations
- Handle data format transformations
- Provide rollback capabilities for migrations
- Validate data integrity during migrations

#### **utilities/performance_monitor.py**
**Role**: Query performance tracking and optimization
**Responsibilities**:
- Monitor query execution times and resource usage
- Identify performance bottlenecks and slow queries
- Suggest database optimizations and indexing strategies
- Generate performance reports for system optimization

---

## Decision Framework: Query Builder vs Analytics Builder

### Use **Query Builder** When:
✅ Simple filtering, sorting, grouping operations  
✅ Frontend needs raw data for custom processing  
✅ Performance is critical (database-optimized queries)  
✅ Query logic is straightforward and reusable  
✅ Multiple frontends need the same data in different formats  

**Examples**: Student grade lists, assignment submissions, course enrollments, activity logs

### Use **Analytics Builder** When:
✅ Multi-step calculations required  
✅ Business logic needs centralization for consistency  
✅ Statistical analysis or predictive modeling  
✅ Multiple data sources need combination  
✅ Results must be identical across all frontends  

**Examples**: Grade trend analysis, performance predictions, risk assessments, comprehensive insights

---

## Implementation Strategy

### Phase 1: Foundation
1. **Base Operations** - Abstract classes and transaction management
2. **Query Builder** - Core query construction utilities
3. **Layer 1 Operations** - Canvas data management (highest priority)

### Phase 2: Core Operations
4. **Layer 0 Operations** - Lifecycle management integration
5. **Layer 2 & 3 Operations** - Historical and metadata management
6. **Basic Composite Operations** - Simple cross-layer coordination

### Phase 3: Advanced Features
7. **Analytics Builder** - Complex analytical capabilities
8. **Advanced Composite Operations** - Full sync orchestration
9. **Performance & Monitoring** - Optimization and monitoring tools

### Phase 4: Polish & Integration
10. **Comprehensive Testing** - Integration and performance tests
11. **Documentation** - API documentation and usage examples
12. **Frontend Integration** - Clean API exposure for UI consumption

---

## Integration Examples

### Canvas Sync Integration
```python
# Clean, high-level API for sync operations
sync_orchestrator = SyncOrchestrator(db_manager)
sync_result = sync_orchestrator.execute_master_sync(canvas_data_bundle)
```

### User Interface Integration
```python
# Simple metadata management
metadata_ops = MetadataManager(db_manager)
metadata_ops.update_student_notes(student_id, user_notes)

# Flexible data retrieval
query_builder = QueryBuilder(db_manager)
student_data = query_builder.build_student_dashboard_query(student_id)
```

### Analytics/Reporting Integration
```python
# Rich analytical capabilities
analytics = AnalyticsBuilder(db_manager)
performance_insights = analytics.generate_student_insights(student_id)
trend_data = analytics.calculate_grade_momentum(student_id, course_id)
```

---

## Success Metrics

### Performance Targets
- Query response times < 100ms for simple queries
- Bulk operations handle 10,000+ records efficiently
- Analytics computations complete within 2 seconds

### Maintainability Goals
- Clear separation of concerns across all components
- 90%+ test coverage for all operations
- Comprehensive documentation for all public APIs

### Scalability Requirements
- Support for multiple concurrent sync operations
- Efficient handling of large historical datasets
- Memory-efficient bulk processing capabilities

---

This architecture provides a robust, scalable foundation for all database operations while maintaining the flexibility to evolve with changing requirements. The hybrid approach ensures we get the best of both performance optimization and business logic centralization.