#!/usr/bin/env python3
"""
TypeScript Interface Test

Tests the Python-TypeScript interface without making actual Canvas API calls.
This validates that the subprocess execution and JSON parsing works correctly.
"""

import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from database.operations.typescript_interface import TypeScriptExecutor

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_typescript_executor():
    """Test TypeScript executor creation and environment validation."""
    logger.info("🔍 Testing TypeScript executor initialization...")
    
    try:
        # Initialize executor
        canvas_path = str(project_root / "canvas-interface")
        executor = TypeScriptExecutor(canvas_path)
        
        logger.info("✅ TypeScript executor initialized successfully")
        
        # Test environment validation
        validation = executor.validate_execution_environment()
        
        if validation['valid']:
            logger.info("✅ TypeScript environment validation passed")
            logger.info(f"  - Node.js: {validation['node_version']}")
            logger.info(f"  - NPX available: {validation['npx_available']}")
            logger.info(f"  - TSX available: {validation['tsx_available']}")
            return True
        else:
            logger.error("❌ TypeScript environment validation failed:")
            for error in validation['errors']:
                logger.error(f"  - {error}")
            return False
            
    except Exception as e:
        logger.error(f"❌ TypeScript executor test failed: {e}")
        return False

def test_transformer_registry():
    """Test the transformer registry initialization."""
    logger.info("🔍 Testing transformer registry...")
    
    try:
        from database.operations.transformers import get_global_registry
        
        registry = get_global_registry()
        
        # Check available transformers
        available_types = registry.get_available_entity_types()
        logger.info("✅ Transformer registry initialized")
        logger.info(f"  Available transformers: {[et.value for et in available_types]}")
        
        # Get registry status
        status = registry.get_registry_status()
        logger.info(f"  Registered transformers: {status['registered_transformers']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Transformer registry test failed: {e}")
        return False

def test_database_tables():
    """Test database table creation."""
    logger.info("🔍 Testing database table creation...")
    
    try:
        from database.config import get_config
        from database.session import get_db_manager
        from database.models.layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
        
        # Use test environment
        config = get_config('test')
        db_manager = get_db_manager(config)
        
        # Create tables
        db_manager.create_all_tables()
        logger.info("✅ Database tables created successfully")
        
        # Test basic queries
        from database.session import get_session
        with get_session(config) as session:
            # Test table accessibility
            courses_count = session.query(CanvasCourse).count()
            students_count = session.query(CanvasStudent).count()
            assignments_count = session.query(CanvasAssignment).count()
            enrollments_count = session.query(CanvasEnrollment).count()
            
            logger.info(f"✅ Database queries successful:")
            logger.info(f"  - Courses table: {courses_count} records")
            logger.info(f"  - Students table: {students_count} records")
            logger.info(f"  - Assignments table: {assignments_count} records")
            logger.info(f"  - Enrollments table: {enrollments_count} records")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {e}")
        return False

def main():
    """Run all interface tests."""
    logger.info("🎯 TypeScript Interface Connection Test")
    logger.info("=" * 60)
    
    tests = [
        ("TypeScript Executor", test_typescript_executor),
        ("Transformer Registry", test_transformer_registry),
        ("Database Tables", test_database_tables)
    ]
    
    all_passed = True
    
    for test_name, test_func in tests:
        logger.info(f"\n🧪 {test_name} Test:")
        try:
            if not test_func():
                all_passed = False
        except Exception as e:
            logger.error(f"❌ {test_name} test failed with exception: {e}")
            all_passed = False
    
    logger.info("=" * 60)
    if all_passed:
        logger.info("🎉 All interface tests PASSED!")
        logger.info("✅ Your Canvas pipeline components are properly connected")
        logger.info("🚀 Ready to test with real Canvas course data")
    else:
        logger.error("❌ Some interface tests FAILED!")
        logger.error("🔧 Please fix the issues above")
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)