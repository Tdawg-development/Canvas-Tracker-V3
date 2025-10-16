"""
Assignment Transformer

Transforms Canvas assignment data to database format using the scalable transformer architecture.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Set, Optional

from .base import EntityTransformer, EntityType, TransformationContext


class AssignmentTransformer(EntityTransformer):
    """
    Transform Canvas assignment data to database format.
    
    Handles assignment data extraction from Canvas modules with full configuration support.
    """
    
    @property
    def entity_type(self) -> EntityType:
        return EntityType.ASSIGNMENTS
    
    @property
    def required_fields(self) -> Set[str]:
        return {'id', 'module_id', 'course_id'}
    
    @property
    def optional_fields(self) -> Set[str]:
        return {
            'name', 'title', 'url', 'published', 'points_possible', 'assignment_type',
            'type', 'position', 'module_position', 'content_details',
            'created_at', 'updated_at'
        }
    
    def transform_entity(self, entity_data: Dict[str, Any], context: TransformationContext) -> Optional[Dict[str, Any]]:
        """Transform a single assignment entity."""
        try:
            # Extract basic assignment info
            assignment_id = entity_data.get('id')
            module_id = entity_data.get('module_id')
            course_id = entity_data.get('course_id')
            
            if not all([assignment_id, module_id, course_id]):
                self.logger.warning(f"Assignment missing required fields: id={assignment_id}, module_id={module_id}, course_id={course_id}")
                return None
            
            # Extract assignment name (handle both 'title' and 'name')
            assignment_name = entity_data.get('title') or entity_data.get('name', '')
            
            # Extract points possible (handle both direct field and content_details)
            content_details = entity_data.get('content_details', {})
            points_possible = entity_data.get('points_possible')
            if points_possible is None:
                points_possible = content_details.get('points_possible')
            
            # Parse assignment type
            assignment_type = entity_data.get('assignment_type') or entity_data.get('type', 'Assignment')
            normalized_type = self._normalize_assignment_type(assignment_type)
            
            # Parse timestamps - preserve original Canvas values, no fallbacks to current time
            current_time = datetime.now(timezone.utc)
            created_at = self._parse_canvas_datetime(entity_data.get('created_at'))
            updated_at = self._parse_canvas_datetime(entity_data.get('updated_at'))
            
            # Create transformed assignment
            transformed_assignment = {
                'id': int(assignment_id),
                'course_id': int(course_id),
                'module_id': int(module_id),
                'name': assignment_name,
                'url': entity_data.get('url', ''),
                'published': bool(entity_data.get('published', False)),
                'points_possible': float(points_possible) if points_possible is not None else None,
                'assignment_type': normalized_type,
                'module_position': entity_data.get('position') or entity_data.get('module_position'),
                'created_at': created_at,
                'updated_at': updated_at,
                'last_synced': current_time
            }
            
            return transformed_assignment
            
        except Exception as e:
            self.logger.error(f"Failed to transform assignment {entity_data.get('id', 'unknown')}: {str(e)}")
            return None
    
    def _normalize_assignment_type(self, assignment_type: str) -> str:
        """Normalize assignment type to standard values."""
        if not assignment_type:
            return 'Assignment'
        
        type_mapping = {
            'assignment': 'Assignment',
            'quiz': 'Quiz',
            'discussion': 'Discussion',
            'external_tool': 'ExternalTool',
            'page': 'Page',
            'wiki_page': 'Page'
        }
        
        normalized = assignment_type.lower().strip()
        return type_mapping.get(normalized, assignment_type.title())
    
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