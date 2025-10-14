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
├── base/
│   ├── __init__.py
│   ├── base_operations.py      # Abstract base classes for all operations
│   ├── transaction_manager.py  # Transaction handling and rollback logic
│   └── exceptions.py           # Operations-specific exceptions
├── layer0/
│   ├── __init__.py
│   ├── lifecycle_ops.py        # Object lifecycle CRUD operations
│   └── dependency_tracker.py   # Cross-layer dependency analysis
├── layer1/
│   ├── __init__.py
│   ├── canvas_ops.py          # Canvas data CRUD operations
│   ├── sync_coordinator.py    # Canvas sync orchestration
│   └── relationship_manager.py # Canvas object relationship management
├── layer2/
│   ├── __init__.py
│   └── history_ops.py         # Historical data CRUD operations
├── layer3/
│   ├── __init__.py
│   ├── metadata_ops.py        # User metadata CRUD operations
│   └── tag_manager.py         # Specialized tag management utilities
├── composite/
│   ├── __init__.py
│   ├── sync_orchestrator.py   # Master cross-layer sync coordination
│   ├── cleanup_manager.py     # Data cleanup and maintenance operations
│   └── integrity_checker.py   # Cross-layer data consistency validation
└── utilities/
    ├── __init__.py
    ├── query_builder.py        # Simple, reusable SQL query construction
    ├── analytics_builder.py    # Complex analytical computations and insights
    ├── bulk_operations.py      # Batch processing utilities for large datasets
    ├── migration_helper.py     # Data migration and transformation tools
    └── performance_monitor.py  # Query performance tracking and optimization
```

---

## Component Roles and Responsibilities

### Base Components

#### **base/base_operations.py**
**Role**: Foundation classes for all database operations
**Responsibilities**:
- Abstract `BaseOperation` class with session management
- Abstract `CRUDOperation` class for standard CRUD patterns
- Common validation and error handling patterns
- Transaction wrapper decorators

**Key Classes**:
```python
class BaseOperation(ABC):
    # Session management, logging, validation framework
    
class CRUDOperation(BaseOperation):
    # Standard Create, Read, Update, Delete operations
    # Bulk operation patterns
```

#### **base/transaction_manager.py**
**Role**: Transaction management and rollback coordination
**Responsibilities**:
- Nested transaction support
- Rollback strategies for different operation types
- Transaction monitoring and logging
- Deadlock detection and retry logic

---

### Layer-Specific Operations

#### **layer0/lifecycle_ops.py**
**Role**: Object lifecycle management operations
**Responsibilities**:
- Track new Canvas objects entering the system
- Mark objects as missing during sync operations
- Manage soft-delete workflows with user approval
- Handle object reactivation when Canvas objects return

**Key Operations**:
- `track_new_object()` - Register new Canvas objects
- `mark_objects_missing()` - Batch update missing status
- `approve_pending_deletions()` - Execute user-approved deletions
- `get_pending_deletions_summary()` - Deletion approval interface data

#### **layer0/dependency_tracker.py**
**Role**: Cross-layer dependency analysis
**Responsibilities**:
- Check for user metadata dependencies before deletion
- Analyze historical data dependencies
- Update dependency flags for lifecycle decisions
- Generate dependency impact reports

**Key Operations**:
- `analyze_deletion_impact()` - Full dependency analysis
- `update_dependency_flags()` - Sync dependency status
- `get_dependency_graph()` - Visual dependency mapping

---

#### **layer1/canvas_ops.py**
**Role**: Canvas data CRUD operations
**Responsibilities**:
- Standard CRUD operations for all Canvas models
- Sync-aware operations (replace vs update)
- Relationship management between Canvas objects
- Canvas data validation and normalization

**Key Operations**:
- `sync_canvas_object()` - Single object sync with change detection
- `batch_sync_objects()` - Efficient bulk sync operations
- `rebuild_course_statistics()` - Recalculate derived data
- `get_stale_canvas_data()` - Identify objects needing refresh

#### **layer1/sync_coordinator.py**
**Role**: Canvas sync operation orchestration
**Responsibilities**:
- Coordinate full Canvas sync operations
- Handle incremental sync scenarios
- Manage sync conflicts and resolution
- Provide sync session rollback capabilities

**Key Operations**:
- `execute_full_sync()` - Complete Canvas data replacement
- `execute_incremental_sync()` - Process only changed objects
- `handle_sync_conflicts()` - Conflict resolution strategies
- `validate_sync_integrity()` - Post-sync validation

#### **layer1/relationship_manager.py**
**Role**: Canvas object relationship management
**Responsibilities**:
- Manage enrollment relationships (student-course)
- Handle assignment-course relationships
- Maintain referential integrity during sync
- Optimize relationship queries for performance

---

#### **layer2/history_ops.py**
**Role**: Historical data CRUD operations
**Responsibilities**:
- Record grade changes and score updates
- Create course performance snapshots
- Manage historical data retention policies
- Provide historical data access patterns

**Key Operations**:
- `record_grade_change()` - Add grade history entry
- `record_assignment_score()` - Track assignment submissions
- `create_course_snapshot()` - Periodic course state capture
- `archive_old_records()` - Retention policy enforcement

---

#### **layer3/metadata_ops.py**
**Role**: User metadata CRUD operations
**Responsibilities**:
- Standard CRUD operations for all metadata models
- Orphaned metadata detection and cleanup
- Metadata validation and normalization
- Bulk metadata operations for efficiency

**Key Operations**:
- `create_student_metadata()` - New student customization
- `update_assignment_metadata()` - Modify assignment annotations
- `find_orphaned_metadata()` - Cleanup candidate identification
- `bulk_metadata_operations()` - Batch processing for large datasets

#### **layer3/tag_manager.py**
**Role**: Specialized tag management operations
**Responsibilities**:
- Tag normalization and deduplication
- Tag usage analytics and suggestions
- Tag merging and organization
- Tag-based search and filtering

**Key Operations**:
- `normalize_tags()` - Consistent tag formatting
- `merge_duplicate_tags()` - Tag cleanup operations
- `get_tag_suggestions()` - AI-powered tag recommendations
- `analyze_tag_usage()` - Tag popularity and trends

---

### Composite Operations

#### **composite/sync_orchestrator.py**
**Role**: Master orchestrator for cross-layer sync operations
**Responsibilities**:
- Coordinate sync operations across all 4 layers
- Ensure proper order of operations during sync
- Handle rollback scenarios for failed syncs
- Provide comprehensive sync reporting

**Key Operations**:
- `execute_master_sync()` - Full 4-layer sync coordination
- `execute_cleanup_cycle()` - Periodic maintenance operations
- `rollback_sync_session()` - Complete sync rollback
- `generate_sync_report()` - Comprehensive sync analysis

#### **composite/cleanup_manager.py**
**Role**: Data cleanup and maintenance operations
**Responsibilities**:
- Identify and process deletion candidates
- Execute approved cleanup operations
- Archive historical data based on retention policies
- Optimize database performance through maintenance

**Key Operations**:
- `identify_cleanup_candidates()` - Find objects ready for cleanup
- `execute_approved_cleanup()` - Process user-approved deletions
- `optimize_database_performance()` - Index maintenance and optimization
- `generate_cleanup_report()` - Cleanup operation summary

#### **composite/integrity_checker.py**
**Role**: Cross-layer data consistency validation
**Responsibilities**:
- Validate referential integrity across layers
- Detect and report data inconsistencies
- Suggest and execute data repair operations
- Monitor data quality metrics over time

**Key Operations**:
- `check_cross_layer_integrity()` - Comprehensive consistency check
- `find_orphaned_records()` - Identify broken references
- `suggest_data_repairs()` - Automated fix recommendations
- `generate_integrity_report()` - Data quality dashboard

---

### Utility Components

#### **utilities/query_builder.py** 🔧 **Core Component**
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