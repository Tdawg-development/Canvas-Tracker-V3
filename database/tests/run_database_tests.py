#!/usr/bin/env python3
"""
Test runner for Canvas Tracker database tests.

This script provides various options for running the database test suite:
- Run all tests
- Run specific test categories (unit, integration, database)
- Run with coverage reporting
- Run specific test files or methods
"""

import sys
import os
import argparse
import subprocess
from pathlib import Path

# Add project root to Python path  
PROJECT_ROOT = Path(__file__).parent.parent.parent  # Go up from tests/database/ to project root
sys.path.insert(0, str(PROJECT_ROOT))

def run_command(cmd, capture_output=False):
    """Run a shell command and return the result."""
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        else:
            result = subprocess.run(cmd, shell=True)
            return result.returncode == 0, "", ""
    except Exception as e:
        print(f"Error running command '{cmd}': {e}")
        return False, "", str(e)

def check_dependencies():
    """Check if required testing dependencies are installed."""
    required_packages = ['pytest', 'sqlalchemy']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        print(f"❌ Missing required packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    print("✅ All required dependencies are installed")
    return True

def run_tests(test_type="all", coverage=False, verbose=False, specific_test=None):
    """Run the database tests with specified options."""
    
    # Change to database directory
    os.chdir(PROJECT_ROOT / "database")
    
    # Build pytest command
    cmd_parts = ["python", "-m", "pytest"]
    
    # Add test directory
    cmd_parts.append("tests/")
    
    # Add specific test if provided
    if specific_test:
        cmd_parts[-1] = f"tests/{specific_test}"
    
    # Add markers based on test type
    if test_type == "unit":
        cmd_parts.extend(["-m", "unit"])
    elif test_type == "integration":
        cmd_parts.extend(["-m", "integration"])
    elif test_type == "database":
        cmd_parts.extend(["-m", "database"])
    elif test_type == "fast":
        cmd_parts.extend(["-m", "not slow"])
    
    # Add coverage if requested
    if coverage:
        cmd_parts.extend(["--cov=../database", "--cov-report=html", "--cov-report=term-missing"])
    
    # Add verbosity
    if verbose:
        cmd_parts.append("-v")
    
    # Additional pytest options
    cmd_parts.extend([
        "--tb=short",
        "--color=yes",
    ])
    
    cmd = " ".join(cmd_parts)
    
    print(f"🧪 Running database tests: {test_type}")
    print(f"📁 Working directory: {os.getcwd()}")
    print(f"🔧 Command: {cmd}")
    print("=" * 80)
    
    success, stdout, stderr = run_command(cmd, capture_output=False)
    
    if success:
        print("=" * 80)
        print("🎉 All tests passed!")
        if coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print("=" * 80)
        print("❌ Some tests failed!")
        return False
    
    return True

def list_available_tests():
    """List all available test files and their descriptions."""
    tests_dir = PROJECT_ROOT / "database" / "tests"
    test_files = list(tests_dir.glob("test_*.py"))
    
    print("📋 Available test files:")
    print("-" * 40)
    
    for test_file in sorted(test_files):
        # Read the docstring from the test file
        try:
            with open(test_file, 'r') as f:
                content = f.read()
                # Extract first docstring
                if '"""' in content:
                    start = content.find('"""') + 3
                    end = content.find('"""', start)
                    if end > start:
                        docstring = content[start:end].strip().split('\n')[0]
                    else:
                        docstring = "No description available"
                else:
                    docstring = "No description available"
        except Exception:
            docstring = "Could not read file"
        
        print(f"  {test_file.name:<30} - {docstring}")
    
    print("\n📊 Test markers:")
    print("  unit        - Unit tests for individual components")
    print("  integration - Integration tests for component interactions")
    print("  database    - Tests requiring database connection")
    print("  slow        - Long-running tests")

def main():
    """Main test runner entry point."""
    parser = argparse.ArgumentParser(
        description="Canvas Tracker Database Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_database_tests.py                    # Run all tests
  python run_database_tests.py --type unit        # Run only unit tests
  python run_database_tests.py --coverage         # Run with coverage report
  python run_database_tests.py --test test_config.py  # Run specific test file
  python run_database_tests.py --list             # List available tests
        """
    )
    
    parser.add_argument(
        "--type", "-t",
        choices=["all", "unit", "integration", "database", "fast"],
        default="all",
        help="Type of tests to run"
    )
    
    parser.add_argument(
        "--coverage", "-c",
        action="store_true",
        help="Run tests with coverage reporting"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Run tests in verbose mode"
    )
    
    parser.add_argument(
        "--test", "-s",
        help="Run a specific test file or test method"
    )
    
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List available test files"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="Check if required dependencies are installed"
    )
    
    args = parser.parse_args()
    
    print("🧪 Canvas Tracker Database Test Runner")
    print("=" * 50)
    
    # Check dependencies first
    if args.check_deps:
        return 0 if check_dependencies() else 1
    
    if not check_dependencies():
        return 1
    
    # List tests if requested
    if args.list:
        list_available_tests()
        return 0
    
    # Run tests
    success = run_tests(
        test_type=args.type,
        coverage=args.coverage,
        verbose=args.verbose,
        specific_test=args.test
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())