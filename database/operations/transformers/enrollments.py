"""
Enrollment Transformer

Transforms Canvas student enrollment data to database format using the scalable transformer architecture.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional

from .base import EntityTransformer, EntityType, TransformationContext


class EnrollmentTransformer(EntityTransformer):
    """
    Transform Canvas student enrollment data to database format.
    
    Extracts enrollment information from Canvas student data with full configuration support.
    """
    
    @property
    def entity_type(self) -> EntityType:
        return EntityType.ENROLLMENTS
    
    @property
    def required_fields(self) -> Set[str]:
        # Canvas provides 'id' or 'user_id' for student identification, not 'student_id'
        # We need either 'id' or 'user_id' (but at least one), plus course_id context
        # Since validation checks ALL required fields exist, we'll use the more common 'id'
        return {'id'}
    
    @property
    def optional_fields(self) -> Set[str]:
        return {
            'user_id', 'course_id', 'enrollment_state', 'enrollment_status',
            'created_at', 'updated_at', 'enrollment_date',
            'course_section_id', 'type', 'role', 'role_id'
        }
    
    def transform_entity(self, entity_data: Dict[str, Any], context: TransformationContext) -> Optional[Dict[str, Any]]:
        """Transform a single student enrollment entity."""
        try:
            # Extract student and course IDs
            student_id = entity_data.get('id') or entity_data.get('user_id')
            course_id = context.course_id if context.course_id else entity_data.get('course_id')
            
            if not student_id or not course_id:
                self.logger.warning(f"Enrollment missing required fields: student_id={student_id}, course_id={course_id}")
                return None
            
            # Parse enrollment status
            enrollment_status = (
                entity_data.get('enrollment_state') or 
                entity_data.get('enrollment_status') or 
                'active'
            )
            
            # Parse timestamps
            current_time = datetime.now(timezone.utc)
            created_at = self._parse_canvas_datetime(entity_data.get('created_at'))
            updated_at = self._parse_canvas_datetime(entity_data.get('updated_at'))
            
            # Use created_at as enrollment_date, or current time as fallback
            enrollment_date = created_at or current_time
            if not created_at:
                created_at = current_time
            if not updated_at:
                updated_at = current_time
            
            # Extract optional enrollment details
            course_section_id = entity_data.get('course_section_id')
            enrollment_type = entity_data.get('type')
            role = entity_data.get('role')
            role_id = entity_data.get('role_id')
            
            # Create transformed enrollment
            transformed_enrollment = {
                'student_id': int(student_id),
                'course_id': int(course_id),
                'enrollment_date': enrollment_date,
                'enrollment_status': self._normalize_enrollment_status(enrollment_status),
                'created_at': created_at,
                'updated_at': updated_at,
                'last_synced': current_time
            }
            
            # Add optional fields if present
            if course_section_id:
                transformed_enrollment['course_section_id'] = int(course_section_id)
            if enrollment_type:
                transformed_enrollment['enrollment_type'] = enrollment_type
            if role:
                transformed_enrollment['role'] = role
            if role_id:
                transformed_enrollment['role_id'] = int(role_id)
            
            return transformed_enrollment
            
        except Exception as e:
            self.logger.error(f"Failed to transform enrollment for student {entity_data.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _normalize_enrollment_status(self, status: str) -> str:
        """Normalize enrollment status to standard values."""
        if not status:
            return 'active'
        
        status_mapping = {
            'active': 'active',
            'invited': 'invited', 
            'inactive': 'inactive',
            'completed': 'completed',
            'deleted': 'deleted',
            'rejected': 'rejected'
        }
        
        normalized = status.lower().strip()
        return status_mapping.get(normalized, status)
    
    def _parse_canvas_datetime(self, date_string: str) -> Optional[datetime]:
        """Parse Canvas datetime string to UTC datetime object."""
        if not date_string:
            return None
        
        try:
            # Handle different Canvas datetime formats
            if date_string.endswith('Z'):
                date_string = date_string.replace('Z', '+00:00')
            elif '+' not in date_string and '-' not in date_string[-6:]:
                date_string = date_string + '+00:00'
            
            dt = datetime.fromisoformat(date_string)
            
            # Ensure UTC timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            elif dt.tzinfo != timezone.utc:
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, TypeError, AttributeError) as e:
            self.logger.warning(f"Failed to parse Canvas datetime '{date_string}': {e}")
            return None