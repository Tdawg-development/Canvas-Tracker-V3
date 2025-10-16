#!/usr/bin/env python
"""
Canvas Tracker Test Runner

Simple script to run different categories of tests with proper configuration.
"""

import sys
import subprocess
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_command(cmd, description):
    """Run a test command with proper error handling."""
    print(f"\n{'='*60}")
    print(f"🧪 {description}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, shell=True, check=True, cwd=str(project_root))
        print(f"✅ {description} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False

def main():
    """Main test runner."""
    if len(sys.argv) < 2:
        print("Canvas Tracker Test Runner")
        print("Usage: python run_tests.py [test_type]")
        print("")
        print("Available test types:")
        print("  all          - Run all tests")
        print("  unit         - Run only unit tests (fast)")
        print("  integration  - Run integration tests (requires database)")
        print("  canvas       - Run Canvas API integration tests (requires credentials)")
        print("  quick        - Run quick unit tests only")
        print("  verbose      - Run all tests with verbose output")
        print("")
        print("Examples:")
        print("  python run_tests.py unit")
        print("  python run_tests.py canvas")
        print("  python run_tests.py verbose")
        return

    test_type = sys.argv[1].lower()
    tests_dir = "database/tests"
    
    # Common pytest options
    base_options = "--tb=short --strict-markers --disable-warnings --color=yes"
    
    if test_type == "all":
        cmd = f"pytest {tests_dir} {base_options} -v"
        run_command(cmd, "Running All Tests")
        
    elif test_type == "unit":
        cmd = f"pytest {tests_dir} {base_options} -v -m unit"
        run_command(cmd, "Running Unit Tests")
        
    elif test_type == "integration":
        cmd = f"pytest {tests_dir} {base_options} -v -m integration"
        run_command(cmd, "Running Integration Tests")
        
    elif test_type == "canvas":
        print("\nCanvas API Integration Tests")
        print("These tests require:")
        print("  - Canvas interface directory at: canvas-interface/")
        print("  - Canvas API credentials in .env file")
        print("  - Access to Canvas course ID 7982015")
        print("  - Node.js and ts-node installed")
        print("")
        
        proceed = input("Do you want to proceed? [y/N]: ").lower().strip()
        if proceed in ('y', 'yes'):
            cmd = f"pytest {tests_dir}/test_real_canvas_api_pipeline.py {base_options} -v -s -m canvas_api"
            run_command(cmd, "Running Canvas API Integration Tests")
        else:
            print("Canvas API tests cancelled.")
            
    elif test_type == "quick":
        cmd = f"pytest {tests_dir} {base_options} -v -m unit --maxfail=5 -x"
        run_command(cmd, "Running Quick Unit Tests")
        
    elif test_type == "verbose":
        cmd = f"pytest {tests_dir} {base_options} -vvv -s"
        run_command(cmd, "Running All Tests (Verbose)")
        
    else:
        print(f"❌ Unknown test type: {test_type}")
        print("Run 'python run_tests.py' without arguments to see available options.")
        return

if __name__ == "__main__":
    main()