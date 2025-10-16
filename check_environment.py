#!/usr/bin/env python3
"""
Canvas Environment Checker

Quick validation of Canvas interface setup before running full pipeline tests.
This checks Node.js, npm/npx, tsx, Canvas interface files, and database setup.
"""

import sys
import subprocess
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def check_node_environment():
    """Check Node.js and npm environment."""
    print("🔍 Checking Node.js environment...")
    
    try:
        # Check Node.js
        result = subprocess.run(['node', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"  ✅ Node.js: {result.stdout.strip()}")
        else:
            print(f"  ❌ Node.js not found")
            return False
            
        # Check NPX
        result = subprocess.run(['npx', '--version'], capture_output=True, text=True, shell=True)
        if result.returncode == 0:
            print(f"  ✅ NPX: {result.stdout.strip()}")
        else:
            print(f"  ❌ NPX not found")
            return False
            
    except FileNotFoundError:
        print("  ❌ Node.js/NPX not found in PATH")
        return False
    
    return True

def check_canvas_interface():
    """Check Canvas interface files."""
    print("🔍 Checking Canvas interface files...")
    
    canvas_path = project_root / "canvas-interface"
    if not canvas_path.exists():
        print(f"  ❌ Canvas interface directory not found: {canvas_path}")
        return False
    
    # Check root package.json (project is structured with package.json in root)
    root_package_json = project_root / "package.json"
    if root_package_json.exists():
        print(f"  ✅ package.json (in project root)")
    else:
        print(f"  ❌ package.json not found in project root")
        return False
    
    # Check Canvas interface files
    required_canvas_files = [
        "staging/canvas-data-constructor.ts",
        "staging/canvas-staging-data.ts"
    ]
    
    for file_path in required_canvas_files:
        full_path = canvas_path / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path} - NOT FOUND")
            return False
    
    # Check if dependencies are installed
    node_modules = project_root / "node_modules"
    if node_modules.exists():
        print(f"  ✅ node_modules (dependencies installed)")
    else:
        print(f"  ⚠️ node_modules not found - run 'npm install' in project root")
    
    return True

def check_tsx_availability():
    """Check if tsx is available for TypeScript execution."""
    print("🔍 Checking TypeScript execution environment...")
    
    canvas_path = project_root / "canvas-interface"
    
    try:
        result = subprocess.run(
            ['npx', 'tsx', '--version'], 
            capture_output=True, 
            text=True, 
            shell=True, 
            cwd=str(canvas_path),
            timeout=15
        )
        
        if result.returncode == 0:
            print(f"  ✅ TSX available")
            return True
        else:
            print(f"  ❌ TSX not available: {result.stderr}")
            return False
            
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        print(f"  ❌ TSX check failed: {e}")
        return False

def check_database_imports():
    """Check if database modules can be imported."""
    print("🔍 Checking database module imports...")
    
    try:
        from database.config import get_config
        print("  ✅ database.config")
        
        from database.session import get_session
        print("  ✅ database.session") 
        
        from database.operations.typescript_interface import validate_typescript_environment
        print("  ✅ database.operations.typescript_interface")
        
        from database.operations.transformers import get_global_registry
        print("  ✅ database.operations.transformers")
        
        return True
        
    except ImportError as e:
        print(f"  ❌ Import failed: {e}")
        return False

def check_canvas_api_credentials():
    """Check if Canvas API credentials are configured."""
    print("🔍 Checking Canvas API credentials...")
    
    # Check for .env file in canvas-interface directory first
    canvas_env_file = project_root / "canvas-interface" / ".env"
    root_env_file = project_root / ".env"
    
    if canvas_env_file.exists():
        print("  ✅ .env file exists (in canvas-interface)")
        return True
    elif root_env_file.exists():
        print("  ✅ .env file exists (in project root)")
        return True
    else:
        print("  ⚠️ .env file not found - Canvas API credentials may not be configured")
        print("  📝 Create .env file in project root with:")
        print("     CANVAS_URL=https://your-canvas-instance.com")
        print("     CANVAS_TOKEN=your_canvas_api_token")
        return False

def test_database_connection():
    """Test basic database connection."""
    print("🔍 Testing database connection...")
    
    try:
        from database.config import get_config
        from database.session import get_db_manager
        
        # Test with test environment
        config = get_config('test')
        db_manager = get_db_manager(config)
        
        # Test health check
        if db_manager.health_check():
            print("  ✅ Database connection successful")
            return True
        else:
            print("  ❌ Database health check failed")
            return False
            
    except Exception as e:
        print(f"  ❌ Database connection failed: {e}")
        return False

def main():
    """Main environment check."""
    print("🎯 Canvas Environment Validation")
    print("=" * 50)
    
    checks = [
        ("Node.js Environment", check_node_environment),
        ("Canvas Interface Files", check_canvas_interface),
        ("TypeScript Execution", check_tsx_availability),
        ("Database Imports", check_database_imports), 
        ("Database Connection", test_database_connection),
        ("Canvas API Credentials", check_canvas_api_credentials)
    ]
    
    all_passed = True
    
    for name, check_func in checks:
        try:
            if not check_func():
                all_passed = False
        except Exception as e:
            print(f"  ❌ {name} check failed with exception: {e}")
            all_passed = False
        print()
    
    print("=" * 50)
    if all_passed:
        print("🎉 Environment validation PASSED!")
        print("✅ Ready to run Canvas pipeline tests")
    else:
        print("❌ Environment validation FAILED!")
        print("🔧 Please fix the issues above before running pipeline tests")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)