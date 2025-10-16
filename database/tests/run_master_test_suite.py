#!/usr/bin/env python3
"""
Master Canvas API Test Suite

Runs all Canvas API layer tests and saves comprehensive results to organized text files.
This provides exhaustive information about test results for analysis and debugging.

Test Coverage:
- Single Course Processing (with multiple configurations)
- Multi-Course Processing (bulk API)
- Configuration Impact Analysis
- Field Filtering Validation
- Performance Metrics

Results are saved to database/tests/results/ with timestamps.
"""

import subprocess
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import tempfile
import shutil


@dataclass
class TestResult:
    """Container for individual test results."""
    test_name: str
    success: bool
    execution_time: float
    output: str
    error_message: Optional[str] = None
    data_summary: Optional[Dict[str, Any]] = None


class MasterTestSuite:
    """
    Master test suite that orchestrates all Canvas API layer tests
    and generates comprehensive result files.
    """
    
    def __init__(self):
        self.start_time = datetime.now(timezone.utc)
        self.results_dir = Path("database/tests/results")
        self.results_dir.mkdir(exist_ok=True)
        
        # Clear previous results
        self._clear_previous_results()
        
        self.test_results: List[TestResult] = []
        self.master_log = []
        
    def _clear_previous_results(self):
        """Clear previous test result files."""
        if self.results_dir.exists():
            for file in self.results_dir.glob("*.txt"):
                file.unlink()
        print(f"📁 Cleared previous results in {self.results_dir}")
    
    def _log(self, message: str, level: str = "INFO"):
        """Add message to master log with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] {level}: {message}"
        self.master_log.append(log_entry)
        print(log_entry)
    
    def _save_result_file(self, filename: str, content: str):
        """Save content to a result file."""
        filepath = self.results_dir / filename
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        self._log(f"💾 Saved {filename} ({len(content)} chars)")
    
    def _run_pytest_test(self, test_path: str, test_name: str, timeout: int = 300) -> TestResult:
        """
        Run a specific pytest test and capture comprehensive output.
        
        Args:
            test_path: Full pytest path to the test
            test_name: Human-readable test name
            timeout: Test timeout in seconds
            
        Returns:
            TestResult with captured output and metadata
        """
        import os  # For environment variable handling
        self._log(f"🧪 Starting {test_name}")
        
        start_time = datetime.now()
        
        try:
            # Run pytest with comprehensive output
            cmd = [
                "python", "-m", "pytest",
                test_path,
                "-v", "-s", "--tb=long",
                "--capture=no"  # Don't capture stdout/stderr
            ]
            
            # Capture output to both console and file
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                env=os.environ.copy()  # Pass current environment (including our test confirmation flag)
            )
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            # Combine stdout and stderr
            full_output = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            
            success = result.returncode == 0
            error_message = None if success else f"Exit code: {result.returncode}"
            
            self._log(f"✅ Completed {test_name} in {execution_time:.1f}s" if success 
                     else f"❌ Failed {test_name} in {execution_time:.1f}s")
            
            return TestResult(
                test_name=test_name,
                success=success,
                execution_time=execution_time,
                output=full_output,
                error_message=error_message
            )
            
        except subprocess.TimeoutExpired:
            execution_time = timeout
            error_msg = f"Test timed out after {timeout} seconds"
            self._log(f"⏰ {test_name} timed out")
            
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time=execution_time,
                output="",
                error_message=error_msg
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"Test execution failed: {str(e)}"
            self._log(f"💥 {test_name} failed with exception: {str(e)}")
            
            return TestResult(
                test_name=test_name,
                success=False,
                execution_time=execution_time,
                output="",
                error_message=error_msg
            )
    
    def run_single_course_test(self) -> TestResult:
        """Run single course processing test."""
        test_path = "database/tests/test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_single_course_processing"
        return self._run_pytest_test(test_path, "Single Course Processing", timeout=120)
    
    def run_configuration_impact_test(self) -> TestResult:
        """Run configuration impact analysis test."""
        test_path = "database/tests/test_real_canvas_api_pipeline.py::TestRealCanvasApiPipeline::test_real_canvas_api_configuration_impact"
        return self._run_pytest_test(test_path, "Configuration Impact Analysis", timeout=120)
    
    def run_full_pipeline_test(self) -> TestResult:
        """Run full real Canvas API pipeline test."""
        test_path = "database/tests/test_real_canvas_api_pipeline.py::TestRealCanvasApiPipeline::test_real_canvas_api_to_transformer_pipeline"
        return self._run_pytest_test(test_path, "Full Canvas API Pipeline", timeout=120)
    
    def run_bulk_processing_test(self) -> TestResult:
        """Run bulk multi-course processing test with user confirmation."""
        self._log("⚠️  Bulk processing test requires user confirmation")
        
        test_path = "database/tests/test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_all_available_courses"
        
        # Prompt user for confirmation
        print("\n" + "="*60)
        print("⚠️  BULK PROCESSING TEST CONFIRMATION")
        print("="*60)
        print("This test will process ALL available courses in your Canvas instance!")
        print("It may take a long time and make many API calls.")
        print()
        print("Options:")
        print("  y - Yes, run the bulk processing test")
        print("  n - No, skip this test (recommended for most runs)")
        print()
        
        try:
            response = input("Run bulk processing test? [y/N]: ").strip().lower()
            
            if response == 'y' or response == 'yes':
                self._log("🚀 User confirmed - running bulk processing test")
                print("Running bulk processing test - this may take several minutes...")
                
                # Set environment variable to bypass internal prompt in the test
                import os
                os.environ['CANVAS_MASTER_TEST_CONFIRMED'] = 'true'
                
                try:
                    return self._run_pytest_test(test_path, "Bulk Multi-Course Processing", timeout=600)  # 10 minute timeout
                finally:
                    # Clean up environment variable
                    os.environ.pop('CANVAS_MASTER_TEST_CONFIRMED', None)
            else:
                self._log("⏭️  User chose to skip bulk processing test")
                return TestResult(
                    test_name="Bulk Multi-Course Processing",
                    success=True,
                    execution_time=0.0,
                    output="SKIPPED: User chose to skip bulk processing test.\nTo run manually: python -m pytest database/tests/test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::test_all_available_courses -v -s",
                    error_message=None
                )
        
        except KeyboardInterrupt:
            self._log("⏹️  Bulk processing test interrupted by user")
            return TestResult(
                test_name="Bulk Multi-Course Processing",
                success=True,
                execution_time=0.0,
                output="INTERRUPTED: Bulk processing test was interrupted by user.",
                error_message=None
            )
    
    def _extract_data_summary(self, test_output: str) -> Optional[Dict[str, Any]]:
        """Extract data summary from test output for analysis."""
        summary = {}
        
        # Look for common patterns in test output
        lines = test_output.split('\n')
        
        for line in lines:
            line = line.strip()
            
            # Extract entity counts
            if 'records' in line and ':' in line:
                parts = line.split(':')
                if len(parts) == 2:
                    entity_type = parts[0].strip().split()[-1]  # Last word before ':'
                    count_part = parts[1].strip().split()[0]    # First word after ':'
                    try:
                        count = int(count_part)
                        summary[f"{entity_type}_count"] = count
                    except ValueError:
                        pass
            
            # Extract timing information
            if 'time:' in line.lower() and 'ms' in line:
                try:
                    # Extract millisecond values
                    ms_parts = line.split('ms')[0].split()
                    if ms_parts:
                        time_val = float(ms_parts[-1])
                        if 'api' in line.lower():
                            summary['api_time_ms'] = time_val
                        elif 'transform' in line.lower():
                            summary['transform_time_ms'] = time_val
                        elif 'total' in line.lower():
                            summary['total_time_ms'] = time_val
                except (ValueError, IndexError):
                    pass
        
        return summary if summary else None
    
    def run_all_tests(self) -> List[TestResult]:
        """Run all Canvas API layer tests."""
        self._log("🚀 Starting Master Canvas API Test Suite")
        self._log("=" * 60)
        
        # Define test sequence
        tests_to_run = [
            ("Single Course", self.run_single_course_test),
            ("Configuration Impact", self.run_configuration_impact_test),
            ("Full Pipeline", self.run_full_pipeline_test),
            ("Bulk Processing", self.run_bulk_processing_test),
        ]
        
        results = []
        
        for test_name, test_func in tests_to_run:
            self._log(f"📋 Running {test_name} Test...")
            
            try:
                result = test_func()
                
                # Extract data summary from output
                result.data_summary = self._extract_data_summary(result.output)
                
                results.append(result)
                self.test_results.append(result)
                
                # Save individual test result
                self._save_individual_test_result(result)
                
            except Exception as e:
                self._log(f"💥 {test_name} test failed with exception: {str(e)}", "ERROR")
                
                error_result = TestResult(
                    test_name=test_name,
                    success=False,
                    execution_time=0.0,
                    output="",
                    error_message=f"Test execution failed: {str(e)}"
                )
                results.append(error_result)
                self.test_results.append(error_result)
        
        return results
    
    def _save_individual_test_result(self, result: TestResult):
        """Save individual test result to a dedicated file."""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        filename = f"{result.test_name.lower().replace(' ', '_')}_{timestamp}.txt"
        
        content = f"""Canvas API Test Result: {result.test_name}
{'=' * 60}

Test Information:
- Test Name: {result.test_name}
- Success: {result.success}
- Execution Time: {result.execution_time:.2f} seconds
- Timestamp: {datetime.now(timezone.utc).isoformat()}

{'Error Information:' if result.error_message else 'Status: PASSED'}
{result.error_message if result.error_message else 'Test completed successfully'}

Data Summary:
{json.dumps(result.data_summary, indent=2) if result.data_summary else 'No structured data extracted'}

Full Test Output:
{'=' * 40}
{result.output}

End of {result.test_name} Result
{'=' * 60}
"""
        
        self._save_result_file(filename, content)
    
    def generate_master_summary(self):
        """Generate master summary file with all test results."""
        timestamp = self.start_time.strftime("%Y%m%d_%H%M%S")
        
        # Calculate summary statistics
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r.success)
        failed_tests = total_tests - passed_tests
        total_execution_time = sum(r.execution_time for r in self.test_results)
        
        content = f"""Canvas API Master Test Suite Results
{'=' * 80}

Execution Summary:
- Suite Start Time: {self.start_time.isoformat()}
- Suite End Time: {datetime.now(timezone.utc).isoformat()}
- Total Execution Time: {total_execution_time:.2f} seconds
- Tests Run: {total_tests}
- Tests Passed: {passed_tests}
- Tests Failed: {failed_tests}
- Success Rate: {(passed_tests/total_tests*100):.1f}%

Test Results Overview:
{'-' * 40}
"""
        
        for result in self.test_results:
            status = "✅ PASS" if result.success else "❌ FAIL"
            content += f"{status} {result.test_name:<30} ({result.execution_time:.1f}s)\n"
            
            if result.data_summary:
                content += f"     Data: {result.data_summary}\n"
            
            if result.error_message:
                content += f"     Error: {result.error_message}\n"
            
            content += "\n"
        
        content += f"""
Performance Analysis:
{'-' * 40}
"""
        
        # Aggregate performance metrics
        total_api_time = sum(r.data_summary.get('api_time_ms', 0) for r in self.test_results if r.data_summary)
        total_transform_time = sum(r.data_summary.get('transform_time_ms', 0) for r in self.test_results if r.data_summary)
        total_entities = sum(r.data_summary.get('courses_count', 0) + r.data_summary.get('students_count', 0) + 
                           r.data_summary.get('assignments_count', 0) + r.data_summary.get('enrollments_count', 0) 
                           for r in self.test_results if r.data_summary)
        
        content += f"Total API Time: {total_api_time:.1f}ms\n"
        content += f"Total Transform Time: {total_transform_time:.1f}ms\n"
        content += f"Total Entities Processed: {total_entities}\n"
        
        if total_execution_time > 0:
            content += f"Processing Rate: {total_entities / total_execution_time:.1f} entities/second\n"
        
        content += f"""

Master Log:
{'-' * 40}
"""
        content += "\n".join(self.master_log)
        
        content += f"""

End of Master Test Suite Results
{'=' * 80}
Generated at: {datetime.now(timezone.utc).isoformat()}
"""
        
        self._save_result_file(f"master_summary_{timestamp}.txt", content)
        
        # Also save a latest summary (always overwrites)
        self._save_result_file("latest_master_summary.txt", content)
    
    def print_final_summary(self):
        """Print final summary to console."""
        passed = sum(1 for r in self.test_results if r.success)
        total = len(self.test_results)
        
        print(f"\n{'='*80}")
        print(f"🎯 MASTER TEST SUITE COMPLETED")
        print(f"{'='*80}")
        print(f"✅ Tests Passed: {passed}/{total}")
        print(f"⏱️  Total Time: {sum(r.execution_time for r in self.test_results):.1f}s")
        print(f"📁 Results saved to: {self.results_dir.absolute()}")
        print(f"{'='*80}")


def main():
    """Main execution function."""
    print("🧪 Canvas API Master Test Suite")
    print("=" * 50)
    print("This will run all Canvas API layer tests and save comprehensive results.")
    print(f"Results will be saved to: database/tests/results/")
    print()
    
    # Check for Canvas environment
    canvas_interface_path = Path("canvas-interface")
    if not canvas_interface_path.exists():
        print("❌ Canvas interface directory not found!")
        print("   Please ensure canvas-interface/ directory exists with proper configuration.")
        return 1
    
    env_file = canvas_interface_path / ".env"
    if not env_file.exists():
        print("❌ Canvas .env file not found!")
        print("   Please ensure canvas-interface/.env exists with Canvas API credentials.")
        return 1
    
    # Ask for confirmation
    response = input("\n🚀 Ready to run master test suite? [y/N]: ")
    if response.lower() != 'y':
        print("❌ Test suite cancelled.")
        return 0
    
    # Run the master test suite
    suite = MasterTestSuite()
    
    try:
        results = suite.run_all_tests()
        suite.generate_master_summary()
        suite.print_final_summary()
        
        # Return appropriate exit code
        failed_tests = sum(1 for r in results if not r.success)
        return 1 if failed_tests > 0 else 0
        
    except KeyboardInterrupt:
        suite._log("⏹️  Test suite interrupted by user", "WARNING")
        suite.generate_master_summary()
        return 1
        
    except Exception as e:
        suite._log(f"💥 Master test suite failed: {str(e)}", "ERROR")
        suite.generate_master_summary()
        return 1


if __name__ == "__main__":
    sys.exit(main())