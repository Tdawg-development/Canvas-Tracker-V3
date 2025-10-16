# Canvas Tracker Database Test Suite

A comprehensive test suite for the Canvas Tracker database layer, covering unit tests, integration tests, and end-to-end validation with real Canvas API calls.

## 🧪 Test Structure

### Core Infrastructure Tests
- **`test_base_and_exceptions.py`** - Base model functionality and exception handling
- **`test_config.py`** - Database configuration and environment management  
- **`test_session.py`** - Database session management and connection handling
- **`test_timezone_handler.py`** - Timezone conversion and datetime utilities

### Database Layer Tests
- **`test_layer0_models.py`** - Core base model functionality
- **`test_layer1_models.py`** - Canvas data models (courses, students, assignments)
- **`test_layer2_models.py`** - Historical tracking models
- **`test_layer3_models.py`** - Analytics and reporting models

### Operations and Query Tests
- **`test_layer1_operations.py`** - Canvas data operations (CRUD, sync)
- **`test_operations_foundation.py`** - Core operation infrastructure
- **`test_query_builder.py`** - Dynamic SQL query construction
- **`test_database_transactions.py`** - Transaction management and rollback

### Transformation System Tests
- **`test_transformers.py`** - Unit tests for individual transformers
- **`test_real_canvas_api_pipeline.py`** - **Main integration test** with real Canvas API calls

### Bridge and Interface Tests  
- **`test_canvas_bridge.py`** - Canvas API integration bridge
- **`test_typescript_interface.py`** - TypeScript execution and data exchange

### Platform and Performance Tests
- **`test_windows_platform.py`** - Windows-specific functionality
- **`test_production_scale.py`** - Large dataset and performance tests
- **`test_integration_layer_comprehensive.py`** - Cross-layer integration tests

## 🌟 Key Test Features

### Real Canvas API Integration
The **`test_real_canvas_api_pipeline.py`** is the crown jewel of the test suite:
- Makes actual Canvas API calls using your TypeScript infrastructure
- Tests the complete pipeline: Canvas API → TypeScript → Python transformers
- Uses your actual course data (Course ID: 7982015)
- Validates score precision (decimal preservation)
- Tests configuration-driven filtering with live data

### Configuration-Driven Testing
Tests support multiple configuration profiles:
- **FULL_REAL**: Complete data extraction with all fields
- **STUDENTS_ANALYTICS**: Student-focused with analytics data
- **COURSE_ONLY**: Minimal course-only extraction
- **LIGHTWEIGHT**: Fast, basic data extraction

### Score Precision Validation
All tests validate that student scores preserve decimal precision:
- Canvas API: `87.53` → Database: `87.53` (not rounded to `88`)
- End-to-end validation from API through transformers to database models

## 🚀 Running Tests

### Basic Test Execution
```bash
# Run all tests
pytest database/tests/ -v

# Run only unit tests
pytest database/tests/ -v -m unit

# Run integration tests (requires Canvas API credentials)
pytest database/tests/ -v -m integration

# Run the real Canvas API pipeline test
pytest database/tests/test_real_canvas_api_pipeline.py -v -s -m canvas_api
```

### Test Categories (Pytest Markers)
- **`@pytest.mark.unit`** - Fast unit tests, no external dependencies
- **`@pytest.mark.integration`** - Integration tests requiring database
- **`@pytest.mark.canvas_api`** - Tests that make real Canvas API calls
- **`@pytest.mark.slow`** - Long-running tests
- **`@pytest.mark.database`** - Tests requiring database connection
- **`@pytest.mark.performance`** - Performance and scalability tests

### Canvas API Integration Requirements
For Canvas API tests to run:
1. **Canvas Interface Path**: `canvas-interface/` directory must exist
2. **API Credentials**: `.env` file with Canvas API credentials  
3. **TypeScript Environment**: Node.js and ts-node must be available
4. **Test Course Access**: Access to Canvas course ID 7982015

## 📊 Test Coverage

### Unit Tests (~70% of tests)
- Individual transformer functionality
- Model validation and relationships
- Configuration validation
- Query building and SQL generation
- Error handling and edge cases

### Integration Tests (~25% of tests)  
- Cross-component interactions
- Database transaction behavior
- Canvas bridge functionality
- TypeScript interface integration

### End-to-End Tests (~5% of tests)
- **Real Canvas API pipeline** - Complete data flow validation
- Production-scale data processing
- Performance benchmarking with live data

## 🔧 Configuration

### Pytest Configuration (`pytest.ini`)
- **Timeout**: 120 seconds (for Canvas API calls)
- **Test Discovery**: Auto-discovery of `test_*.py` files
- **Markers**: Strict marker enforcement
- **Output**: Verbose with colored output
- **Asyncio**: Full async test support

### Test Fixtures (`conftest.py`)
- **Database**: In-memory SQLite for fast testing
- **Session Management**: Automatic transaction rollback
- **Mock Data**: Realistic Canvas API response fixtures
- **State Reset**: Clean global state between tests

## 🧹 Recent Cleanup (2024)

### Removed Redundant Tests
- ❌ `test_full_pipeline_canvas_to_transformer.py` - Mock data, replaced by real API test
- ❌ `test_data_transformers.py` - Legacy transformer system  
- ❌ `test_transformers_integration.py` - Overlapped with pipeline integration
- ❌ `test_transformer_pipeline_integration.py` - Complex, non-functional TypeScript generation

### Consolidated Functionality
- **Score Precision**: All models updated to support `Float` with 2 decimal places
- **Real API Integration**: Single comprehensive test replaces multiple mock tests
- **Configuration Validation**: Streamlined into main pipeline test
- **Performance Testing**: Integrated into real data tests

## 💡 Test Development Guidelines

### Adding New Tests
1. **Use appropriate markers** (`@pytest.mark.unit`, etc.)
2. **Follow naming convention** (`test_*.py` files, `test_*` methods)
3. **Use fixtures** from `conftest.py` for common setup
4. **Test edge cases** and error conditions
5. **Validate precision** for numeric data (especially scores)

### Canvas API Tests
1. **Check requirements** in `setUpClass` method
2. **Use `@pytest.mark.canvas_api`** marker
3. **Handle API failures** gracefully with proper error messages
4. **Validate data structures** against real Canvas response format
5. **Test configuration impact** with live data

### Performance Tests
1. **Use `@pytest.mark.performance`** marker
2. **Measure actual execution time**
3. **Test with realistic data volumes**
4. **Set reasonable performance assertions**
5. **Compare different configuration impacts**

## 🎯 Future Enhancements

### Planned Improvements
- **Multiple Course Testing**: Extend real API tests to multiple courses
- **Error Simulation**: More comprehensive API error handling tests
- **Performance Benchmarks**: Automated performance regression detection
- **Data Validation**: Enhanced Canvas data structure validation
- **Mock Improvements**: Better mock data reflecting actual API responses

### Integration Opportunities
- **CI/CD Integration**: Automated test runs on code changes
- **Performance Monitoring**: Track test execution time trends
- **Coverage Reporting**: Automated code coverage analysis
- **Canvas API Monitoring**: Regular API health checks via tests

---

## 📈 Test Results Summary

The test suite provides:
- ✅ **Comprehensive Coverage**: All major components tested
- ✅ **Real Data Validation**: Actual Canvas API integration  
- ✅ **Precision Preservation**: Decimal scores maintained throughout pipeline
- ✅ **Configuration Flexibility**: Multiple sync profiles tested
- ✅ **Performance Validation**: Large dataset processing verified
- ✅ **Error Handling**: Robust error condition testing
- ✅ **Cross-Platform**: Windows-specific functionality validated

**Total Test Files**: 19  
**Total Size**: ~460 KB of test code  
**Estimated Test Count**: ~300 individual test methods  
**Coverage**: Core functionality, edge cases, and real-world scenarios