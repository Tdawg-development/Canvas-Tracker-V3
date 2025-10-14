# Database Documentation

This folder contains documentation for the multi-layer database architecture and data operations.

## 📁 Files in this Category

### Database Architecture
- **[database_architecture.md](./database_architecture.md)** - Complete database schema and layer definitions
  - **Layer 0**: Object lifecycle management (active/inactive state tracking)
  - **Layer 1**: Canvas data (pure sync, matches Canvas API exactly)  
  - **Layer 2**: Historical data (time-series, append-only grade tracking)
  - **Layer 3**: User data (persistent metadata and customizations)
  - Complete table definitions with SQL schemas

### Database Operations  
- **[database-operations-guide.md](./database-operations-guide.md)** - Operations and query patterns
  - CRUD operations across all layers
  - Data synchronization processes
  - Query optimization strategies
  - Performance considerations

## 🎯 Database Design Principles

### Multi-Layer Architecture
The database uses a **4-layer separation** to cleanly organize different types of data:

1. **Layer 0 (Lifecycle)** - Tracks object existence across sync operations
2. **Layer 1 (Canvas)** - Pure Canvas data, completely replaced during syncs  
3. **Layer 2 (Historical)** - Time-series data for trend analysis
4. **Layer 3 (User)** - Persistent user metadata that survives syncs

### Key Benefits
- **Data Integrity** - Canvas sync never interferes with user data
- **Historical Tracking** - Complete audit trail of grade changes
- **Performance** - Optimized for both sync operations and analytics
- **Flexibility** - User metadata persists across Canvas changes

## 📊 Database Schema Overview

### Core Tables
- `object_status` - Tracks Canvas object lifecycle
- `enrollment_status` - Tracks student-course enrollment lifecycle
- `canvas_courses`, `canvas_students`, `canvas_assignments` - Pure Canvas data
- `grade_history`, `assignment_scores` - Historical tracking
- `course_snapshots` - Statistical snapshots over time

### Relationships
- **Canvas Layer** maintains FK relationships matching Canvas structure
- **Historical Layer** references Canvas objects but persists independently  
- **Lifecycle Layer** provides meta-tracking for all objects
- **User Layer** provides customization without Canvas dependencies

## 📖 Reading Order

1. **Start with database_architecture.md** for complete schema and layer explanations
2. **Review database-operations-guide.md** for operational patterns and queries

## 🔗 Related Documentation

- **[System Architecture](../architecture/)** - How database fits in overall architecture
- **[Canvas API](../api/)** - How Canvas data structures map to database
- **[Testing Strategy](../testing/)** - Database testing approaches and coverage

---

*Part of [Canvas Tracker V3 Documentation](../README.md)*