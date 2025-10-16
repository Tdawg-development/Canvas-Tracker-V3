# Canvas Tracker V3 - Test Environment

This directory contains all the files needed to manage and control the Canvas Tracker V3 test database environment.

## Files Overview

### Database Management
- **`init_database.py`** - Initialize database schema and tables
- **`setup_test_database.py`** - Comprehensive test database setup with cleanup options
  - Use `--force` to rebuild database from scratch
  - Use `--verify-only` to check existing database schema

### Integration Testing  
- **`test_canvas_integration.py`** - Full Canvas-to-Database integration test
  - Tests complete Canvas API → TypeScript → Python → Database pipeline
  - Supports single course sync testing
  - Includes comprehensive error handling and reporting
- **`test_bulk_canvas_integration.py`** - Bulk Canvas-to-Database integration test
  - Tests complete Canvas API → TypeScript → Python → Database pipeline for ALL courses
  - Syncs all available Canvas courses to database
  - Includes performance metrics and detailed reporting

### Test Utilities
- **`test_helpers.py`** - Shared utilities for test database operations
  - Database session management
  - Test environment configuration
  - Standardized test database setup functions

## Usage Examples

**Note: Run these commands from the main project directory, not from within test-environment/**

### Set up clean test database:
```bash
python test-environment/setup_test_database.py --force
```

### Run full integration test (single course):
```bash
python test-environment/test_canvas_integration.py
```

### Run bulk integration test (all courses):
```bash
python test-environment/test_bulk_canvas_integration.py
```

### Initialize database schema only:
```bash
python test-environment/init_database.py
```

### Verify existing database:
```bash
python test-environment/setup_test_database.py --verify-only
```

## Database Location

The test database file `canvas_tracker_test.db` is created in the main project directory when these scripts are run.

## Environment

All scripts automatically configure themselves to use the test database environment (`DATABASE_ENV=test`).