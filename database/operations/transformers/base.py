"""
Base Transformation System

This module provides the foundation for a scalable, extensible data transformation
system that supports configuration-driven field filtering and easy addition of new
Canvas data types.

Key Components:
- EntityTransformer: Base class for all entity transformers
- TransformerRegistry: Discovery and registration system
- ConfigurationContext: Context for field filtering and validation
- ValidationSchemas: Extensible validation system
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Type, Union, Set, Callable
from datetime import datetime, timezone
from dataclasses import dataclass
from enum import Enum

from ..base.exceptions import ValidationError, DataValidationError


class EntityType(Enum):
    """Supported Canvas entity types."""
    COURSES = "courses"
    STUDENTS = "students" 
    ASSIGNMENTS = "assignments"
    ENROLLMENTS = "enrollments"
    MODULES = "modules"
    # Future extensibility
    DISCUSSIONS = "discussions"
    FILES = "files"
    PAGES = "pages"
    ANALYTICS = "analytics"


@dataclass
class TransformationContext:
    """Context information for transformation operations."""
    entity_type: EntityType
    source_data_count: int
    configuration: Optional[Dict[str, Any]] = None
    course_id: Optional[int] = None
    transformation_timestamp: datetime = None
    
    def __post_init__(self):
        if self.transformation_timestamp is None:
            self.transformation_timestamp = datetime.now(timezone.utc)


@dataclass 
class TransformationResult:
    """Result of entity transformation operation."""
    entity_type: EntityType
    success: bool
    transformed_data: List[Dict[str, Any]]
    source_count: int
    transformed_count: int
    skipped_count: int
    filtered_fields: Set[str]
    errors: List[str]
    warnings: List[str]
    processing_time_ms: Optional[float] = None
    
    @property
    def success_rate(self) -> float:
        """Calculate transformation success rate."""
        if self.source_count == 0:
            return 1.0
        return (self.transformed_count + self.skipped_count) / self.source_count


class EntityTransformer(ABC):
    """
    Abstract base class for all entity transformers.
    
    This class defines the interface that all entity transformers must implement,
    ensuring consistent behavior and extensibility across different Canvas data types.
    """
    
    def __init__(self):
        """Initialize entity transformer."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    @property
    @abstractmethod
    def entity_type(self) -> EntityType:
        """Return the entity type this transformer handles."""
        pass
        
    @property
    @abstractmethod
    def required_fields(self) -> Set[str]:
        """Return set of required fields for this entity type."""
        pass
        
    @property  
    @abstractmethod
    def optional_fields(self) -> Set[str]:
        """Return set of optional fields for this entity type."""
        pass
    
    @abstractmethod
    def transform_entity(
        self, 
        entity_data: Dict[str, Any], 
        context: TransformationContext
    ) -> Optional[Dict[str, Any]]:
        """
        Transform a single entity from Canvas format to database format.
        
        Args:
            entity_data: Raw entity data from Canvas API
            context: Transformation context with configuration
            
        Returns:
            Transformed entity dict, or None if should be skipped
        """
        pass
    
    def validate_entity_data(
        self, 
        entity_data: Dict[str, Any]
    ) -> List[str]:
        """
        Validate entity data structure and required fields.
        
        Args:
            entity_data: Entity data to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check required fields
        missing_required = self.required_fields - set(entity_data.keys())
        if missing_required:
            errors.append(f"Missing required fields: {missing_required}")
        
        # Check data types for known fields
        type_errors = self._validate_field_types(entity_data)
        errors.extend(type_errors)
        
        return errors
    
    def apply_field_filtering(
        self, 
        entity_data: Dict[str, Any], 
        context: TransformationContext
    ) -> Dict[str, Any]:
        """
        Apply configuration-driven field filtering.
        
        Args:
            entity_data: Original entity data
            context: Transformation context with configuration
            
        Returns:
            Filtered entity data
        """
        if not context.configuration:
            return entity_data
            
        # Get field configuration for this entity type
        entity_config = context.configuration.get('fields', {}).get(
            self.entity_type.value, {}
        )
        
        if not entity_config:
            return entity_data
        
        # Apply field filtering
        filtered_data = {}
        
        # Always include required fields
        for field in self.required_fields:
            if field in entity_data:
                filtered_data[field] = entity_data[field]
        
        # Check if configuration has explicit field-level settings
        has_explicit_field_config = any(
            field_name in self.optional_fields or field_name in self.required_fields
            for field_name in entity_config.keys()
        )
        
        if has_explicit_field_config:
            # Use explicit field configuration - only include fields that are explicitly enabled
            for field, include in entity_config.items():
                if include and field in entity_data:
                    filtered_data[field] = entity_data[field]
        else:
            # No explicit field configuration found - this appears to be group-level config
            # (like 'basicInfo': True, 'timestamps': True)
            # In this case, be permissive and include all optional fields
            for field in self.optional_fields:
                if field in entity_data:
                    filtered_data[field] = entity_data[field]
        
        return filtered_data
    
    def transform_batch(
        self, 
        entities_data: List[Dict[str, Any]], 
        context: TransformationContext
    ) -> TransformationResult:
        """
        Transform a batch of entities with comprehensive result tracking.
        
        Args:
            entities_data: List of entity data from Canvas
            context: Transformation context
            
        Returns:
            TransformationResult with detailed statistics
        """
        start_time = datetime.now()
        
        result = TransformationResult(
            entity_type=self.entity_type,
            success=True,
            transformed_data=[],
            source_count=len(entities_data),
            transformed_count=0,
            skipped_count=0,
            filtered_fields=set(),
            errors=[],
            warnings=[]
        )
        
        try:
            for i, entity_data in enumerate(entities_data):
                try:
                    # Validate entity data
                    validation_errors = self.validate_entity_data(entity_data)
                    if validation_errors:
                        result.errors.extend([
                            f"Entity {i}: {error}" for error in validation_errors
                        ])
                        result.skipped_count += 1
                        continue
                    
                    # Apply field filtering
                    filtered_data = self.apply_field_filtering(entity_data, context)
                    
                    # Track filtered fields
                    original_fields = set(entity_data.keys())
                    filtered_fields = set(filtered_data.keys())
                    result.filtered_fields.update(original_fields - filtered_fields)
                    
                    # Transform entity
                    transformed = self.transform_entity(filtered_data, context)
                    
                    if transformed is not None:
                        result.transformed_data.append(transformed)
                        result.transformed_count += 1
                    else:
                        result.skipped_count += 1
                        
                except Exception as e:
                    error_msg = f"Entity {i} transformation failed: {str(e)}"
                    result.errors.append(error_msg)
                    result.skipped_count += 1
                    self.logger.error(error_msg, exc_info=True)
            
            # Calculate processing time
            end_time = datetime.now()
            result.processing_time_ms = (end_time - start_time).total_seconds() * 1000
            
            # Log transformation summary
            self.logger.info(
                f"{self.entity_type.value} transformation: "
                f"{result.transformed_count}/{result.source_count} successful, "
                f"{result.skipped_count} skipped, {len(result.errors)} errors"
            )
            
        except Exception as e:
            result.success = False
            result.errors.append(f"Batch transformation failed: {str(e)}")
            self.logger.error(f"Batch transformation failed: {str(e)}", exc_info=True)
        
        # Determine final success - allow some errors but not complete failure
        if result.transformed_count > 0 and result.transformed_count >= (result.source_count * 0.5):
            result.success = True  # At least 50% transformed successfully
        elif result.source_count > 0 and result.transformed_count == 0:
            result.success = False  # Complete failure
        
        return result
    
    def _validate_field_types(self, entity_data: Dict[str, Any]) -> List[str]:
        """
        Validate field types for known fields.
        Override in subclasses for specific type validation.
        
        Args:
            entity_data: Entity data to validate
            
        Returns:
            List of type validation errors
        """
        # Base implementation - override in subclasses for specific validation
        return []


class TransformerRegistry:
    """
    Registry for discovering and managing entity transformers.
    
    Provides a central registry system that allows easy registration of new
    transformers and automatic discovery of transformation capabilities.
    """
    
    def __init__(self):
        """Initialize transformer registry."""
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._transformers: Dict[EntityType, EntityTransformer] = {}
        self._initialization_errors: List[str] = []
    
    def register_transformer(
        self, 
        transformer: EntityTransformer
    ) -> None:
        """
        Register a transformer for an entity type.
        
        Args:
            transformer: Entity transformer instance
        """
        entity_type = transformer.entity_type
        
        if entity_type in self._transformers:
            self.logger.warning(
                f"Overriding existing transformer for {entity_type.value}"
            )
        
        self._transformers[entity_type] = transformer
        self.logger.info(f"Registered transformer for {entity_type.value}")
    
    def get_transformer(self, entity_type: EntityType) -> EntityTransformer:
        """
        Get transformer for entity type.
        
        Args:
            entity_type: Entity type to get transformer for
            
        Returns:
            Entity transformer instance
            
        Raises:
            ValueError: If no transformer registered for entity type
        """
        if entity_type not in self._transformers:
            raise ValueError(
                f"No transformer registered for {entity_type.value}. "
                f"Available: {list(self._transformers.keys())}"
            )
        
        return self._transformers[entity_type]
    
    def has_transformer(self, entity_type: EntityType) -> bool:
        """Check if transformer is registered for entity type."""
        return entity_type in self._transformers
    
    def get_available_entity_types(self) -> List[EntityType]:
        """Get list of entity types with registered transformers."""
        return list(self._transformers.keys())
    
    def auto_register_transformers(self, transformer_module) -> None:
        """
        Automatically register transformers from a module.
        
        Args:
            transformer_module: Module containing transformer classes
        """
        registered_count = 0
        
        for attr_name in dir(transformer_module):
            attr = getattr(transformer_module, attr_name)
            
            # Check if it's a transformer class
            if (isinstance(attr, type) and 
                issubclass(attr, EntityTransformer) and 
                attr != EntityTransformer):
                
                try:
                    transformer_instance = attr()
                    self.register_transformer(transformer_instance)
                    registered_count += 1
                except Exception as e:
                    error_msg = f"Failed to register {attr_name}: {str(e)}"
                    self._initialization_errors.append(error_msg)
                    self.logger.error(error_msg)
        
        self.logger.info(f"Auto-registered {registered_count} transformers")
    
    def transform_entities(
        self,
        canvas_data: Dict[str, List[Dict[str, Any]]],
        configuration: Optional[Dict[str, Any]] = None,
        course_id: Optional[int] = None
    ) -> Dict[str, TransformationResult]:
        """
        Transform multiple entity types with configuration.
        
        Args:
            canvas_data: Dictionary of entity data from Canvas
            configuration: Sync configuration
            course_id: Course ID for context
            
        Returns:
            Dictionary mapping entity types to transformation results
        """
        results = {}
        
        for entity_name, entities_data in canvas_data.items():
            try:
                # Convert string to EntityType
                entity_type = EntityType(entity_name)
                
                if not self.has_transformer(entity_type):
                    self.logger.warning(f"No transformer available for {entity_name}")
                    continue
                
                # Check if entity is enabled in configuration
                if configuration and not configuration.get('entities', {}).get(entity_name, True):
                    self.logger.info(f"Skipping {entity_name} (disabled in configuration)")
                    continue
                
                # Check entity dependencies
                if entity_name == 'enrollments':
                    # Enrollments depend on students data - skip if students are disabled
                    students_enabled = configuration.get('entities', {}).get('students', True) if configuration else True
                    if not students_enabled:
                        self.logger.info(f"Skipping {entity_name} (depends on students which is disabled)")
                        continue
                
                # Create transformation context
                context = TransformationContext(
                    entity_type=entity_type,
                    source_data_count=len(entities_data),
                    configuration=configuration,
                    course_id=course_id
                )
                
                # Transform entities
                transformer = self.get_transformer(entity_type)
                result = transformer.transform_batch(entities_data, context)
                results[entity_name] = result
                
            except ValueError as e:
                self.logger.warning(f"Unknown entity type: {entity_name}")
                continue
            except Exception as e:
                error_msg = f"Failed to transform {entity_name}: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                
                # Create error result
                results[entity_name] = TransformationResult(
                    entity_type=EntityType(entity_name) if entity_name in [e.value for e in EntityType] else None,
                    success=False,
                    transformed_data=[],
                    source_count=len(entities_data) if entities_data else 0,
                    transformed_count=0,
                    skipped_count=0,
                    filtered_fields=set(),
                    errors=[error_msg],
                    warnings=[]
                )
        
        return results
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get current registry status and statistics."""
        return {
            'registered_transformers': len(self._transformers),
            'available_entity_types': [et.value for et in self._transformers.keys()],
            'initialization_errors': self._initialization_errors,
            'transformer_details': {
                et.value: {
                    'class_name': transformer.__class__.__name__,
                    'required_fields': list(transformer.required_fields),
                    'optional_fields': list(transformer.optional_fields)
                }
                for et, transformer in self._transformers.items()
            }
        }


# Global registry instance
_global_registry = TransformerRegistry()

def get_global_registry() -> TransformerRegistry:
    """Get the global transformer registry instance."""
    return _global_registry

def register_transformer(transformer: EntityTransformer) -> None:
    """Convenience function to register transformer in global registry."""
    _global_registry.register_transformer(transformer)