"""
Canvas-Database Integration Bridge

This module provides the main integration bridge between the TypeScript Canvas interface
and Python database operations. It orchestrates the complete sync process by:

1. Executing TypeScript CanvasDataConstructor via subprocess
2. Transforming TypeScript data formats to Python database models
3. Coordinating database sync operations across all layers

Key Components:
- CanvasDataBridge: Main orchestrator for Canvas-Database integration
- Integration with existing CanvasDataManager and SyncCoordinator
- Error handling and transaction management
- Comprehensive logging and monitoring
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timezone
from dataclasses import dataclass

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .base.base_operations import BaseOperation
from .base.transaction_manager import TransactionManager
from .base.exceptions import (
    CanvasOperationError, ValidationError, TransactionError
)
from .layer1.canvas_ops import CanvasDataManager
from .layer1.sync_coordinator import SyncCoordinator, SyncResult, SyncPriority
from .typescript_interface import TypeScriptExecutor, TypeScriptExecutionError
from .transformers import get_global_registry


@dataclass
class CanvasBridgeResult:
    """Container for Canvas bridge operation results."""
    success: bool
    course_id: Optional[int]
    typescript_execution_time: Optional[float]
    data_transformation_time: Optional[float]
    database_sync_time: Optional[float]
    total_time: Optional[float]
    objects_synced: Dict[str, int]
    sync_result: Optional[SyncResult]
    errors: List[str]
    warnings: List[str]
    
    @property
    def ready_for_frontend(self) -> bool:
        """Check if result indicates system is ready for frontend development."""
        return (
            self.success and 
            self.sync_result and 
            self.sync_result.success and
            self.objects_synced.get('courses', 0) > 0
        )


class CanvasDataBridge(BaseOperation):
    """
    Main integration bridge between TypeScript Canvas interface and Python database operations.
    
    This class orchestrates the complete Canvas sync process by coordinating TypeScript
    execution, data transformation, and database operations. It provides the critical
    integration layer that connects the existing Canvas interface with database operations.
    
    Features:
    - TypeScript subprocess execution
    - Data format transformation between TypeScript and Python
    - Transaction-safe database operations
    - Comprehensive error handling and rollback
    - Performance monitoring and logging
    """

    def __init__(
        self, 
        canvas_interface_path: str, 
        session: Session,
        auto_detect_path: bool = True,
        sync_configuration: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Canvas data bridge.
        
        Args:
            canvas_interface_path: Path to canvas-interface directory
            session: SQLAlchemy session for database operations
            auto_detect_path: Whether to auto-detect canvas-interface path if not found
        """
        super().__init__(session)
        
        # Store canvas interface path
        self.canvas_path = Path(canvas_interface_path)
        if auto_detect_path and not self.canvas_path.exists():
            self.canvas_path = self._detect_canvas_interface_path()
        
        # Store sync configuration
        self.sync_configuration = sync_configuration
        
        # Initialize core components
        self.typescript_executor = TypeScriptExecutor(str(self.canvas_path))
        self.transformer_registry = get_global_registry()
        self.canvas_manager = CanvasDataManager(session)
        self.sync_coordinator = SyncCoordinator(session)
        self.transaction_manager = TransactionManager(session)
        
        # Setup logging
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.logger.info(f"Canvas Data Bridge initialized with path: {self.canvas_path}")

    def validate_input(self, **kwargs) -> bool:
        """Validate Canvas bridge operation input parameters."""
        course_id = kwargs.get('course_id')
        if not course_id or not isinstance(course_id, int):
            raise ValidationError(
                "Canvas bridge requires valid course_id parameter",
                field_name="course_id",
                invalid_value=course_id,
                operation_name="canvas_bridge_validation"
            )
        return True

    async def initialize_canvas_course_sync(
        self, 
        course_id: int,
        priority: SyncPriority = SyncPriority.HIGH,
        validate_environment: bool = True
    ) -> CanvasBridgeResult:
        """
        Initialize a Canvas course in the database with complete sync process.
        
        This is the main method that orchestrates the entire Canvas-to-database sync:
        1. Validates environment and prerequisites
        2. Executes TypeScript CanvasDataConstructor
        3. Transforms TypeScript data to database format
        4. Executes database sync operations
        5. Validates final state
        
        Args:
            course_id: Canvas course ID to initialize
            priority: Sync operation priority level
            validate_environment: Whether to validate prerequisites before starting
            
        Returns:
            CanvasBridgeResult with complete operation details
            
        Raises:
            CanvasOperationError: If any step of the sync process fails
            ValidationError: If input validation fails
        """
        # Validate input
        self.validate_input(course_id=course_id)
        
        # Initialize result tracking
        bridge_result = CanvasBridgeResult(
            success=False,
            course_id=course_id,
            typescript_execution_time=None,
            data_transformation_time=None,
            database_sync_time=None,
            total_time=None,
            objects_synced={},
            sync_result=None,
            errors=[],
            warnings=[]
        )
        
        start_time = datetime.now()
        self.logger.info(f"Starting Canvas course sync for course {course_id}")
        
        try:
            # Step 1: Environment validation
            if validate_environment:
                self.logger.info("Validating Canvas bridge environment...")
                env_validation = self.validate_bridge_environment()
                if not env_validation['valid']:
                    bridge_result.errors.extend(env_validation['errors'])
                    raise CanvasOperationError(
                        f"Environment validation failed: {'; '.join(env_validation['errors'])}"
                    )
                if env_validation['warnings']:
                    bridge_result.warnings.extend(env_validation['warnings'])

            # Step 2: Execute TypeScript data constructor
            self.logger.info(f"Executing TypeScript CanvasDataConstructor for course {course_id}...")
            ts_start = datetime.now()
            
            canvas_data = await self.typescript_executor.execute_course_data_constructor(course_id)
            
            ts_end = datetime.now()
            bridge_result.typescript_execution_time = (ts_end - ts_start).total_seconds()
            self.logger.info(f"TypeScript execution completed in {bridge_result.typescript_execution_time:.2f}s")

            # Step 3: Transform data formats with configuration
            self.logger.info("Transforming TypeScript data to database format...")
            if self.sync_configuration:
                self.logger.info(f"Using sync configuration: {list(self.sync_configuration.get('entities', {}).keys())}")
            transform_start = datetime.now()
            
            # Convert TypeScript canvas data to registry format
            registry_format_data = self._convert_to_registry_format(canvas_data)
            
            # Use new transformer registry
            transformation_results = self.transformer_registry.transform_entities(
                canvas_data=registry_format_data,
                configuration=self.sync_configuration,
                course_id=course_id
            )
            
            # Convert results to legacy format for sync coordinator compatibility
            db_data = self._convert_transformation_results(transformation_results)
            
            transform_end = datetime.now()
            bridge_result.data_transformation_time = (transform_end - transform_start).total_seconds()
            self.logger.info(f"Data transformation completed in {bridge_result.data_transformation_time:.2f}s")
            
            # Step 4: Execute database sync
            self.logger.info("Executing database sync operations...")
            db_start = datetime.now()
            
            sync_result = await self._execute_database_sync(db_data, priority, course_id)
            bridge_result.sync_result = sync_result
            
            db_end = datetime.now()
            bridge_result.database_sync_time = (db_end - db_start).total_seconds()
            self.logger.info(f"Database sync completed in {bridge_result.database_sync_time:.2f}s")

            # Step 5: Calculate totals and validate success
            end_time = datetime.now()
            bridge_result.total_time = (end_time - start_time).total_seconds()
            bridge_result.objects_synced = {
                'courses': sync_result.objects_created.get('courses', 0) + sync_result.objects_updated.get('courses', 0),
                'students': sync_result.objects_created.get('students', 0) + sync_result.objects_updated.get('students', 0),
                'assignments': sync_result.objects_created.get('assignments', 0) + sync_result.objects_updated.get('assignments', 0),
                'enrollments': sync_result.objects_created.get('enrollments', 0) + sync_result.objects_updated.get('enrollments', 0)
            }
            
            # Check if sync was successful
            if sync_result.success and not sync_result.errors:
                bridge_result.success = True
                self.logger.info(f"Canvas course sync completed successfully for course {course_id}")
                self.logger.info(f"Total processing time: {bridge_result.total_time:.2f}s")
                self.logger.info(f"Objects synced: {bridge_result.objects_synced}")
            else:
                bridge_result.errors.extend(sync_result.errors)
                raise CanvasOperationError(f"Database sync failed: {'; '.join(sync_result.errors)}")

        except TypeScriptExecutionError as e:
            error_msg = f"TypeScript execution failed: {str(e)}"
            bridge_result.errors.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            raise CanvasOperationError(error_msg)
            
        except Exception as e:
            error_msg = f"Canvas bridge sync failed: {str(e)}"
            bridge_result.errors.append(error_msg)
            self.logger.error(error_msg, exc_info=True)
            
            # Ensure rollback if we're in a transaction
            if hasattr(self.sync_coordinator, 'rollback_sync_session'):
                try:
                    self.sync_coordinator.rollback_sync_session(bridge_result.sync_result)
                except Exception as rollback_error:
                    self.logger.error(f"Rollback failed: {rollback_error}")
            
            raise CanvasOperationError(error_msg)
            
        return bridge_result

    def validate_bridge_environment(self) -> Dict[str, Any]:
        """
        Validate Canvas bridge environment prerequisites.
        
        Returns:
            Dictionary with validation results:
            - valid: bool - Whether environment is valid
            - errors: List[str] - Critical errors that prevent operation
            - warnings: List[str] - Non-critical issues that should be noted
        """
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        try:
            # Check canvas-interface directory structure
            if not self.canvas_path.exists():
                validation_result['errors'].append(f"Canvas interface path not found: {self.canvas_path}")
                validation_result['valid'] = False
                
            staging_dir = self.canvas_path / "staging"
            if not staging_dir.exists():
                validation_result['errors'].append("Canvas interface staging directory not found")
                validation_result['valid'] = False
                
            constructor_file = staging_dir / "canvas-data-constructor.ts"
            if not constructor_file.exists():
                validation_result['errors'].append("canvas-data-constructor.ts not found")
                validation_result['valid'] = False
                
            # Check .env file
            env_file = self.canvas_path / ".env"
            if not env_file.exists():
                validation_result['warnings'].append("Canvas .env file not found - API credentials may not be configured")
                
            # Validate TypeScript execution environment
            try:
                ts_validation = self.typescript_executor.validate_execution_environment()
                if not ts_validation['valid']:
                    validation_result['errors'].extend(ts_validation['errors'])
                    validation_result['valid'] = False
                if ts_validation['warnings']:
                    validation_result['warnings'].extend(ts_validation['warnings'])
            except Exception as e:
                validation_result['errors'].append(f"TypeScript environment validation failed: {str(e)}")
                validation_result['valid'] = False
                
        except Exception as e:
            validation_result['errors'].append(f"Environment validation error: {str(e)}")
            validation_result['valid'] = False
            
        return validation_result

    async def _execute_database_sync(
        self, 
        db_data: Dict[str, List[Dict[str, Any]]], 
        priority: SyncPriority,
        course_id: int
    ) -> SyncResult:
        """
        Execute database sync operations within transaction.
        
        Args:
            db_data: Transformed database data
            priority: Sync priority level
            course_id: Course ID for logging context
            
        Returns:
            SyncResult with sync operation details
        """
        try:
            # Execute full sync with transaction management
            sync_result = self.sync_coordinator.execute_full_sync(
                canvas_data=db_data,
                priority=priority,
                validate_integrity=True
            )
            
            # Log sync statistics
            self.logger.info(f"Sync completed for course {course_id}:")
            self.logger.info(f"  - Courses: {sync_result.objects_created.get('courses', 0)} created, {sync_result.objects_updated.get('courses', 0)} updated")
            self.logger.info(f"  - Students: {sync_result.objects_created.get('students', 0)} created, {sync_result.objects_updated.get('students', 0)} updated")
            self.logger.info(f"  - Assignments: {sync_result.objects_created.get('assignments', 0)} created, {sync_result.objects_updated.get('assignments', 0)} updated")
            self.logger.info(f"  - Enrollments: {sync_result.objects_created.get('enrollments', 0)} created, {sync_result.objects_updated.get('enrollments', 0)} updated")
            
            return sync_result
            
        except Exception as e:
            self.logger.error(f"Database sync failed for course {course_id}: {str(e)}")
            raise

    def _detect_canvas_interface_path(self) -> Path:
        """
        Auto-detect canvas-interface path if not found.
        
        Returns:
            Path to canvas-interface directory
            
        Raises:
            CanvasOperationError: If path cannot be detected
        """
        # Common locations to check
        potential_paths = [
            Path.cwd() / "canvas-interface",
            Path.cwd().parent / "canvas-interface",
            Path.cwd() / ".." / "canvas-interface",
            Path(__file__).parent.parent.parent / "canvas-interface"
        ]
        
        for path in potential_paths:
            if path.exists() and (path / "staging" / "canvas-data-constructor.ts").exists():
                self.logger.info(f"Auto-detected canvas-interface path: {path}")
                return path
                
        raise CanvasOperationError(
            "Could not auto-detect canvas-interface path. "
            f"Checked locations: {[str(p) for p in potential_paths]}"
        )

    def get_bridge_status(self) -> Dict[str, Any]:
        """
        Get current status of Canvas bridge components.
        
        Returns:
            Dictionary with component status information
        """
        try:
            env_validation = self.validate_bridge_environment()
            ts_validation = self.typescript_executor.validate_execution_environment()
            
            return {
                'canvas_interface_path': str(self.canvas_path),
                'path_exists': self.canvas_path.exists(),
                'environment_valid': env_validation['valid'],
                'environment_errors': env_validation['errors'],
                'environment_warnings': env_validation['warnings'],
                'typescript_environment': ts_validation,
                'components': {
                    'typescript_executor': type(self.typescript_executor).__name__,
                    'transformer_registry': type(self.transformer_registry).__name__,
                    'canvas_manager': type(self.canvas_manager).__name__,
                    'sync_coordinator': type(self.sync_coordinator).__name__
                }
            }
        except Exception as e:
            return {
                'error': f"Failed to get bridge status: {str(e)}",
                'canvas_interface_path': str(self.canvas_path),
                'path_exists': self.canvas_path.exists() if hasattr(self, 'canvas_path') else False
            }
    
    def _convert_to_registry_format(self, canvas_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert TypeScript canvas data to transformer registry format."""
        registry_format = {}
        
        # Convert singular 'course' to plural 'courses' list
        if 'course' in canvas_data and canvas_data['course']:
            registry_format['courses'] = [canvas_data['course']]
        
        # Copy other entities as-is (they're already plural)
        for entity_key in ['students', 'modules', 'enrollments']:
            if entity_key in canvas_data:
                registry_format[entity_key] = canvas_data[entity_key]
        
        # Extract assignments from modules
        if 'modules' in canvas_data:
            assignments = []
            for module_data in canvas_data['modules']:
                module_id = module_data.get('id')
                # Handle both 'assignments' and 'items' keys (Canvas API uses 'items')
                items = module_data.get('assignments', [])
                if not items:
                    items = module_data.get('items', [])
                
                for item in items:
                    if item.get('type') in ['Assignment', 'Quiz']:
                        # Add module context to assignment
                        item_with_context = item.copy()
                        item_with_context['course_id'] = canvas_data.get('course', {}).get('id')
                        item_with_context['module_id'] = item.get('module_id') or module_id
                        assignments.append(item_with_context)
            
            registry_format['assignments'] = assignments
        
        # Extract enrollments from students if needed
        if 'students' in canvas_data and 'enrollments' not in registry_format:
            enrollments = []
            for student_data in canvas_data['students']:
                # Add course context to student for enrollment creation
                enrollment_data = student_data.copy()
                enrollment_data['course_id'] = canvas_data.get('course', {}).get('id')
                enrollments.append(enrollment_data)
            registry_format['enrollments'] = enrollments
        
        return registry_format
    
    def _convert_transformation_results(self, transformation_results: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Convert new transformer results to legacy format for sync coordinator."""
        legacy_result = {}
        
        for entity_type, result in transformation_results.items():
            if result.success:
                legacy_result[entity_type] = result.transformed_data
            else:
                # Log errors but don't fail entirely (legacy behavior)
                self.logger.error(f"Failed to transform {entity_type}: {result.errors}")
                legacy_result[entity_type] = []
        
        # Ensure all expected entity types are present (legacy compatibility)
        for entity_type in ['courses', 'students', 'assignments', 'enrollments']:
            if entity_type not in legacy_result:
                legacy_result[entity_type] = []
        
        return legacy_result


# Convenience function for quick course initialization
async def initialize_canvas_course(
    course_id: int,
    canvas_interface_path: Optional[str] = None,
    session: Optional[Session] = None,
    priority: SyncPriority = SyncPriority.HIGH,
    sync_configuration: Optional[Dict[str, Any]] = None
) -> CanvasBridgeResult:
    """
    Convenience function to initialize a Canvas course with default settings.
    
    Args:
        course_id: Canvas course ID to initialize
        canvas_interface_path: Optional path to canvas-interface directory
        session: Optional database session
        priority: Sync operation priority
        
    Returns:
        CanvasBridgeResult with operation details
    """
    # Auto-detect canvas interface path if not provided
    if not canvas_interface_path:
        # Default to project root + canvas-interface
        canvas_interface_path = str(Path(__file__).parent.parent.parent / "canvas-interface")
    
    # Create session if not provided
    if not session:
        from database.session import get_session
        session = get_session()
        
    # Initialize and execute bridge
    bridge = CanvasDataBridge(canvas_interface_path, session, sync_configuration=sync_configuration)
    return await bridge.initialize_canvas_course_sync(course_id, priority)
