"""
Student Entity Transformer

Transforms Canvas student data from TypeScript format to database format with
configuration-driven field filtering and validation.
"""

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone

from .base import EntityTransformer, EntityType, TransformationContext
from .validation import ValidationIssue, ValidationSeverity


class StudentTransformer(EntityTransformer):
    """
    Transformer for Canvas student entities.
    
    Handles transformation from TypeScript student enrollment data
    to Python database CanvasStudent format with configurable field filtering.
    """
    
    @property
    def entity_type(self) -> EntityType:
        """Return the entity type this transformer handles."""
        return EntityType.STUDENTS
    
    @property
    def required_fields(self) -> Set[str]:
        """Return set of required fields for student entities."""
        return {
            'user_id',  # Canvas user ID (primary identifier)
            'id'        # Enrollment ID or student record ID
        }
    
    @property
    def optional_fields(self) -> Set[str]:
        """Return set of optional fields for student entities."""
        return {
            # Structural fields (containers for other data) - always needed
            'user',
            'grades', 
            
            # User information fields
            'name',
            'login_id', 
            'email',
            'sortable_name',
            
            # Grade fields  
            'current_score',
            'final_score',
            'current_grade',
            'final_grade',
            
            # Activity fields
            'last_activity_at',
            'last_attended_at',
            
            # Enrollment fields
            'enrollment_state',
            'enrollment_date', 
            'created_at',
            'updated_at',
            'course_section_id',
            'type',
            'role',
            'role_id',
            'limit_privileges_to_course_section',
            
            # Analytics fields (from Canvas analytics API)
            'submitted_assignments',
            'missing_assignments',
            'total_activity_time',
            'page_views'
        }
    
    def transform_entity(
        self, 
        entity_data: Dict[str, Any], 
        context: TransformationContext
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single student entity from Canvas format to database format.
        
        Args:
            entity_data: Student data from TypeScript (enrollment format)
            context: Transformation context with configuration
            
        Returns:
            Transformed student dict ready for database insertion
        """
        try:
            # Extract user information (handle both nested and flat structures)
            user_info = self._extract_user_info(entity_data)
            if not user_info:
                self.logger.warning(f"No user information found for student: {entity_data}")
                return None
            
            # Get IDs and ensure they are integers
            student_id = entity_data.get('id') or entity_data.get('user_id')
            user_id = user_info.get('id') or entity_data.get('user_id')
            
            if not student_id or not user_id:
                self.logger.warning(f"Missing required ID for student: {entity_data}")
                return None
            
            # Build base transformed student
            transformed_student = {
                'id': int(student_id),
                'student_id': int(student_id),  # Keep for database compatibility
                'user_id': int(user_id),
                'last_synced': datetime.now(timezone.utc)
            }
            
            # Apply configuration-based field inclusion
            config = context.configuration or {}
            student_fields = config.get('fields', {}).get('students', {})
            
            # Basic info fields (controlled by configuration)
            if student_fields.get('basicInfo', True):  # Default to True for backward compatibility
                transformed_student.update({
                    'name': user_info.get('name', 'Unknown'),
                    'login_id': user_info.get('login_id', 'unknown'),
                    'email': user_info.get('email', entity_data.get('email', ''))
                })
                
                # Optional basic info fields
                if 'sortable_name' in user_info:
                    transformed_student['sortable_name'] = user_info['sortable_name']
            else:
                # Even when basic info is disabled, we need some defaults
                transformed_student.update({
                    'name': 'Unknown',
                    'login_id': 'unknown', 
                    'email': '',
                    'sortable_name': 'Unknown'
                })
            
            # Score fields (controlled by configuration)  
            if student_fields.get('scores', True):  # Default to True
                # Handle grades from different locations
                grades = entity_data.get('grades', {})
                
                # Get scores from grades object first, then fallback to direct fields
                current_score = grades.get('current_score')
                if current_score is None:
                    current_score = entity_data.get('current_score')
                    
                final_score = grades.get('final_score')
                if final_score is None:
                    final_score = entity_data.get('final_score')
                
                transformed_student.update({
                    'current_score': self._normalize_score(current_score),
                    'final_score': self._normalize_score(final_score)
                })
                
                # Add grade letters if available
                if grades.get('current_grade'):
                    transformed_student['current_grade'] = grades['current_grade']
                if grades.get('final_grade'):
                    transformed_student['final_grade'] = grades['final_grade']
            else:
                # When scores are disabled, still include with default values for compatibility
                transformed_student.update({
                    'current_score': 0,
                    'final_score': 0
                })
            
            # Analytics fields (controlled by configuration)
            if student_fields.get('analytics', False):  # Default to False for performance
                self._add_optional_field(entity_data, transformed_student, 'last_activity_at', self._parse_canvas_datetime)
                self._add_optional_field(entity_data, transformed_student, 'last_attended_at', self._parse_canvas_datetime)
                
                # Assignment analytics
                if 'submitted_assignments' in entity_data:
                    transformed_student['submitted_assignments_count'] = len(entity_data['submitted_assignments'])
                if 'missing_assignments' in entity_data:
                    transformed_student['missing_assignments_count'] = len(entity_data['missing_assignments'])
                
                # Additional analytics if available
                self._add_optional_field(entity_data, transformed_student, 'total_activity_time')
                self._add_optional_field(entity_data, transformed_student, 'page_views', int)
            
            # Enrollment details (controlled by configuration)
            if student_fields.get('enrollmentDetails', False):  # Default to False
                transformed_student.update({
                    'enrollment_date': self._parse_canvas_datetime(entity_data.get('created_at')),
                    'enrollment_status': entity_data.get('enrollment_state', 'active'),
                    'created_at': self._parse_canvas_datetime(entity_data.get('created_at')),
                    'updated_at': datetime.now(timezone.utc)
                })
                
                # Additional enrollment fields
                self._add_optional_field(entity_data, transformed_student, 'course_section_id', int)
                self._add_optional_field(entity_data, transformed_student, 'type')
                self._add_optional_field(entity_data, transformed_student, 'role')
                self._add_optional_field(entity_data, transformed_student, 'role_id', int)
                self._add_optional_field(entity_data, transformed_student, 'limit_privileges_to_course_section', bool)
            else:
                # Always include minimal enrollment info
                transformed_student['enrollment_date'] = self._parse_canvas_datetime(entity_data.get('created_at'))
                transformed_student['created_at'] = self._parse_canvas_datetime(entity_data.get('created_at'))
                transformed_student['updated_at'] = datetime.now(timezone.utc)
            
            return transformed_student
            
        except Exception as e:
            self.logger.error(f"Failed to transform student {entity_data.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _validate_field_types(self, entity_data: Dict[str, Any]) -> List[str]:
        """
        Validate field types for student data.
        
        Args:
            entity_data: Student data to validate
            
        Returns:
            List of type validation errors
        """
        errors = []
        
        # Validate required field types
        for id_field in ['id', 'user_id']:
            if id_field in entity_data:
                try:
                    int(entity_data[id_field])
                except (ValueError, TypeError):
                    errors.append(f"Student '{id_field}' must be convertible to integer")
        
        # Validate score fields if present
        for score_field in ['current_score', 'final_score']:
            if score_field in entity_data and entity_data[score_field] is not None:
                try:
                    score = float(entity_data[score_field])
                    if score < 0 or score > 100:
                        errors.append(f"Student '{score_field}' must be between 0 and 100")
                except (ValueError, TypeError):
                    errors.append(f"Student '{score_field}' must be numeric")
        
        # Validate enrollment state
        if 'enrollment_state' in entity_data:
            valid_states = ['active', 'inactive', 'completed', 'deleted', 'invited']
            if entity_data['enrollment_state'] not in valid_states:
                errors.append(f"Student 'enrollment_state' must be one of {valid_states}")
        
        return errors
    
    def _extract_user_info(self, entity_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Extract user information from enrollment data.
        
        Args:
            entity_data: Student enrollment data
            
        Returns:
            User information dict or None if not found
        """
        # Check for nested user object
        user_info = entity_data.get('user', {})
        
        # If no nested user object, try to extract from flat structure
        if not user_info and entity_data.get('user_id'):
            user_info = {
                'id': entity_data.get('user_id'),
                'name': entity_data.get('name', 'Unknown'),
                'login_id': entity_data.get('login_id', 'unknown'),
                'email': entity_data.get('email', ''),
                'sortable_name': entity_data.get('sortable_name', 'Unknown')
            }
        
        return user_info if user_info.get('id') else None
    
    def _normalize_score(self, score: Any) -> float:
        """
        Normalize Canvas scores to float percentages with 2 decimal precision.
        
        Args:
            score: Score value from Canvas (may be None, float, or string)
            
        Returns:
            Float score (0.00-100.00) or 0.0 if invalid
        """
        if score is None:
            return 0.0
        
        try:
            # Convert to float and round to 2 decimal places
            float_score = float(score)
            return round(float_score, 2)
        except (ValueError, TypeError):
            self.logger.warning(f"Failed to normalize score '{score}', defaulting to 0.0")
            return 0.0
    
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
                try:
                    value = transform_func(value)
                except Exception as e:
                    self.logger.warning(f"Failed to transform field '{field_name}': {e}")
                    return
            target_data[field_name] = value
    
    def validate_configuration(self, field_config: Dict[str, bool]) -> List[ValidationIssue]:
        """
        Validate student-specific field configuration.
        
        Args:
            field_config: Field configuration for students
            
        Returns:
            List of validation issues specific to student configuration
        """
        issues = []
        
        # Define valid student field groups
        valid_field_groups = {
            'basicInfo',
            'scores',
            'analytics', 
            'enrollmentDetails'
        }
        
        # Check for unknown field groups
        for field_name in field_config.keys():
            if field_name not in valid_field_groups and field_name not in self.optional_fields:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=self.entity_type,
                    field_name=f'fields.students.{field_name}',
                    issue_code="UNKNOWN_STUDENT_FIELD",
                    message=f"Unknown student field configuration '{field_name}'",
                    suggestion=f"Valid field groups: {sorted(valid_field_groups)}, Valid individual fields: {sorted(self.optional_fields)}"
                ))
        
        # Validate field group combinations and implications
        if field_config.get('analytics', False) and not field_config.get('basicInfo', True):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                entity_type=self.entity_type,
                field_name='fields.students.analytics',
                issue_code="INCOMPLETE_STUDENT_CONFIG",
                message="Analytics enabled without basic info - analytics data may be less meaningful",
                suggestion="Consider enabling 'basicInfo' along with 'analytics' for better data context"
            ))
        
        # Check for performance implications
        if field_config.get('analytics', False) and field_config.get('enrollmentDetails', False):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                entity_type=self.entity_type,
                field_name='fields.students',
                issue_code="HIGH_PERFORMANCE_IMPACT",
                message="Both analytics and enrollment details enabled - may significantly impact performance",
                suggestion="Consider enabling only necessary field groups for large student populations"
            ))
        
        # Warn about missing core student data
        if not field_config.get('basicInfo', True) and not field_config.get('scores', True):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                entity_type=self.entity_type,
                field_name='fields.students',
                issue_code="MINIMAL_STUDENT_DATA",
                message="Both basic info and scores disabled - very limited student data will be collected",
                suggestion="Enable 'basicInfo' or 'scores' to collect meaningful student information"
            ))
        
        # Check privacy/compliance implications
        if field_config.get('analytics', False):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                entity_type=self.entity_type,
                field_name='fields.students.analytics',
                issue_code="PRIVACY_CONSIDERATION",
                message="Analytics data collection enabled - ensure compliance with privacy policies",
                suggestion="Verify that collecting detailed student analytics complies with your institution's privacy policies"
            ))
        
        return issues
    
    def apply_field_filtering(
        self, 
        entity_data: Dict[str, Any], 
        context: TransformationContext
    ) -> Dict[str, Any]:
        """
        Override field filtering to preserve structural data objects.
        
        Student data has nested 'user' and 'grades' objects that contain the actual
        field data. We need to preserve these structural containers even if specific
        fields within them are configured to be filtered.
        
        Args:
            entity_data: Original student entity data
            context: Transformation context with configuration
            
        Returns:
            Filtered entity data with structural objects preserved
        """
        if not context.configuration:
            return entity_data
            
        # For students, we need to preserve structural fields that contain nested data
        structural_fields = {'user', 'grades', 'id', 'user_id'}
        
        # Always include required fields and structural fields
        filtered_data = {}
        
        # Include required fields
        for field in self.required_fields:
            if field in entity_data:
                filtered_data[field] = entity_data[field]
        
        # Include structural fields (needed for data extraction)
        for field in structural_fields:
            if field in entity_data:
                filtered_data[field] = entity_data[field]
        
        # Include other fields based on configuration
        entity_config = context.configuration.get('fields', {}).get('students', {})
        
        # If no specific field config, include everything else
        if not entity_config:
            filtered_data.update(entity_data)
        else:
            # Include fields based on configuration groups and individual field settings
            for field in entity_data:
                if field not in filtered_data:  # Don't override already included fields
                    # Check if field should be included based on configuration
                    if field in entity_config and entity_config[field]:
                        filtered_data[field] = entity_data[field]
                    elif field in self.optional_fields and field not in entity_config:
                        # Include optional fields that aren't explicitly configured
                        filtered_data[field] = entity_data[field]
        
        return filtered_data
