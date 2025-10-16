"""
Configuration Validation System

Provides comprehensive validation for sync configurations, ensuring compatibility
between Canvas data availability and transformation requirements.
"""

import logging
from typing import Dict, List, Optional, Any, Set, Union
from dataclasses import dataclass
from enum import Enum

from .base import EntityType, TransformerRegistry


class ValidationSeverity(Enum):
    """Validation issue severity levels."""
    ERROR = "error"      # Prevents operation
    WARNING = "warning"  # May cause issues but operation can continue
    INFO = "info"       # Informational only


@dataclass
class ValidationIssue:
    """Container for validation issues."""
    severity: ValidationSeverity
    entity_type: Optional[EntityType]
    field_name: Optional[str]
    issue_code: str
    message: str
    suggestion: Optional[str] = None


@dataclass 
class ConfigurationValidationResult:
    """Result of configuration validation."""
    valid: bool
    issues: List[ValidationIssue]
    validated_configuration: Optional[Dict[str, Any]]
    performance_estimate: Optional[Dict[str, Any]] = None
    
    @property
    def errors(self) -> List[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.ERROR]
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.WARNING]
    
    @property
    def infos(self) -> List[ValidationIssue]:
        """Get only info-level issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.INFO]


class ConfigurationValidator:
    """
    Validates sync configurations for correctness and compatibility.
    
    Ensures that requested configurations are valid, available transformers
    can handle the requests, and provides performance estimates.
    """
    
    def __init__(self, registry: TransformerRegistry):
        """Initialize validator with transformer registry."""
        self.registry = registry
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    def validate_configuration(
        self, 
        configuration: Dict[str, Any],
        canvas_data_sample: Optional[Dict[str, Any]] = None
    ) -> ConfigurationValidationResult:
        """
        Validate sync configuration comprehensively.
        
        Args:
            configuration: Sync configuration to validate
            canvas_data_sample: Optional sample data for field validation
            
        Returns:
            ConfigurationValidationResult with detailed findings
        """
        issues = []
        validated_config = configuration.copy()
        
        try:
            # 1. Validate configuration structure
            structure_issues = self._validate_structure(configuration)
            issues.extend(structure_issues)
            
            # 2. Validate entity configurations
            entity_issues = self._validate_entities(configuration)
            issues.extend(entity_issues)
            
            # 3. Validate field configurations
            field_issues = self._validate_fields(configuration, canvas_data_sample)
            issues.extend(field_issues)
            
            # 4. Validate transformer compatibility
            transformer_issues = self._validate_transformer_compatibility(configuration)
            issues.extend(transformer_issues)
            
            # 5. Generate performance estimate
            performance_estimate = self._estimate_performance_impact(configuration)
            
            # 6. Apply configuration fixes/defaults
            validated_config = self._apply_configuration_fixes(configuration, issues)
            
            # Determine if configuration is valid (no errors)
            has_errors = any(issue.severity == ValidationSeverity.ERROR for issue in issues)
            
            result = ConfigurationValidationResult(
                valid=not has_errors,
                issues=issues,
                validated_configuration=validated_config,
                performance_estimate=performance_estimate
            )
            
            self.logger.info(
                f"Configuration validation: {len(issues)} issues "
                f"({len(result.errors)} errors, {len(result.warnings)} warnings)"
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {str(e)}", exc_info=True)
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                entity_type=None,
                field_name=None,
                issue_code="VALIDATION_FAILED",
                message=f"Configuration validation failed: {str(e)}"
            ))
            
            return ConfigurationValidationResult(
                valid=False,
                issues=issues,
                validated_configuration=None
            )
    
    def _validate_structure(self, configuration: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate basic configuration structure."""
        issues = []
        
        # Check for required top-level keys
        if 'entities' not in configuration:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                entity_type=None,
                field_name='entities',
                issue_code="MISSING_ENTITIES",
                message="Configuration missing 'entities' section",
                suggestion="Add entities configuration with at least one enabled entity"
            ))
        
        # Validate entities structure
        entities = configuration.get('entities', {})
        if not isinstance(entities, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                entity_type=None,
                field_name='entities',
                issue_code="INVALID_ENTITIES_TYPE",
                message="'entities' must be a dictionary",
                suggestion="Use format: {'students': True, 'assignments': False, ...}"
            ))
        elif not entities:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                entity_type=None,
                field_name='entities',
                issue_code="EMPTY_ENTITIES",
                message="No entities configured - no data will be collected",
                suggestion="Enable at least one entity type for data collection"
            ))
        
        # Validate fields structure if present
        if 'fields' in configuration:
            fields = configuration['fields']
            if not isinstance(fields, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    entity_type=None,
                    field_name='fields',
                    issue_code="INVALID_FIELDS_TYPE", 
                    message="'fields' must be a dictionary",
                    suggestion="Use format: {'students': {'basicInfo': True, 'scores': False}, ...}"
                ))
        
        return issues
    
    def _validate_entities(self, configuration: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate entity configurations."""
        issues = []
        entities = configuration.get('entities', {})
        
        # Check for unknown entity types
        known_entities = {et.value for et in EntityType}
        for entity_name in entities.keys():
            if entity_name not in known_entities:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=None,
                    field_name=f'entities.{entity_name}',
                    issue_code="UNKNOWN_ENTITY_TYPE",
                    message=f"Unknown entity type '{entity_name}'",
                    suggestion=f"Known entity types: {sorted(known_entities)}"
                ))
        
        # Check for entities without available transformers
        available_transformers = {et.value for et in self.registry.get_available_entity_types()}
        enabled_entities = {name for name, enabled in entities.items() if enabled}
        
        for entity_name in enabled_entities:
            if entity_name in known_entities and entity_name not in available_transformers:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    entity_type=EntityType(entity_name) if entity_name in known_entities else None,
                    field_name=f'entities.{entity_name}',
                    issue_code="NO_TRANSFORMER_AVAILABLE",
                    message=f"No transformer available for enabled entity '{entity_name}'",
                    suggestion=f"Available transformers: {sorted(available_transformers)}"
                ))
        
        # Check for potentially conflicting entity configurations
        if entities.get('students', True) and not entities.get('enrollments', True):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                entity_type=EntityType.STUDENTS,
                field_name='entities.enrollments',
                issue_code="MISSING_ENROLLMENT_DATA",
                message="Students enabled but enrollments disabled - may affect data relationships",
                suggestion="Consider enabling enrollments for complete student data"
            ))
        
        return issues
    
    def _validate_fields(
        self, 
        configuration: Dict[str, Any], 
        canvas_data_sample: Optional[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate field configurations."""
        issues = []
        fields = configuration.get('fields', {})
        entities = configuration.get('entities', {})
        
        for entity_name, field_config in fields.items():
            # Skip validation for disabled entities
            if not entities.get(entity_name, True):
                continue
            
            # Check if entity type exists
            if entity_name not in {et.value for et in EntityType}:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=None,
                    field_name=f'fields.{entity_name}',
                    issue_code="UNKNOWN_ENTITY_IN_FIELDS",
                    message=f"Field configuration for unknown entity '{entity_name}'",
                    suggestion="Remove field configuration or correct entity name"
                ))
                continue
            
            # Validate field configuration structure
            if not isinstance(field_config, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    entity_type=EntityType(entity_name),
                    field_name=f'fields.{entity_name}',
                    issue_code="INVALID_FIELD_CONFIG_TYPE",
                    message=f"Field configuration for '{entity_name}' must be a dictionary",
                    suggestion="Use format: {'fieldName': True/False, ...}"
                ))
                continue
            
            # Validate against transformer requirements if transformer available
            try:
                entity_type = EntityType(entity_name)
                if self.registry.has_transformer(entity_type):
                    transformer = self.registry.get_transformer(entity_type)
                    field_issues = self._validate_transformer_fields(
                        transformer, field_config, entity_name, canvas_data_sample
                    )
                    issues.extend(field_issues)
                    
                    # Call transformer-specific validation if available
                    if hasattr(transformer, 'validate_configuration'):
                        transformer_issues = transformer.validate_configuration(field_config)
                        issues.extend(transformer_issues)
            except ValueError:
                # Entity type not in enum - already handled above
                pass
        
        return issues
    
    def _validate_transformer_fields(
        self,
        transformer,
        field_config: Dict[str, bool],
        entity_name: str,
        canvas_data_sample: Optional[Dict[str, Any]]
    ) -> List[ValidationIssue]:
        """Validate field configuration against transformer capabilities."""
        issues = []
        
        # Get transformer's known fields
        required_fields = transformer.required_fields
        optional_fields = transformer.optional_fields
        all_known_fields = required_fields.union(optional_fields)
        
        # Check for unknown fields in configuration
        for field_name in field_config.keys():
            if field_name not in all_known_fields:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=transformer.entity_type,
                    field_name=f'fields.{entity_name}.{field_name}',
                    issue_code="UNKNOWN_FIELD_IN_CONFIG",
                    message=f"Unknown field '{field_name}' in {entity_name} configuration",
                    suggestion=f"Known fields: {sorted(all_known_fields)}"
                ))
        
        # Check if any required fields are explicitly disabled (shouldn't be possible but validate)
        for field_name, enabled in field_config.items():
            if not enabled and field_name in required_fields:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    entity_type=transformer.entity_type,
                    field_name=f'fields.{entity_name}.{field_name}',
                    issue_code="REQUIRED_FIELD_DISABLED",
                    message=f"Required field '{field_name}' cannot be disabled for {entity_name}",
                    suggestion="Remove field from configuration or set to true"
                ))
        
        # Validate against sample data if available
        if canvas_data_sample:
            entity_sample = canvas_data_sample.get(entity_name, [])
            if entity_sample and isinstance(entity_sample, list) and len(entity_sample) > 0:
                sample_item = entity_sample[0]
                self._validate_fields_against_sample(
                    field_config, sample_item, entity_name, issues
                )
        
        return issues
    
    def _validate_fields_against_sample(
        self,
        field_config: Dict[str, bool],
        sample_data: Dict[str, Any],
        entity_name: str,
        issues: List[ValidationIssue]
    ) -> None:
        """Validate field configuration against sample data."""
        sample_fields = set(sample_data.keys())
        
        # Check for enabled fields not available in sample data
        for field_name, enabled in field_config.items():
            if enabled and field_name not in sample_fields:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    entity_type=EntityType(entity_name) if entity_name in {et.value for et in EntityType} else None,
                    field_name=f'fields.{entity_name}.{field_name}',
                    issue_code="FIELD_NOT_IN_SAMPLE",
                    message=f"Enabled field '{field_name}' not found in {entity_name} sample data",
                    suggestion="Verify field name or check if field is available in your Canvas instance"
                ))
    
    def _validate_transformer_compatibility(self, configuration: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate compatibility with available transformers."""
        issues = []
        entities = configuration.get('entities', {})
        
        # Check registry status
        registry_status = self.registry.get_registry_status()
        if registry_status.get('initialization_errors'):
            for error in registry_status['initialization_errors']:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    entity_type=None,
                    field_name=None,
                    issue_code="TRANSFORMER_INIT_ERROR",
                    message=f"Transformer initialization error: {error}",
                    suggestion="Check transformer implementation and dependencies"
                ))
        
        # Validate each enabled entity has a working transformer
        for entity_name, enabled in entities.items():
            if enabled and entity_name in {et.value for et in EntityType}:
                try:
                    entity_type = EntityType(entity_name)
                    if not self.registry.has_transformer(entity_type):
                        issues.append(ValidationIssue(
                            severity=ValidationSeverity.ERROR,
                            entity_type=entity_type,
                            field_name=f'entities.{entity_name}',
                            issue_code="MISSING_TRANSFORMER",
                            message=f"No transformer registered for enabled entity '{entity_name}'",
                            suggestion="Implement and register transformer for this entity type"
                        ))
                except ValueError:
                    # Already handled in entity validation
                    pass
        
        return issues
    
    def _estimate_performance_impact(self, configuration: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate performance impact of configuration."""
        entities = configuration.get('entities', {})
        fields = configuration.get('fields', {})
        
        enabled_entities = [name for name, enabled in entities.items() if enabled]
        
        # More accurate performance estimation
        base_impact = len(enabled_entities) * 0.15  # Base cost per entity type
        
        # Add field complexity impact with heavier weighting
        field_impact = 0.0
        for entity_name, field_config in fields.items():
            if entities.get(entity_name, True):  # Only count if entity enabled
                enabled_fields = sum(1 for enabled in field_config.values() if enabled)
                # Different entities have different complexity impacts
                if entity_name == 'students' and enabled_fields >= 3:
                    field_impact += enabled_fields * 0.1  # Heavy impact for student analytics
                elif entity_name == 'courses' and enabled_fields >= 3:
                    field_impact += enabled_fields * 0.08  # Moderate impact for course details
                else:
                    field_impact += enabled_fields * 0.05  # Standard impact
        
        total_impact = base_impact + field_impact
        
        return {
            'enabled_entities': len(enabled_entities),
            'entity_types': enabled_entities,
            'estimated_relative_cost': min(total_impact, 1.0),  # Cap at 1.0
            'performance_category': self._categorize_performance(total_impact),
            'api_call_estimate': len(enabled_entities) * 2,  # Rough estimate
            'memory_impact': 'low' if total_impact < 0.3 else 'medium' if total_impact < 0.7 else 'high'
        }
    
    def _categorize_performance(self, impact: float) -> str:
        """Categorize performance impact."""
        if impact < 0.2:
            return 'very_light'
        elif impact < 0.4:
            return 'light'
        elif impact < 0.6:
            return 'moderate'
        elif impact < 0.8:
            return 'heavy'
        else:
            return 'very_heavy'
    
    def _apply_configuration_fixes(
        self, 
        configuration: Dict[str, Any], 
        issues: List[ValidationIssue]
    ) -> Dict[str, Any]:
        """Apply automatic fixes to configuration based on validation issues."""
        fixed_config = configuration.copy()
        
        # Apply fixes for specific issue codes
        for issue in issues:
            if issue.issue_code == "MISSING_ENTITIES" and issue.severity != ValidationSeverity.ERROR:
                # Add default entities if missing
                if 'entities' not in fixed_config:
                    fixed_config['entities'] = {
                        'courses': True,
                        'students': True,
                        'assignments': False,
                        'enrollments': False
                    }
            
            elif issue.issue_code == "REQUIRED_FIELD_DISABLED":
                # Re-enable required fields
                if issue.field_name and 'fields' in fixed_config:
                    field_path = issue.field_name.replace('fields.', '').split('.')
                    if len(field_path) == 2:
                        entity_name, field_name = field_path
                        if entity_name in fixed_config['fields']:
                            fixed_config['fields'][entity_name][field_name] = True
        
        return fixed_config


# Convenience functions
def validate_sync_configuration(
    configuration: Dict[str, Any],
    registry: Optional[TransformerRegistry] = None,
    canvas_data_sample: Optional[Dict[str, Any]] = None
) -> ConfigurationValidationResult:
    """
    Convenience function to validate sync configuration.
    
    Args:
        configuration: Configuration to validate
        registry: Optional transformer registry (uses global if not provided)
        canvas_data_sample: Optional sample data for validation
        
    Returns:
        ConfigurationValidationResult
    """
    if registry is None:
        from .base import get_global_registry
        registry = get_global_registry()
    
    validator = ConfigurationValidator(registry)
    return validator.validate_configuration(configuration, canvas_data_sample)