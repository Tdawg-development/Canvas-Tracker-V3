# Canvas API Master Test Suite

The Canvas API Master Test Suite provides comprehensive testing of all Canvas API layers with detailed result logging and analysis.

## 🎯 Purpose

- **Comprehensive Testing**: Runs all major Canvas API layer tests in sequence
- **Detailed Logging**: Saves complete test outputs to organized text files  
- **Performance Analysis**: Tracks API performance, transformation times, and data processing metrics
- **Result Archival**: Maintains timestamped results for historical analysis
- **Easy Execution**: Simple one-command test suite execution

## 📋 Test Coverage

The master test suite runs these key tests:

### 1. Single Course Processing
- **Test**: `test_multi_course_canvas_pipeline.py::test_single_course_processing`
- **Purpose**: Tests single course processing with multiple configurations
- **Validates**: Configuration impact, field filtering, entity processing
- **Duration**: ~8-15 seconds

### 2. Configuration Impact Analysis  
- **Test**: `test_real_canvas_api_pipeline.py::test_real_canvas_api_configuration_impact`
- **Purpose**: Analyzes how different configurations affect processing
- **Validates**: LIGHTWEIGHT vs STANDARD vs MAXIMUM configurations
- **Duration**: ~8-12 seconds

### 3. Full Canvas API Pipeline
- **Test**: `test_real_canvas_api_pipeline.py::test_real_canvas_api_to_transformer_pipeline`
- **Purpose**: Complete end-to-end Canvas API → TypeScript → Transformers pipeline
- **Validates**: Full data flow, transformation accuracy, field population
- **Duration**: ~8-12 seconds

### 4. Bulk Processing (Optional)
- **Test**: `test_multi_course_canvas_pipeline.py::test_all_available_courses`
- **Purpose**: Multi-course bulk processing using bulk API infrastructure
- **Status**: Skipped by default (requires manual confirmation for safety)
- **Duration**: ~30+ seconds when run manually

## 🚀 Quick Start

### Run the Complete Test Suite
```bash
# From Canvas-Tracker-V3 root directory
python database/tests/run_all_tests.py
```

### Run Individual Components
```bash
# Run just the master test suite (bypassing launcher)
python database/tests/run_master_test_suite.py

# Run specific test manually
python -m pytest database/tests/test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_single_course_processing -v -s
```

## 📁 Results Structure

All results are saved to `database/tests/results/`:

### Generated Files

1. **Individual Test Results**
   - `single_course_processing_YYYYMMDD_HHMMSS.txt`
   - `configuration_impact_analysis_YYYYMMDD_HHMMSS.txt`
   - `full_canvas_api_pipeline_YYYYMMDD_HHMMSS.txt`
   - `bulk_multi-course_processing_YYYYMMDD_HHMMSS.txt`

2. **Master Summary**
   - `master_summary_YYYYMMDD_HHMMSS.txt` (timestamped)
   - `latest_master_summary.txt` (always current)

### File Contents

Each individual test result file contains:
- **Test Information**: Name, success status, execution time, timestamp
- **Error Information**: Detailed error messages if test failed
- **Data Summary**: Extracted structured data (entity counts, timing metrics)
- **Full Test Output**: Complete stdout/stderr from test execution

The master summary contains:
- **Execution Summary**: Overall suite statistics and timing
- **Test Results Overview**: Status and metrics for each test
- **Performance Analysis**: Aggregated performance metrics across all tests
- **Master Log**: Chronological log of all suite activities

## 📊 Sample Results

### Successful Test Suite Run
```
Canvas API Master Test Suite Results
================================================================================

Execution Summary:
- Suite Start Time: 2025-10-15T20:00:00Z
- Suite End Time: 2025-10-15T20:01:30Z
- Total Execution Time: 90.5 seconds
- Tests Run: 4
- Tests Passed: 3
- Tests Failed: 0
- Success Rate: 100.0%

Test Results Overview:
----------------------------------------
✅ PASS Single Course Processing      (8.2s)
     Data: {'courses_count': 1, 'students_count': 33, 'assignments_count': 35}

✅ PASS Configuration Impact Analysis (7.8s)
     Data: {'api_time_ms': 7139.0, 'transform_time_ms': 1.0}

✅ PASS Full Canvas API Pipeline      (7.7s)
     Data: {'courses_count': 1, 'students_count': 33, 'enrollments_count': 33}

✅ PASS Bulk Multi-Course Processing  (0.0s)
     Data: Skipped for safety

Performance Analysis:
----------------------------------------
Total API Time: 21277.0ms
Total Transform Time: 3.0ms
Total Entities Processed: 102
Processing Rate: 1.1 entities/second
```

## ⚙️ Prerequisites

### Required Environment
- **Canvas Interface**: `canvas-interface/` directory with proper configuration
- **Environment File**: `canvas-interface/.env` with Canvas API credentials
- **Node.js**: For TypeScript Canvas API calls
- **Python**: 3.9+ with pytest installed

### Canvas API Access
- Valid Canvas API token in `.env` file
- Access to Canvas course (default: course ID 7982015)
- Appropriate Canvas permissions for course data access

## 🔧 Configuration

### Environment Variables (in canvas-interface/.env)
```env
CANVAS_API_URL=https://your-canvas.instructure.com/api/v1
CANVAS_ACCESS_TOKEN=your_canvas_api_token
```

### Timeout Settings
- Individual Test Timeout: 120 seconds (configurable in master suite)
- Bulk Processing Timeout: 300 seconds (5 minutes)

## 🎯 Use Cases

### Development Testing
- Run after making changes to Canvas API layer
- Validate configuration changes don't break existing functionality
- Performance regression testing

### Deployment Validation
- Pre-deployment testing to ensure system integrity
- Post-deployment verification of Canvas API connectivity
- Environment-specific testing

### Performance Analysis
- Track API performance over time using timestamped results
- Identify performance bottlenecks in transformation pipeline
- Compare different configuration impacts

### Debugging
- Comprehensive logs for troubleshooting failed tests
- Full stdout/stderr capture for detailed error analysis
- Data structure validation and inspection

## 🚨 Important Notes

### Safety Measures
- Bulk processing test is skipped by default to prevent accidental load on Canvas API
- User confirmation required for bulk operations
- Results directory is cleared before each run (previous results are replaced)

### Performance Considerations  
- Tests make real Canvas API calls (not mocked)
- Respects Canvas API rate limits
- Total execution time: ~30-90 seconds depending on Canvas response times

### Result File Management
- Files are automatically timestamped to prevent conflicts
- `latest_master_summary.txt` always contains most recent results
- No automatic cleanup (manual removal required for disk space management)

## 🔍 Troubleshooting

### Common Issues

**Test Timeout**
```
Solution: Increase timeout in master suite or check Canvas API connectivity
```

**Environment Not Found**
```
Solution: Ensure running from Canvas-Tracker-V3 root directory
```

**Canvas API Errors**
```
Solution: Verify .env file has correct Canvas credentials and course access
```

**Permission Errors**
```
Solution: Ensure write access to database/tests/results/ directory
```

---

**Last Updated**: October 15, 2025  
**Version**: 1.0