"""
Course Entity Transformer

Transforms Canvas course data from TypeScript format to database format with
configuration-driven field filtering and validation.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone

from .base import EntityTransformer, EntityType, TransformationContext
from .validation import ValidationIssue, ValidationSeverity


class CourseTransformer(EntityTransformer):
    """
    Transformer for Canvas course entities.
    
    Handles transformation from TypeScript CanvasCourseStaging format
    to Python database CanvasCourse format with configurable field filtering.
    """
    
    @property
    def entity_type(self) -> EntityType:
        """Return the entity type this transformer handles."""
        return EntityType.COURSES
    
    @property
    def required_fields(self) -> Set[str]:
        """Return set of required fields for course entities."""
        return {
            'id',
            'name', 
            'course_code'
        }
    
    @property
    def optional_fields(self) -> Set[str]:
        """Return set of optional fields for course entities."""
        return {
            'workflow_state',
            'start_at',
            'end_at', 
            'calendar',
            'created_at',
            'updated_at',
            'enrollment_term_id',
            'default_view',
            'is_public',
            'is_public_to_auth_users',
            'public_syllabus',
            'public_syllabus_to_auth',
            'public_description',
            'storage_quota_mb',
            'is_favorite',
            'apply_assignment_group_weights',
            'locale',
            'time_zone',
            'blueprint',
            'blueprint_restrictions',
            'template'
        }
    
    def transform_entity(
        self, 
        entity_data: Dict[str, Any], 
        context: TransformationContext
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single course entity from Canvas format to database format.
        
        Args:
            entity_data: Course data from TypeScript CanvasCourseStaging
            context: Transformation context with configuration
            
        Returns:
            Transformed course dict ready for database insertion
        """
        try:
            # Build base transformed course
            transformed_course = {
                'id': int(entity_data['id']),
                'name': entity_data.get('name', ''),
                'course_code': entity_data.get('course_code', ''),
                'workflow_state': entity_data.get('workflow_state', 'available'),
                'last_synced': datetime.now(timezone.utc)
            }
            
            # Add optional fields based on data availability and configuration
            self._add_optional_field(entity_data, transformed_course, 'start_at', self._parse_canvas_datetime)
            self._add_optional_field(entity_data, transformed_course, 'end_at', self._parse_canvas_datetime)
            self._add_optional_field(entity_data, transformed_course, 'created_at', self._parse_canvas_datetime)
            self._add_optional_field(entity_data, transformed_course, 'updated_at', self._parse_canvas_datetime)
            
            # Handle calendar ICS extraction
            calendar_ics = self._extract_calendar_ics(entity_data)
            if calendar_ics:
                transformed_course['calendar_ics'] = calendar_ics
            
            # Add metadata if available
            if 'metadata' in entity_data:
                metadata = entity_data['metadata']
                self._add_optional_field(metadata, transformed_course, 'total_students')
                self._add_optional_field(metadata, transformed_course, 'total_modules') 
                self._add_optional_field(metadata, transformed_course, 'total_assignments')
            
            # Add configuration-specific fields
            if context.configuration:
                course_fields = context.configuration.get('fields', {}).get('courses', {})
                
                # Add extended fields if configured
                if course_fields.get('extended_info', False):
                    self._add_optional_field(entity_data, transformed_course, 'enrollment_term_id')
                    self._add_optional_field(entity_data, transformed_course, 'default_view')
                    self._add_optional_field(entity_data, transformed_course, 'locale')
                    self._add_optional_field(entity_data, transformed_course, 'time_zone')
                
                if course_fields.get('public_info', False):
                    self._add_optional_field(entity_data, transformed_course, 'is_public', bool)
                    self._add_optional_field(entity_data, transformed_course, 'is_public_to_auth_users', bool)
                    self._add_optional_field(entity_data, transformed_course, 'public_syllabus', bool)
                    self._add_optional_field(entity_data, transformed_course, 'public_description')
                
                if course_fields.get('settings', False):
                    self._add_optional_field(entity_data, transformed_course, 'storage_quota_mb', int)
                    self._add_optional_field(entity_data, transformed_course, 'apply_assignment_group_weights', bool)
                    self._add_optional_field(entity_data, transformed_course, 'is_favorite', bool)
            
            return transformed_course
            
        except Exception as e:
            self.logger.error(f"Failed to transform course {entity_data.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _validate_field_types(self, entity_data: Dict[str, Any]) -> List[str]:
        """
        Validate field types for course data.
        
        Args:
            entity_data: Course data to validate
            
        Returns:
            List of type validation errors
        """
        errors = []
        
        # Validate required field types
        if 'id' in entity_data:
            try:
                int(entity_data['id'])
            except (ValueError, TypeError):
                errors.append("Course 'id' must be convertible to integer")
        
        if 'name' in entity_data and not isinstance(entity_data['name'], str):
            errors.append("Course 'name' must be a string")
        
        if 'course_code' in entity_data and not isinstance(entity_data['course_code'], str):
            errors.append("Course 'course_code' must be a string")
        
        # Validate optional field types
        if 'workflow_state' in entity_data:
            valid_states = ['available', 'unpublished', 'completed', 'deleted']
            if entity_data['workflow_state'] not in valid_states:
                errors.append(f"Course 'workflow_state' must be one of {valid_states}")
        
        return errors
    
    def _add_optional_field(
        self, 
        source_data: Dict[str, Any], 
        target_data: Dict[str, Any], 
        field_name: str,
        transform_func: Optional[callable] = None
    ) -> None:
        """
        Add optional field to target data if present in source.
        
        Args:
            source_data: Source data dictionary
            target_data: Target data dictionary  
            field_name: Field name to transfer
            transform_func: Optional transformation function
        """
        if field_name in source_data and source_data[field_name] is not None:
            value = source_data[field_name]
            if transform_func:
                value = transform_func(value)
            target_data[field_name] = value
    
    def _parse_canvas_datetime(self, date_string: str) -> Optional[datetime]:
        """
        Parse Canvas datetime strings to Python datetime objects.
        
        Args:
            date_string: Canvas datetime string (ISO 8601 format)
            
        Returns:
            Python datetime object with UTC timezone, or None if parsing fails
        """
        if not date_string:
            return None
        
        try:
            # Handle Canvas ISO 8601 format
            if date_string.endswith('Z'):
                date_string = date_string.replace('Z', '+00:00')
            elif '+' not in date_string and '-' not in date_string[-6:]:
                date_string = date_string + '+00:00'
            
            # Parse to datetime with timezone
            dt = datetime.fromisoformat(date_string)
            
            # Convert to UTC if not already
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse Canvas datetime '{date_string}': {e}")
            return None
    
    def _extract_calendar_ics(self, course_data: Dict[str, Any]) -> str:
        """
        Extract calendar ICS URL from course data.
        
        Args:
            course_data: Course data from TypeScript
            
        Returns:
            Calendar ICS URL or empty string
        """
        calendar = course_data.get('calendar')
        if isinstance(calendar, dict):
            return calendar.get('ics', '')
        return ''
    
    def validate_configuration(self, field_config: Dict[str, bool]) -> List[ValidationIssue]:
        """
        Validate course-specific field configuration.
        
        Args:
            field_config: Field configuration for courses
            
        Returns:
            List of validation issues specific to course configuration
        """
        issues = []
        
        # Define valid course field groups
        valid_field_groups = {
            'extended_info',
            'public_info', 
            'settings',
            'blueprint_info',
            'metadata'
        }
        
        # Check for unknown field groups
        for field_name in field_config.keys():
            if field_name not in valid_field_groups and field_name not in self.optional_fields:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=self.entity_type,
                    field_name=f'fields.courses.{field_name}',
                    issue_code="UNKNOWN_COURSE_FIELD",
                    message=f"Unknown course field configuration '{field_name}'",
                    suggestion=f"Valid field groups: {sorted(valid_field_groups)}, Valid individual fields: {sorted(self.optional_fields)}"
                ))
        
        # Validate field group combinations
        if field_config.get('public_info', False) and not field_config.get('extended_info', False):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                entity_type=self.entity_type,
                field_name='fields.courses.public_info',
                issue_code="INCOMPLETE_COURSE_CONFIG",
                message="Public info enabled without extended info - consider enabling extended_info for better context",
                suggestion="Enable 'extended_info' along with 'public_info' for comprehensive course data"
            ))
        
        # Check for performance-heavy combinations
        enabled_heavy_fields = sum(1 for field in ['extended_info', 'settings', 'blueprint_info'] 
                                 if field_config.get(field, False))
        if enabled_heavy_fields >= 3:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                entity_type=self.entity_type,
                field_name='fields.courses',
                issue_code="HIGH_PERFORMANCE_IMPACT",
                message="Multiple heavy field groups enabled - may impact performance",
                suggestion="Consider enabling only necessary field groups for better performance"
            ))
        
        return issues
