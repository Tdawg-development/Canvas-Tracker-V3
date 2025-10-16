"""
Scalable Data Transformation System

This module provides a scalable, extensible data transformation system for Canvas entities
with configuration-driven field filtering and easy extensibility for new data types.

Key Features:
- Automatic transformer registration
- Configuration-driven field filtering  
- Extensible architecture for new Canvas data types
- Legacy compatibility bridge
- Comprehensive validation and error handling
"""

from .base import (
    EntityType, 
    EntityTransformer, 
    TransformerRegistry,
    TransformationContext,
    TransformationResult,
    get_global_registry,
    register_transformer
)

from .courses import CourseTransformer
from .students import StudentTransformer
from .assignments import AssignmentTransformer
from .enrollments import EnrollmentTransformer
from .validation import (
    ValidationSeverity,
    ValidationIssue,
    ConfigurationValidationResult,
    ConfigurationValidator,
    validate_sync_configuration
)

# Import future transformers here as they're added
# from .discussions import DiscussionTransformer


class LegacyCanvasDataTransformer:
    """
    Legacy compatibility bridge for existing CanvasDataTransformer interface.
    
    This class maintains backward compatibility with the existing codebase while
    internally using the new scalable transformation system. It provides the same
    public interface as the original CanvasDataTransformer but with enhanced
    configuration support.
    """
    
    def __init__(self, configuration=None):
        """Initialize legacy transformer with optional configuration."""
        from ..base.exceptions import ValidationError
        import logging
        
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.configuration = configuration
        self.registry = get_global_registry()
        
        # Store original exception for compatibility
        self.ValidationError = ValidationError
        
        self.logger.info("Legacy Canvas Data Transformer initialized with scalable backend")
    
    def transform_canvas_staging_data(self, canvas_data):
        """
        Legacy interface: Transform complete Canvas staging data to database format.
        
        Args:
            canvas_data: Complete Canvas data from TypeScript execution
            
        Returns:
            Dictionary with database-ready data organized by entity type
            
        Raises:
            ValidationError: If data validation fails
        """
        try:
            # Validate input structure (legacy compatibility)
            self._validate_canvas_data_structure(canvas_data)
            
            # Convert legacy format to registry format
            # Legacy: {'course': {...}, 'students': [...], 'modules': [...]}
            # Registry: {'courses': [...], 'students': [...], 'modules': [...]}
            registry_format_data = {}
            
            # Convert singular 'course' to plural 'courses' list
            if 'course' in canvas_data and canvas_data['course']:
                registry_format_data['courses'] = [canvas_data['course']]
            
            # Copy other entities as-is (they're already plural)
            for entity_key in ['students', 'modules', 'enrollments']:
                if entity_key in canvas_data:
                    registry_format_data[entity_key] = canvas_data[entity_key]
            
            # Handle assignments specially - extract from modules
            if 'modules' in canvas_data:
                registry_format_data['assignments'] = self._extract_assignments_from_modules(
                    canvas_data['modules'], 
                    canvas_data.get('course', {}).get('id')
                )
            
            # Handle enrollments specially - extract from students  
            if 'students' in canvas_data:
                registry_format_data['enrollments'] = self._extract_enrollments_from_students(
                    canvas_data['students'],
                    canvas_data.get('course', {}).get('id')
                )
            
            # Use new registry system for transformation
            transformation_results = self.registry.transform_entities(
                canvas_data=registry_format_data,
                configuration=self.configuration,
                course_id=canvas_data.get('course', {}).get('id')
            )
            
            # Convert new format to legacy format
            legacy_result = {}
            
            for entity_type, result in transformation_results.items():
                if result.success:
                    legacy_result[entity_type] = result.transformed_data
                    
                    # Log transformation summary (legacy style)
                    self.logger.info(f"Transformed {len(result.transformed_data)} {entity_type} records")
                else:
                    # Log errors but don't fail entirely (legacy behavior)
                    self.logger.error(f"Failed to transform {entity_type}: {result.errors}")
                    legacy_result[entity_type] = []
            
            # All entity types now have proper transformers - no legacy fallback needed
            
            # Ensure all expected entity types are present (legacy compatibility)
            for entity_type in ['courses', 'students', 'assignments', 'enrollments']:
                if entity_type not in legacy_result:
                    legacy_result[entity_type] = []
            
            return legacy_result
            
        except Exception as e:
            self.logger.error(f"Canvas data transformation failed: {str(e)}", exc_info=True)
            raise self.ValidationError(
                f"Failed to transform Canvas staging data: {str(e)}",
                operation_name="canvas_data_transformation"
            )
    
    def transform_course_data(self, course_data):
        """Legacy interface: Transform course data."""
        if not course_data or not course_data.get('id'):
            self.logger.warning("Empty or invalid course data provided")
            return []
        
        try:
            transformer = self.registry.get_transformer(EntityType.COURSES)
            context = TransformationContext(
                entity_type=EntityType.COURSES,
                source_data_count=1,
                configuration=self.configuration
            )
            result = transformer.transform_batch([course_data], context)
            return result.transformed_data
        except Exception as e:
            self.logger.error(f"Failed to transform course data: {str(e)}")
            raise self.ValidationError(
                f"Course data transformation failed: {str(e)}",
                field_name="course_data",
                operation_name="transform_course_data"
            )
    
    def transform_students_data(self, students_data):
        """Legacy interface: Transform students data."""
        if not students_data:
            self.logger.info("No student data to transform")
            return []
        
        try:
            transformer = self.registry.get_transformer(EntityType.STUDENTS)
            context = TransformationContext(
                entity_type=EntityType.STUDENTS,
                source_data_count=len(students_data),
                configuration=self.configuration
            )
            result = transformer.transform_batch(students_data, context)
            return result.transformed_data
        except Exception as e:
            self.logger.error(f"Failed to transform students data: {str(e)}")
            return []  # Legacy behavior: return empty list on error
    
    def transform_assignments_data(self, modules_data, course_id):
        """Legacy interface: Transform assignments from modules data."""
        if not modules_data or not course_id:
            self.logger.info("No modules data or course ID to transform assignments")
            return []
        
        # Extract assignments from modules (legacy behavior)
        assignments_data = []
        for module_data in modules_data:
            module_id = module_data.get('id')
            # Handle both 'assignments' and 'items' keys (Canvas API uses 'items')
            assignments = module_data.get('assignments', [])
            if not assignments:
                assignments = module_data.get('items', [])
            
            for assignment_data in assignments:
                # Add module context to assignment
                assignment_with_context = assignment_data.copy()
                assignment_with_context['course_id'] = course_id
                assignment_with_context['module_id'] = assignment_data.get('module_id') or module_id
                assignments_data.append(assignment_with_context)
        
        # Transform using legacy logic for now (to be replaced with AssignmentTransformer)
        return self._legacy_transform_assignments(assignments_data, course_id)
    
    def transform_enrollments_data(self, students_data, course_id):
        """Legacy interface: Transform enrollments from students data."""
        if not students_data or not course_id:
            self.logger.info("No students data or course ID to transform enrollments")
            return []
        
        # Transform using legacy logic for now (to be replaced with EnrollmentTransformer)
        return self._legacy_transform_enrollments(students_data, course_id)
    
    def get_transformation_summary(self, canvas_data):
        """Legacy interface: Get transformation summary."""
        try:
            summary = {
                'valid_structure': False,
                'course_count': 0,
                'student_count': 0,
                'module_count': 0,
                'assignment_count': 0,
                'errors': [],
                'warnings': []
            }
            
            # Validate structure
            try:
                self._validate_canvas_data_structure(canvas_data)
                summary['valid_structure'] = True
            except Exception as e:
                summary['errors'].append(str(e))
                return summary
            
            # Count entities
            summary['course_count'] = 1 if canvas_data.get('course', {}).get('id') else 0
            summary['student_count'] = len(canvas_data.get('students', []))
            summary['module_count'] = len(canvas_data.get('modules', []))
            
            # Count assignments across all modules
            assignment_count = 0
            for module_data in canvas_data.get('modules', []):
                assignments = module_data.get('assignments', [])
                assignment_count += len(assignments)
            summary['assignment_count'] = assignment_count
            
            return summary
            
        except Exception as e:
            return {
                'valid_structure': False,
                'error': f"Failed to generate summary: {str(e)}",
                'course_count': 0,
                'student_count': 0,
                'module_count': 0,
                'assignment_count': 0
            }
    
    def _validate_canvas_data_structure(self, canvas_data):
        """Legacy validation logic."""
        if not isinstance(canvas_data, dict):
            raise self.ValidationError(
                f"Canvas data must be a dictionary, got {type(canvas_data)}",
                operation_name="canvas_data_validation"
            )
        
        # Check for success flag
        if not canvas_data.get('success', False):
            error_info = canvas_data.get('error', {})
            raise self.ValidationError(
                f"Canvas data indicates failure: {error_info.get('message', 'Unknown error')}",
                operation_name="canvas_data_validation"
            )
        
        # Check for required top-level fields  
        required_fields = ['course', 'students', 'modules']
        missing_fields = [field for field in required_fields if field not in canvas_data]
        
        if missing_fields:
            raise self.ValidationError(
                f"Canvas data missing required fields: {missing_fields}",
                operation_name="canvas_data_validation"
            )
        
        # Validate course data has ID
        course_data = canvas_data.get('course', {})
        if not course_data.get('id'):
            raise self.ValidationError(
                "Course data missing required 'id' field",
                field_name="course.id",
                operation_name="canvas_data_validation"
            )
    
    def _legacy_transform_assignments(self, assignments_data, course_id):
        """Legacy assignment transformation logic (temporary)."""
        from datetime import datetime, timezone
        
        transformed_assignments = []
        
        for assignment_data in assignments_data:
            try:
                # Extract content details or points directly
                content_details = assignment_data.get('content_details', {})
                points_possible = content_details.get('points_possible')
                if points_possible is None:
                    points_possible = assignment_data.get('points_possible')
                
                # Parse timestamps with fallbacks
                current_time = datetime.now(timezone.utc)
                created_at = self._parse_canvas_datetime(assignment_data.get('created_at'))
                updated_at = self._parse_canvas_datetime(assignment_data.get('updated_at'))
                
                if created_at is None:
                    created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
                if updated_at is None:
                    updated_at = created_at if assignment_data.get('created_at') else current_time
                
                assignment_type = assignment_data.get('assignment_type') or assignment_data.get('type')
                
                # Handle both 'title' and 'name' for assignment name
                assignment_name = assignment_data.get('title') or assignment_data.get('name', '')
                
                transformed_assignment = {
                    'id': assignment_data.get('id'),
                    'course_id': course_id,
                    'module_id': assignment_data.get('module_id'),
                    'module_position': assignment_data.get('position'),
                    'url': assignment_data.get('url', ''),
                    'name': assignment_name,
                    'published': bool(assignment_data.get('published', False)),
                    'points_possible': points_possible,
                    'assignment_type': self._normalize_assignment_type(assignment_type),
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'last_synced': current_time
                }
                
                # Validate required fields
                if not transformed_assignment['id'] or not transformed_assignment['module_id']:
                    self.logger.warning(f"Assignment missing required fields: {assignment_data}")
                    continue
                
                transformed_assignments.append(transformed_assignment)
                
            except Exception as e:
                self.logger.error(f"Failed to transform assignment {assignment_data.get('id', 'unknown')}: {str(e)}")
                continue
        
        return transformed_assignments
    
    def _legacy_transform_enrollments(self, students_data, course_id):
        """Legacy enrollment transformation logic (temporary)."""
        from datetime import datetime, timezone
        
        transformed_enrollments = []
        
        for student_data in students_data:
            try:
                student_id = student_data.get('id') or student_data.get('user_id')
                if not student_id:
                    continue
                
                enrollment_date = self._parse_canvas_datetime(student_data.get('created_at'))
                if not enrollment_date:
                    enrollment_date = datetime.now(timezone.utc)
                
                transformed_enrollment = {
                    'student_id': int(student_id),
                    'course_id': int(course_id),
                    'enrollment_date': enrollment_date,
                    'enrollment_status': student_data.get('enrollment_state', 'active'),
                    'created_at': enrollment_date,
                    'updated_at': datetime.now(timezone.utc),
                    'last_synced': datetime.now(timezone.utc)
                }
                
                transformed_enrollments.append(transformed_enrollment)
                
            except Exception as e:
                self.logger.error(f"Failed to transform enrollment for student {student_data.get('id', 'unknown')}: {str(e)}")
                continue
        
        return transformed_enrollments
    
    def _parse_canvas_datetime(self, date_string):
        """Legacy datetime parsing."""
        if not date_string:
            return None
        
        try:
            from datetime import datetime, timezone
            
            if date_string.endswith('Z'):
                date_string = date_string.replace('Z', '+00:00')
            elif '+' not in date_string and '-' not in date_string[-6:]:
                date_string = date_string + '+00:00'
            
            dt = datetime.fromisoformat(date_string)
            
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse Canvas datetime '{date_string}': {e}")
            return None
    
    def _normalize_assignment_type(self, assignment_type):
        """Legacy assignment type normalization."""
        if not assignment_type:
            return 'Assignment'
        
        type_mapping = {
            'assignment': 'Assignment',
            'quiz': 'Quiz',
            'discussion': 'Discussion',
            'external_tool': 'ExternalTool',
            'page': 'Page'
        }
        
        return type_mapping.get(assignment_type.lower(), assignment_type)
    
    def _extract_assignments_from_modules(self, modules_data, course_id):
        """Extract assignments from Canvas modules data for new transformer system."""
        if not modules_data or not course_id:
            return []
        
        assignments_data = []
        for module_data in modules_data:
            module_id = module_data.get('id')
            # Handle both 'assignments' and 'items' keys (Canvas API uses 'items')
            assignments = module_data.get('assignments', [])
            if not assignments:
                assignments = module_data.get('items', [])
            
            for assignment_data in assignments:
                # Add module and course context to assignment
                assignment_with_context = assignment_data.copy()
                assignment_with_context['course_id'] = course_id
                assignment_with_context['module_id'] = assignment_data.get('module_id') or module_id
                assignments_data.append(assignment_with_context)
        
        return assignments_data
    
    def _extract_enrollments_from_students(self, students_data, course_id):
        """Extract enrollments from Canvas students data for new transformer system."""
        if not students_data or not course_id:
            return []
        
        enrollments_data = []
        for student_data in students_data:
            # Add course context to student for enrollment creation
            enrollment_data = student_data.copy()
            enrollment_data['course_id'] = course_id
            enrollments_data.append(enrollment_data)
        
        return enrollments_data


def _initialize_global_registry():
    """Initialize the global transformer registry with available transformers."""
    registry = get_global_registry()
    
    # Register available transformers
    registry.register_transformer(CourseTransformer())
    registry.register_transformer(StudentTransformer())
    registry.register_transformer(AssignmentTransformer())
    registry.register_transformer(EnrollmentTransformer())
    
    # Future transformers will be registered here:
    # registry.register_transformer(DiscussionTransformer())
    
    return registry


# Initialize registry on import
_initialize_global_registry()


# Legacy compatibility exports (maintain existing public interface)
def transform_canvas_data(canvas_data, configuration=None):
    """Legacy function: Transform Canvas data with default settings."""
    transformer = LegacyCanvasDataTransformer(configuration)
    return transformer.transform_canvas_staging_data(canvas_data)


def validate_canvas_data_structure(canvas_data):
    """Legacy function: Validate Canvas data structure."""
    transformer = LegacyCanvasDataTransformer()
    try:
        transformer._validate_canvas_data_structure(canvas_data)
        return {'valid': True, 'errors': []}
    except Exception as e:
        return {'valid': False, 'errors': [str(e)]}


def get_transformation_preview(canvas_data):
    """Legacy function: Preview transformation results.""" 
    transformer = LegacyCanvasDataTransformer()
    return transformer.get_transformation_summary(canvas_data)


# Export both new and legacy interfaces
__all__ = [
    # New scalable system
    'EntityType',
    'EntityTransformer', 
    'TransformerRegistry',
    'TransformationContext',
    'TransformationResult',
    'get_global_registry',
    'register_transformer',
    'CourseTransformer',
    'StudentTransformer',
    'AssignmentTransformer',
    'EnrollmentTransformer',
    
    # Legacy compatibility
    'LegacyCanvasDataTransformer',
    'transform_canvas_data',
    'validate_canvas_data_structure', 
    'get_transformation_preview',
    
    # Configuration validation
    'ValidationSeverity',
    'ValidationIssue', 
    'ConfigurationValidationResult',
    'ConfigurationValidator',
    'validate_sync_configuration'
]