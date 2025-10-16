#!/usr/bin/env python3
"""
Multi-Course Canvas API Test Runner

Provides easy access to different multi-course testing scenarios.
"""

import subprocess
import sys
from pathlib import Path

def run_test(test_name: str, verbose: bool = True):
    """Run a specific test with proper arguments."""
    cmd = [
        "python", "-m", "pytest",
        f"database/tests/test_multi_course_canvas_pipeline.py::TestMultiCourseCanvasPipeline::{test_name}",
        "-s",  # Don't capture output
        "--tb=short"  # Short traceback format
    ]
    
    if verbose:
        cmd.append("-v")
    
    print(f"🧪 Running: {test_name}")
    print(f"📋 Command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        print(f"\n✅ {test_name} completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"\n❌ {test_name} failed with exit code {e.returncode}")
        return False

def show_available_tests():
    """Show available test scenarios."""
    print("\n🧪 Available Multi-Course Canvas API Tests")
    print("=" * 60)
    
    tests = {
        "1": {
            "name": "test_single_course_processing",
            "description": "Single course with multiple configurations",
            "requirements": "Just the JDU course (7982015)"
        },
        "2": {
            "name": "test_multi_course_processing",
            "description": "Multiple courses processing (individual + bulk)",
            "requirements": "Additional course IDs in ADDITIONAL_COURSES list"
        },
        "3": {
            "name": "test_all_available_courses", 
            "description": "All courses processing (use with extreme caution)",
            "requirements": "Admin access to Canvas instance"
        }
    }
    
    for key, test_info in tests.items():
        print(f"\n{key}. {test_info['name']}")
        print(f"   📋 {test_info['description']}")
        print(f"   📋 Requirements: {test_info['requirements']}")
    
    print(f"\n📝 Configuration Instructions:")
    print(f"   • Edit TEST_COURSES in test_multi_course_canvas_pipeline.py")
    print(f"   • Add real Canvas course IDs to ADDITIONAL_COURSES list")
    print(f"   • Course IDs found in URLs: /courses/{{COURSE_ID}}")

def main():
    """Main test runner interface."""
    if len(sys.argv) > 1:
        # Direct test execution
        test_arg = sys.argv[1]
        
        if test_arg == "single":
            return run_test("test_single_course_processing")
        elif test_arg == "multi":
            return run_test("test_multi_course_processing")
        elif test_arg == "all":
            print("⚠️  WARNING: This will test ALL courses in your Canvas instance!")
            response = input("Are you sure you want to continue? [y/N]: ")
            if response.lower() == 'y':
                return run_test("test_all_available_courses")
            else:
                print("❌ Cancelled")
                return False
        else:
            print(f"❌ Unknown test: {test_arg}")
            show_available_tests()
            return False
    
    # Interactive mode
    print("\nMulti-Course Canvas API Test Runner")
    print("=" * 50)
    
    show_available_tests()
    
    print(f"\n🎯 Quick Options:")
    print(f"   python run_multi_course_tests.py single    # Run single course test")
    print(f"   python run_multi_course_tests.py multi     # Run multi-course test")  
    print(f"   python run_multi_course_tests.py all       # Run all courses test")
    
    while True:
        choice = input(f"\nSelect test (1-3) or 'q' to quit: ").strip()
        
        if choice.lower() == 'q':
            print("👋 Goodbye!")
            break
        elif choice == "1":
            run_test("test_single_course_processing")
            break
        elif choice == "2":
            print("\n📋 Multi-course test requires additional course IDs.")
            print("   Please edit ADDITIONAL_COURSES in test_multi_course_canvas_pipeline.py")
            
            # Check if additional courses are configured
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("test_module", 
                    "database/tests/test_multi_course_canvas_pipeline.py")
                test_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(test_module)
                
                if len(test_module.TEST_COURSES["ADDITIONAL_COURSES"]) == 0:
                    print("❌ No additional courses configured. Please add course IDs first.")
                    continue
                else:
                    print(f"✅ Found {len(test_module.TEST_COURSES['ADDITIONAL_COURSES'])} additional courses")
                    run_test("test_multi_course_processing")
                    break
            except Exception as e:
                print(f"⚠️  Could not check course configuration: {e}")
                run_test("test_multi_course_processing")
                break
        elif choice == "3":
            print("⚠️  WARNING: This will test ALL courses in your Canvas instance!")
            response = input("Are you sure? [y/N]: ")
            if response.lower() == 'y':
                run_test("test_all_available_courses")
                break
            else:
                print("❌ Cancelled")
        else:
            print("❌ Invalid choice. Please select 1-3 or 'q'.")

if __name__ == "__main__":
    main()