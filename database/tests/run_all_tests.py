#!/usr/bin/env python3
"""
Quick Launcher for Canvas API Master Test Suite

Simple wrapper to run the master test suite with common options.
"""

import sys
import os
import subprocess
from pathlib import Path

def main():
    """Quick launcher for master test suite."""
    print("🚀 Canvas API Master Test Suite Launcher")
    print("=" * 50)
    
    # Check if we're in the right directory
    if not Path("database/tests/run_master_test_suite.py").exists():
        print("❌ Error: Must run from Canvas-Tracker-V3 root directory")
        print("   Current directory:", os.getcwd())
        return 1
    
    # Show available options
    if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
        print("Usage:")
        print("  python database/tests/run_all_tests.py        # Run full master test suite")
        print("  python database/tests/run_all_tests.py --help # Show this help")
        print()
        print("The master test suite will run:")
        print("  • Single Course Processing")
        print("  • Configuration Impact Analysis") 
        print("  • Full Canvas API Pipeline")
        print("  • Bulk Processing (with user confirmation prompt)")
        print()
        print("Results are saved to database/tests/results/")
        return 0
    
    # Quick environment check
    canvas_dir = Path("canvas-interface")
    if not canvas_dir.exists():
        print("⚠️  Canvas interface directory not found!")
        print("   Make sure you're in the Canvas-Tracker-V3 root directory.")
        return 1
    
    env_file = canvas_dir / ".env"
    if not env_file.exists():
        print("⚠️  Canvas .env file not found!")
        print("   Make sure canvas-interface/.env exists with Canvas API credentials.")
        return 1
    
    print("✅ Environment looks good!")
    print("   Canvas interface: ✓")
    print("   Environment file: ✓")
    print()
    
    # Run the master test suite
    try:
        result = subprocess.run([
            "python", "database/tests/run_master_test_suite.py"
        ], check=False)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\n⏹️  Test suite cancelled by user")
        return 1
    except Exception as e:
        print(f"\n💥 Failed to run master test suite: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())