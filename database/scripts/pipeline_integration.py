#!/usr/bin/env python3
"""
Pipeline Integration Script

Bridges TypeScript Canvas data pipeline with Python transformer system.
Utilizes the new modular transformer registry for data transformation.

Usage:
    python pipeline_integration.py <input_file> <config_file> [--bulk]

Where:
    input_file: Path to JSON file containing Canvas staging data
    config_file: Path to JSON file containing sync configuration
    --bulk: Optional flag for bulk processing mode
"""

import json
import sys
import os
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

# Add both database and project root to Python path for imports
database_root = Path(__file__).parent.parent
project_root = database_root.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(database_root))

try:
    from database.operations.transformers import (
        get_global_registry,
        LegacyCanvasDataTransformer,
        TransformationContext,
        EntityType
    )
    try:
        from database.operations.base.exceptions import ValidationError
    except ImportError:
        # Fallback if base exceptions don't exist
        class ValidationError(Exception):
            def __init__(self, message, field_name=None, operation_name=None):
                super().__init__(message)
                self.field_name = field_name
                self.operation_name = operation_name
except ImportError as e:
    print(f"Error importing transformer modules: {e}", file=sys.stderr)
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # Log to stderr to keep stdout clean for JSON output
    ]
)

logger = logging.getLogger(__name__)


class PipelineIntegrationError(Exception):
    """Custom exception for pipeline integration errors"""
    pass


class CanvasPipelineIntegrator:
    """
    Integrates TypeScript Canvas pipeline with Python transformers.
    
    Handles both single course and bulk processing modes using the new
    modular transformer system while maintaining backward compatibility.
    """
    
    def __init__(self, configuration: Optional[Dict[str, Any]] = None):
        """Initialize the integrator with optional configuration."""
        self.configuration = configuration or {}
        self.registry = get_global_registry()
        
        # Initialize legacy transformer for backward compatibility
        self.legacy_transformer = LegacyCanvasDataTransformer(configuration)
        
        logger.info("Pipeline integrator initialized with modular transformer system")
    
    def process_single_course(self, canvas_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process single course data from TypeScript pipeline.
        
        Args:
            canvas_data: Canvas staging data in legacy format
            
        Returns:
            Transformed data ready for database storage
        """
        logger.info("Processing single course data through modular transformers")
        
        try:
            # Validate input data structure
            self._validate_input_data(canvas_data)
            
            # Use the legacy transformer which internally uses the new registry system
            transformed_data = self.legacy_transformer.transform_canvas_staging_data(canvas_data)
            
            # Add metadata about the transformation
            result = {
                'success': True,
                'transformation_method': 'modular_registry',
                'processed_at': datetime.utcnow().isoformat(),
                'configuration': self.configuration,
                **transformed_data
            }
            
            # Log transformation summary
            self._log_transformation_summary(transformed_data, single_course=True)
            
            return result
            
        except ValidationError as e:
            logger.error(f"Validation error during single course processing: {e}")
            return {
                'success': False,
                'error': {
                    'type': 'validation_error',
                    'message': str(e),
                    'operation': getattr(e, 'operation_name', 'unknown')
                }
            }
        except Exception as e:
            logger.error(f"Unexpected error during single course processing: {e}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'type': 'processing_error',
                    'message': str(e)
                }
            }
    
    def process_bulk_courses(self, canvas_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process bulk course data from TypeScript pipeline.
        
        Args:
            canvas_data: Canvas staging data containing multiple courses
            
        Returns:
            Transformed data ready for bulk database storage
        """
        logger.info("Processing bulk course data through modular transformers")
        
        try:
            # Validate bulk input data
            self._validate_bulk_input_data(canvas_data)
            
            # Convert bulk format to registry format and process
            registry_results = self.registry.transform_entities(
                canvas_data=canvas_data,
                configuration=self.configuration
            )
            
            # Convert registry results to expected format
            transformed_data = {}
            total_records = 0
            
            for entity_type, transform_result in registry_results.items():
                if transform_result.success:
                    transformed_data[entity_type] = transform_result.transformed_data
                    total_records += len(transform_result.transformed_data)
                    logger.info(f"Successfully transformed {len(transform_result.transformed_data)} {entity_type} records")
                else:
                    logger.error(f"Failed to transform {entity_type}: {transform_result.errors}")
                    transformed_data[entity_type] = []
            
            # Add metadata about the bulk transformation
            result = {
                'success': True,
                'transformation_method': 'modular_registry_bulk',
                'processed_at': datetime.utcnow().isoformat(),
                'configuration': self.configuration,
                'total_records_processed': total_records,
                **transformed_data
            }
            
            # Log bulk transformation summary
            self._log_transformation_summary(transformed_data, single_course=False)
            
            return result
            
        except Exception as e:
            logger.error(f"Error during bulk course processing: {e}", exc_info=True)
            return {
                'success': False,
                'error': {
                    'type': 'bulk_processing_error',
                    'message': str(e)
                }
            }
    
    def _validate_input_data(self, canvas_data: Dict[str, Any]) -> None:
        """Validate single course input data structure."""
        if not isinstance(canvas_data, dict):
            raise PipelineIntegrationError("Canvas data must be a dictionary")
        
        if not canvas_data.get('success', False):
            error_info = canvas_data.get('error', {})
            raise PipelineIntegrationError(f"Canvas data indicates failure: {error_info.get('message', 'Unknown error')}")
        
        # Check for required fields
        if 'course' not in canvas_data:
            raise PipelineIntegrationError("Missing required 'course' field in canvas data")
        
        course_data = canvas_data['course']
        if not isinstance(course_data, dict) or not course_data.get('id'):
            raise PipelineIntegrationError("Course data missing required 'id' field")
        
        logger.info(f"Validated single course data for course ID: {course_data['id']}")
    
    def _validate_bulk_input_data(self, canvas_data: Dict[str, Any]) -> None:
        """Validate bulk course input data structure."""
        if not isinstance(canvas_data, dict):
            raise PipelineIntegrationError("Bulk canvas data must be a dictionary")
        
        # Check for expected bulk data structure
        expected_keys = ['courses', 'students', 'assignments', 'enrollments']
        present_keys = [key for key in expected_keys if key in canvas_data]
        
        if not present_keys:
            raise PipelineIntegrationError(f"Bulk data missing expected entity keys: {expected_keys}")
        
        # Validate each entity is a list
        for key in present_keys:
            if not isinstance(canvas_data[key], list):
                raise PipelineIntegrationError(f"Bulk data '{key}' must be a list")
        
        total_records = sum(len(canvas_data.get(key, [])) for key in expected_keys)
        logger.info(f"Validated bulk data with {total_records} total records across {len(present_keys)} entity types")
    
    def _log_transformation_summary(self, transformed_data: Dict[str, Any], single_course: bool = True) -> None:
        """Log summary of transformation results."""
        mode = "Single Course" if single_course else "Bulk"
        logger.info(f"{mode} Transformation Summary:")
        
        total_records = 0
        for entity_type, data in transformed_data.items():
            if isinstance(data, list):
                count = len(data)
                total_records += count
                logger.info(f"  {entity_type}: {count} records")
        
        logger.info(f"  Total records transformed: {total_records}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Canvas Pipeline Integration Bridge",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        'input_file',
        help='Path to JSON file containing Canvas staging data'
    )
    
    parser.add_argument(
        'config_file',
        help='Path to JSON file containing sync configuration'
    )
    
    parser.add_argument(
        '--bulk',
        action='store_true',
        help='Process in bulk mode for multiple courses'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    return parser.parse_args()


def load_input_data(input_file: str) -> Dict[str, Any]:
    """Load and parse input JSON data."""
    try:
        input_path = Path(input_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Successfully loaded input data from {input_file}")
        return data
        
    except json.JSONDecodeError as e:
        raise PipelineIntegrationError(f"Invalid JSON in input file: {e}")
    except Exception as e:
        raise PipelineIntegrationError(f"Error reading input file: {e}")


def parse_configuration(config_file: str) -> Dict[str, Any]:
    """Parse configuration from JSON file."""
    try:
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        logger.info(f"Successfully parsed configuration from {config_file}")
        return config
    except json.JSONDecodeError as e:
        raise PipelineIntegrationError(f"Invalid configuration JSON in {config_file}: {e}")
    except Exception as e:
        raise PipelineIntegrationError(f"Error reading configuration file {config_file}: {e}")


def main():
    """Main entry point for the pipeline integration script."""
    try:
        # Parse command line arguments
        args = parse_arguments()
        
        # Configure debug logging if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            logger.debug("Debug logging enabled")
        
        # Load input data and configuration
        canvas_data = load_input_data(args.input_file)
        configuration = parse_configuration(args.config_file)
        
        # Initialize the integrator
        integrator = CanvasPipelineIntegrator(configuration)
        
        # Process data based on mode
        if args.bulk:
            logger.info("Running in bulk processing mode")
            result = integrator.process_bulk_courses(canvas_data)
        else:
            logger.info("Running in single course processing mode")
            result = integrator.process_single_course(canvas_data)
        
        # Output results as JSON to stdout
        print(json.dumps(result, indent=2, default=str))
        
        # Exit with appropriate code
        sys.exit(0 if result.get('success', False) else 1)
        
    except PipelineIntegrationError as e:
        logger.error(f"Pipeline integration error: {e}")
        error_result = {
            'success': False,
            'error': {
                'type': 'pipeline_integration_error',
                'message': str(e)
            }
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(130)  # Standard exit code for SIGINT
        
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        error_result = {
            'success': False,
            'error': {
                'type': 'unexpected_error',
                'message': str(e)
            }
        }
        print(json.dumps(error_result, indent=2))
        sys.exit(1)


if __name__ == '__main__':
    main()