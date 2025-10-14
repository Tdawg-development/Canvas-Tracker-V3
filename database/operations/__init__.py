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

Usage:
    # Import specific operations
    from database.operations.layer1 import CanvasDataManager
    from database.operations.utilities import QueryBuilder
    
    # Import composite operations
    from database.operations.composite import SyncOrchestrator
"""

# Operations will be imported here as we implement each component
__all__ = [
    # Will be populated as we implement each operations component
]