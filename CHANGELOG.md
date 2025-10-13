# Canvas Tracker V3 - Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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