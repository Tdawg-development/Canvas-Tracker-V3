"""
Database Operations Package for Canvas Tracker V3.

This package provides high-level, business-focused APIs that abstract away
the complexities of our 4-layer database model interactions. The operations
layer adopts a hybrid approach balancing flexibility, performance, and maintainability.

Package Structure:
- base/: Foundation classes and transaction management
- layer0/: Object lifecycle management operations  
- layer1/: Canvas data CRUD and sync operations
- layer2/: Historical data operations and analytics
- layer3/: User metadata and tag management operations
- composite/: Cross-layer sync orchestration and coordination
- utilities/: Query builders, analytics, and performance utilities
- Canvas Integration Bridge: TypeScript-Python integration components

Usage:
    # Import Canvas bridge components (Phase 1 - Critical Integration)
    from database.operations import CanvasDataBridge, TypeScriptExecutor
    from database.operations import get_global_registry  # New modular transformer system
    from database.operations import initialize_canvas_course  # Convenience function
    
    # Use new transformer system (recommended)
    registry = get_global_registry()
    result = registry.transform_entities(canvas_data, configuration)
    
    # Import specific operations
    from database.operations.layer1 import CanvasDataManager
    from database.operations.utilities import QueryBuilder
    
    # Import composite operations
    from database.operations.composite import SyncOrchestrator
"""

# ==================== CANVAS INTEGRATION BRIDGE (Phase 1) ====================
# These are the critical integration components that bridge TypeScript Canvas interface
# with Python database operations - the key unlock for the entire system

try:
    from .canvas_bridge import CanvasDataBridge, CanvasBridgeResult, initialize_canvas_course
    from .typescript_interface import TypeScriptExecutor, TypeScriptExecutionError
    
    # Import new transformer system (replaces legacy CanvasDataTransformer)
    from .transformers import get_global_registry, TransformerRegistry
    from .transformers import LegacyCanvasDataTransformer  # Legacy compatibility
    
    # Mark Canvas bridge components as available
    CANVAS_BRIDGE_AVAILABLE = True
except ImportError as e:
    # Canvas bridge components not yet implemented or have dependencies missing
    CANVAS_BRIDGE_AVAILABLE = False
    import warnings
    warnings.warn(f"Canvas bridge components not available: {e}", UserWarning)

# ==================== EXISTING OPERATIONS ====================
# Import existing operations components

try:
    from .layer1.canvas_ops import CanvasDataManager
    from .layer1.sync_coordinator import SyncCoordinator, SyncResult, SyncPriority
    from .layer1.relationship_manager import RelationshipManager
    LAYER1_AVAILABLE = True
except ImportError:
    LAYER1_AVAILABLE = False

try:
    from .utilities.query_builder import QueryBuilder
    UTILITIES_AVAILABLE = True
except ImportError:
    UTILITIES_AVAILABLE = False

try:
    from .base.base_operations import BaseOperation, CRUDOperation
    from .base.transaction_manager import TransactionManager
    from .base.exceptions import (
        OperationError, ValidationError, TransactionError, 
        CanvasOperationError, DataValidationError
    )
    BASE_AVAILABLE = True
except ImportError:
    BASE_AVAILABLE = False

# ==================== PACKAGE EXPORTS ====================

__all__ = []

# Canvas Integration Bridge exports (Phase 1 - Critical)
if CANVAS_BRIDGE_AVAILABLE:
    __all__.extend([
        'CanvasDataBridge',
        'CanvasBridgeResult', 
        'TypeScriptExecutor',
        'TypeScriptExecutionError',
        'get_global_registry',  # New transformer system
        'TransformerRegistry',  # New transformer system
        'LegacyCanvasDataTransformer',  # Legacy compatibility
        'initialize_canvas_course',  # Convenience function
    ])

# Layer 1 operations exports
if LAYER1_AVAILABLE:
    __all__.extend([
        'CanvasDataManager',
        'SyncCoordinator',
        'SyncResult',
        'SyncPriority',
        'RelationshipManager',
    ])

# Utilities exports
if UTILITIES_AVAILABLE:
    __all__.extend([
        'QueryBuilder',
    ])

# Base operations exports
if BASE_AVAILABLE:
    __all__.extend([
        'BaseOperation',
        'CRUDOperation', 
        'TransactionManager',
        'OperationError',
        'ValidationError',
        'TransactionError',
        'CanvasOperationError',
        'DataValidationError',
    ])

# ==================== PACKAGE METADATA ====================

# Package status information
PACKAGE_STATUS = {
    'canvas_bridge': CANVAS_BRIDGE_AVAILABLE,
    'layer1_operations': LAYER1_AVAILABLE,
    'utilities': UTILITIES_AVAILABLE,
    'base_operations': BASE_AVAILABLE,
    'phase1_complete': CANVAS_BRIDGE_AVAILABLE and LAYER1_AVAILABLE and BASE_AVAILABLE
}

# Phase 1 completion status
PHASE1_COMPLETE = PACKAGE_STATUS['phase1_complete']

def get_package_status():
    """Get current package status and component availability."""
    return PACKAGE_STATUS.copy()

def check_canvas_bridge_ready():
    """Check if Canvas bridge is ready for use."""
    return {
        'ready': CANVAS_BRIDGE_AVAILABLE,
        'missing_components': []
        if CANVAS_BRIDGE_AVAILABLE 
        else ['CanvasDataBridge', 'TypeScriptExecutor', 'TransformerRegistry']
    }
