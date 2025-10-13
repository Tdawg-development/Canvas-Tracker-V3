# Canvas Tracker V3 - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.2] - 2024-10-13

### Added - Layer 2 Historical Data Models
- **Complete Historical Data Architecture**: Append-only models for tracking changes over time
  - `GradeHistory`: Student grade progression and change tracking across assignments/courses
  - `AssignmentScore`: Detailed assignment-level scoring with submission status and timing
  - `CourseSnapshot`: Course-level statistics and metrics captured at sync intervals
- **Advanced Analytics Capabilities**:
  - Grade trend analysis with configurable time windows
  - Assignment completion rate tracking and late submission detection
  - Course health monitoring with activity and performance metrics
  - Historical change detection with improvement/decline identification
- **Append-Only Data Integrity**: Historical records are never modified, only added
  - Complete audit trail for all grade and assignment changes
  - Trend analysis support with chronological ordering
  - Data consistency validation across related historical records

### Enhanced - Testing Infrastructure
- **Comprehensive Layer 2 Test Suite**: 27 test cases covering all historical models
  - Grade history creation, modification tracking, and trend analysis
  - Assignment score validation, submission timing, and missing assignment detection
  - Course snapshot metrics, health checks, and historical progression
  - Cross-model integration testing for data consistency
- **Advanced Test Scenarios**: Real-world workflow simulation
  - Complete trend analysis workflows with grade progression over time
  - Append-only behavior validation ensuring historical data preservation
  - Timezone-aware datetime handling for accurate historical timestamps

### Technical Improvements
- Extended `HistoricalBaseModel` usage for consistent timestamp management
- Robust query methods with flexible filtering and ordering options
- Canvas timezone handler integration for reliable datetime comparisons
- Comprehensive validation of NOT NULL constraints and data relationships

### Database Architecture Progress
- **Layer 0**: Object Lifecycle Management ✅ (v0.2.1)
- **Layer 1**: Canvas Data Models ✅ (v0.2.0) 
- **Layer 2**: Historical Data Models ✅ (v0.2.2) **NEW**
- **Layer 3**: User Metadata Models ⏳ (Next: v0.2.3)

## [0.2.1] - 2024-10-13

### Added - Layer 0 Object Lifecycle & Canvas Timezone Handling
- **Layer 0 Object Lifecycle Models**: Complete soft-delete and lifecycle management system
  - `ObjectStatus`: Individual Canvas object lifecycle tracking (courses, students, assignments)
  - `EnrollmentStatus`: Student-course enrollment relationship lifecycle tracking
  - Soft-delete functionality with user approval workflows for data preservation
  - Dependency tracking for user metadata and historical data
  - Object reactivation support when Canvas objects return after removal
  - Comprehensive query methods for pending deletions and lifecycle state management
- **Canvas Timezone Handler**: Production-ready timezone handling for Canvas API integration
  - Native support for Canvas datetime format (`2025-07-28T16:31:18Z`)
  - Timezone-aware datetime conversion, storage, and retrieval
  - Database compatibility layer handling SQLite timezone stripping
  - Cross-timezone comparison utilities for reliable datetime operations
  - Helper functions for Canvas datetime parsing and API format conversion

### Fixed - Test Infrastructure & Timezone Issues
- **Transaction Management**: Resolved SQLAlchemy session teardown issues
  - Fixed `ResourceClosedError` exceptions during test cleanup
  - Improved test fixture handling for both committed and uncommitted transactions
  - Eliminated test noise and improved development experience
- **Timezone Compatibility**: Fixed timezone-related test failures
  - Proper timezone-aware datetime comparison in database tests
  - Consistent handling of naive vs timezone-aware datetimes across models
  - SQLite timezone stripping compatibility for cross-platform development

### Technical Improvements
- Enhanced model initialization ensuring boolean fields never have `None` values
- Added 28 comprehensive Layer 0 lifecycle model tests covering all state transitions
- Added 22 timezone handler tests covering Canvas datetime scenarios
- Improved database test isolation and state management reliability
- Extended utility module structure for Canvas-specific operations

### Quality Assurance
- **Complete Test Coverage**: All 143 database tests now pass without errors or warnings
- **Zero Transaction Issues**: Eliminated all SQLAlchemy transaction teardown problems
- **Timezone Reliability**: Robust datetime handling ready for production Canvas API integration

## [0.2.0] - 2024-10-13

### Added - Database Layer 1 (Canvas Data Models)
- **Layer 1 Canvas Data Models**: Complete implementation of Canvas data models
  - `CanvasCourse`: Course information with Canvas course IDs as primary keys
  - `CanvasStudent`: Student enrollment and grade data with Canvas student IDs as primary keys  
  - `CanvasAssignment`: Assignment/quiz information with Canvas assignment IDs as primary keys
  - `CanvasEnrollment`: Student-course relationship model with composite primary keys
- **Enhanced Base Model Architecture**:
  - `CanvasEntityModel`: Base class for Canvas entities using Canvas IDs as primary keys
  - `CanvasRelationshipModel`: Base class for relationship models without name fields
  - Both include automatic sync tracking and timestamp management
- **Comprehensive Unit Tests**: 
  - Layer 1 model tests in `database/tests/test_layer1_models.py`
  - Tests cover model creation, relationships, constraints, and Canvas-specific business logic
  - All tests passing with proper database schema validation
- **Database Development Tools**:
  - `scripts/create_dev_db.py`: Development database creation script with sample data structure
  - Persistent SQLite database for manual inspection with DB Browser for SQLite

### Technical Details
- **Canvas Data Mapping**: Models precisely map from Canvas API data structures (CanvasCourseStaging, CanvasStudentStaging, etc.)
- **Primary Key Strategy**: Uses Canvas IDs as primary keys instead of auto-incrementing IDs
- **Relationship Management**: Proper SQLAlchemy relationships with overlap handling for many-to-many relationships
- **Sync Tracking**: Built-in sync tracking capabilities for all Canvas models
- **Foreign Key Constraints**: Proper referential integrity between courses, students, assignments, and enrollments

### Fixed
- **SQLAlchemy Primary Key Conflicts**: Resolved composite primary key issues with SQLite by creating dedicated base classes
- **Relationship Overlap Warnings**: Added proper `overlaps` parameters to SQLAlchemy relationships
- **Database Schema Generation**: All Layer 1 tables generate correctly without conflicts

## [0.1.0] - 2024-10-13

### Added - Database Infrastructure Foundation
- **Core Database Infrastructure**:
  - Multi-environment configuration system (dev/test/prod) 
  - SQLAlchemy session management with automatic transaction handling
  - Database connection pooling and performance optimization
  - Comprehensive error handling and custom exception hierarchy
- **Base Model System**:
  - `BaseModel`: Auto-incrementing primary keys with timestamp tracking
  - `CanvasBaseModel`: Canvas-specific models with sync tracking
  - `HistoricalBaseModel`: Historical data models with recorded_at timestamps
  - `MetadataBaseModel`: User metadata models with notes and tags
- **Testing Infrastructure**:
  - Comprehensive test fixtures and configuration
  - In-memory test databases for fast, isolated testing
  - 81 passing tests covering all core infrastructure components
- **Utility Systems**:
  - Custom exception hierarchy for database operations
  - Configuration validation and environment handling
  - Database health checking and connection management

### Technical Foundation
- **Architecture**: 4-layer database design (Layer 0-3) with proper separation of concerns
- **Database Support**: SQLite for development/testing with PostgreSQL production readiness
- **Session Management**: Context managers for clean database operations
- **Error Handling**: Comprehensive SQLAlchemy error conversion to custom exceptions