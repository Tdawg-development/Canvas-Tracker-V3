"""
Database models for Canvas Tracker V3.

This package contains all SQLAlchemy models organized by architectural layers:
- Layer 0: Object lifecycle models (existence tracking)
- Layer 1: Canvas data models (pure sync data) 
- Layer 2: Historical data models (sync-generated)
- Layer 3: User metadata models (persistent)

Usage:
    # Import specific models
    from database.models import CanvasStudent, ObjectStatus, GradeHistory, StudentMetadata
    
    # Import all models from a specific layer
    from database.models.layer1_canvas import CanvasCourse, CanvasStudent
    from database.models.layer0_lifecycle import ObjectStatus, EnrollmentStatus
"""

# Models will be imported here as we implement each layer
# This allows clean imports throughout the application

__all__ = [
    # Layer imports will be populated as we implement each layer
]

# Layer imports will be added here as we implement each layer:
# from .layer0_lifecycle import ObjectStatus, EnrollmentStatus
# from .layer1_canvas import CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment  
# from .layer2_historical import GradeHistory, AssignmentScore
# from .layer3_metadata import StudentMetadata, AssignmentMetadata, CourseMetadata