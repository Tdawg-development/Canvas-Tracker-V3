#!/usr/bin/env python3
"""
Comprehensive Canvas API Unit Test Runner

Runs all Canvas API unit tests with detailed reporting and analysis.
Provides test coverage metrics and performance analysis.
"""

import sys
import subprocess
import time
import json
from pathlib import Path

def run_test_suite(test_pattern=None, verbose=True):
    """Run the complete Canvas API test suite."""
    
    print("🚀 Canvas API Comprehensive Unit Test Suite")
    print("=" * 60)
    
    # Test configurations
    test_categories = {
        'canvas_unit': {
            'description': 'Canvas Unit Tests (Fast)',
            'marker': 'canvas_unit and not slow',
            'expected_duration': '< 2 minutes'
        },
        'canvas_performance': {
            'description': 'Canvas Performance Tests',
            'marker': 'canvas_unit and slow',
            'expected_duration': '2-5 minutes'
        },
        'canvas_error_handling': {
            'description': 'Canvas Error Handling Tests',
            'marker': 'canvas_unit',
            'files': ['test_canvas_api_error_handling.py'],
            'expected_duration': '< 3 minutes'
        },
        'canvas_integration': {
            'description': 'Canvas Integration Tests',
            'marker': 'canvas_integration',
            'expected_duration': '3-10 minutes'
        }
    }
    
    overall_results = {
        'categories': {},
        'start_time': time.time(),
        'total_tests': 0,
        'total_passed': 0,
        'total_failed': 0,
        'total_skipped': 0
    }
    
    # Run each test category
    for category, config in test_categories.items():
        if test_pattern and test_pattern not in category:
            continue
            
        print(f"\\n🧪 Running {config['description']}")
        print(f"   Expected duration: {config['expected_duration']}")
        print("-" * 50)
        
        # Build pytest command
        cmd = ['python', '-m', 'pytest']
        
        if 'files' in config:
            # Run specific test files
            for test_file in config['files']:
                cmd.append(test_file)
        else:
            # Run all tests with marker
            cmd.extend(['-m', config['marker']])
        
        # Add common pytest options
        cmd.extend([
            '-v' if verbose else '-q',
            '--tb=short',
            '--durations=10',
            '--json-report',
            '--json-report-file=test_results.json'
        ])
        
        # Run the tests
        category_start = time.time()
        try:
            result = subprocess.run(
                cmd,
                cwd=Path(__file__).parent,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            category_duration = time.time() - category_start
            
            # Parse results
            category_results = parse_test_results(result, category_duration)
            overall_results['categories'][category] = category_results
            
            # Update totals
            overall_results['total_tests'] += category_results['total_tests']
            overall_results['total_passed'] += category_results['passed']
            overall_results['total_failed'] += category_results['failed']
            overall_results['total_skipped'] += category_results['skipped']
            
            # Print category summary
            print_category_summary(category, config['description'], category_results)
            
        except subprocess.TimeoutExpired:
            print(f"⏰ {config['description']} timed out after 10 minutes")
            overall_results['categories'][category] = {
                'status': 'timeout',
                'duration': 600,
                'total_tests': 0,
                'passed': 0,
                'failed': 1,
                'skipped': 0
            }
            overall_results['total_failed'] += 1
            
        except Exception as e:
            print(f"💥 Error running {config['description']}: {e}")
            overall_results['categories'][category] = {
                'status': 'error',
                'error': str(e),
                'duration': time.time() - category_start,
                'total_tests': 0,
                'passed': 0,
                'failed': 1,
                'skipped': 0
            }
            overall_results['total_failed'] += 1
    
    # Calculate overall duration
    overall_results['total_duration'] = time.time() - overall_results['start_time']
    
    # Print comprehensive summary
    print_comprehensive_summary(overall_results)
    
    # Generate test report
    generate_test_report(overall_results)
    
    return overall_results

def parse_test_results(subprocess_result, duration):
    """Parse pytest subprocess results."""
    
    # Try to parse JSON report if available
    try:
        with open('test_results.json', 'r') as f:
            json_report = json.load(f)
            
        return {
            'status': 'completed',
            'duration': duration,
            'total_tests': json_report['summary']['total'],
            'passed': json_report['summary'].get('passed', 0),
            'failed': json_report['summary'].get('failed', 0),
            'skipped': json_report['summary'].get('skipped', 0),
            'return_code': subprocess_result.returncode,
            'stdout': subprocess_result.stdout,
            'stderr': subprocess_result.stderr
        }
    except:
        # Fallback to parsing stdout
        stdout = subprocess_result.stdout
        
        # Basic parsing of pytest output
        passed = stdout.count(' PASSED')
        failed = stdout.count(' FAILED')
        skipped = stdout.count(' SKIPPED')
        
        return {
            'status': 'completed',
            'duration': duration,
            'total_tests': passed + failed + skipped,
            'passed': passed,
            'failed': failed,
            'skipped': skipped,
            'return_code': subprocess_result.returncode,
            'stdout': stdout,
            'stderr': subprocess_result.stderr
        }

def print_category_summary(category, description, results):
    """Print summary for a test category."""
    
    status_emoji = "✅" if results['failed'] == 0 else "❌"
    duration_str = f"{results['duration']:.1f}s"
    
    print(f"\\n{status_emoji} {description} Summary:")
    print(f"   Duration: {duration_str}")
    print(f"   Tests: {results['total_tests']} total")
    print(f"   Passed: {results['passed']}")
    print(f"   Failed: {results['failed']}")
    print(f"   Skipped: {results['skipped']}")
    
    if results['failed'] > 0:
        print(f"   ⚠️  {results['failed']} test(s) failed - check output above")

def print_comprehensive_summary(overall_results):
    """Print comprehensive test suite summary."""
    
    print("\\n" + "=" * 60)
    print("🎯 COMPREHENSIVE TEST SUITE SUMMARY")
    print("=" * 60)
    
    # Overall metrics
    total_duration = overall_results['total_duration']
    total_tests = overall_results['total_tests']
    total_passed = overall_results['total_passed']
    total_failed = overall_results['total_failed']
    total_skipped = overall_results['total_skipped']
    
    success_rate = (total_passed / total_tests * 100) if total_tests > 0 else 0
    overall_status = "✅ PASSED" if total_failed == 0 else "❌ FAILED"
    
    print(f"\\n📊 Overall Results: {overall_status}")
    print(f"   Total Duration: {total_duration:.1f}s ({total_duration/60:.1f} minutes)")
    print(f"   Total Tests: {total_tests}")
    print(f"   Passed: {total_passed} ({success_rate:.1f}%)")
    print(f"   Failed: {total_failed}")
    print(f"   Skipped: {total_skipped}")
    
    # Category breakdown
    print(f"\\n📋 Category Breakdown:")
    for category, results in overall_results['categories'].items():
        status_emoji = "✅" if results.get('failed', 1) == 0 else "❌"
        duration = results.get('duration', 0)
        print(f"   {status_emoji} {category:<20} {duration:>6.1f}s  {results.get('passed', 0):>3}/{results.get('total_tests', 0):<3} tests")
    
    # Performance analysis
    print(f"\\n⚡ Performance Analysis:")
    fastest_category = min(overall_results['categories'].items(), key=lambda x: x[1].get('duration', float('inf')))
    slowest_category = max(overall_results['categories'].items(), key=lambda x: x[1].get('duration', 0))
    
    if fastest_category[1].get('duration'):
        print(f"   Fastest category: {fastest_category[0]} ({fastest_category[1]['duration']:.1f}s)")
    if slowest_category[1].get('duration'):
        print(f"   Slowest category: {slowest_category[0]} ({slowest_category[1]['duration']:.1f}s)")
    
    avg_test_duration = (total_duration / total_tests) if total_tests > 0 else 0
    print(f"   Average test duration: {avg_test_duration:.2f}s")
    
    # Recommendations
    print(f"\\n💡 Recommendations:")
    if total_failed > 0:
        print(f"   🔧 Fix {total_failed} failing test(s) before deployment")
    if success_rate < 95:
        print(f"   📈 Improve test success rate (currently {success_rate:.1f}%)")
    if avg_test_duration > 5:
        print(f"   ⚡ Consider optimizing test performance (avg {avg_test_duration:.1f}s per test)")
    if total_failed == 0 and success_rate >= 95:
        print(f"   🎉 Excellent! All tests passing with good coverage")

def generate_test_report(overall_results):
    """Generate detailed test report file."""
    
    report_file = Path(__file__).parent / 'test_report.json'
    
    # Add timestamp and additional metadata
    report_data = {
        'timestamp': time.time(),
        'test_run_summary': overall_results,
        'environment': {
            'python_version': sys.version,
            'platform': sys.platform,
            'working_directory': str(Path.cwd())
        },
        'recommendations': generate_recommendations(overall_results)
    }
    
    with open(report_file, 'w') as f:
        json.dump(report_data, f, indent=2, default=str)
    
    print(f"\\n📄 Detailed report saved to: {report_file}")

def generate_recommendations(results):
    """Generate actionable recommendations based on test results."""
    
    recommendations = []
    
    total_tests = results['total_tests']
    total_failed = results['total_failed']
    total_duration = results['total_duration']
    
    # Test coverage recommendations
    if total_tests < 20:
        recommendations.append({
            'category': 'coverage',
            'priority': 'high',
            'message': f'Test coverage appears low ({total_tests} tests total). Consider adding more comprehensive tests.'
        })
    
    # Performance recommendations
    if total_duration > 300:  # 5 minutes
        recommendations.append({
            'category': 'performance', 
            'priority': 'medium',
            'message': f'Test suite is slow ({total_duration:.1f}s). Consider parallelization or test optimization.'
        })
    
    # Reliability recommendations
    if total_failed > 0:
        recommendations.append({
            'category': 'reliability',
            'priority': 'critical',
            'message': f'{total_failed} test(s) failing. These must be fixed before production deployment.'
        })
    
    # Success recommendations
    if total_failed == 0 and total_tests >= 15:
        recommendations.append({
            'category': 'success',
            'priority': 'info',
            'message': 'Excellent test coverage and reliability! Consider adding performance tests if not present.'
        })
    
    return recommendations

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='Run comprehensive Canvas API unit tests')
    parser.add_argument('--category', '-c', help='Run specific test category (canvas_unit, canvas_performance, etc.)')
    parser.add_argument('--quiet', '-q', action='store_true', help='Run tests in quiet mode')
    parser.add_argument('--fast', '-f', action='store_true', help='Run only fast unit tests')
    
    args = parser.parse_args()
    
    # Determine test pattern
    test_pattern = None
    if args.category:
        test_pattern = args.category
    elif args.fast:
        test_pattern = 'canvas_unit'
    
    # Run the tests
    try:
        results = run_test_suite(test_pattern=test_pattern, verbose=not args.quiet)
        
        # Exit with appropriate code
        exit_code = 0 if results['total_failed'] == 0 else 1
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print("\\n⏹️  Test run interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\\n💥 Test runner failed: {e}")
        sys.exit(1)