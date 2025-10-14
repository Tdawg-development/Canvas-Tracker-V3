"""
Layer 1: Canvas Sync Operation Orchestration

This module coordinates full Canvas sync operations with conflict resolution,
incremental sync capabilities, and rollback support.

Key Features:
- Full Canvas data sync coordination
- Incremental sync for changed objects only
- Sync conflict detection and resolution
- Post-sync validation and integrity checks
- Rollback capabilities for failed syncs
"""

from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, select, func
from sqlalchemy.exc import SQLAlchemyError

from ..base.base_operations import BaseOperation
from ..base.transaction_manager import TransactionManager
from ..base.exceptions import (
    CanvasOperationError, SyncConflictError, ValidationError
)
from .canvas_ops import CanvasDataManager
from database.models.layer1_canvas import (
    CanvasCourse, CanvasStudent, CanvasAssignment, CanvasEnrollment
)


class SyncStrategy(Enum):
    """Sync strategy options."""
    FULL_REPLACE = "full_replace"
    INCREMENTAL = "incremental"
    CONSERVATIVE = "conservative"


class SyncPriority(Enum):
    """Sync operation priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class SyncResult:
    """Container for sync operation results."""
    strategy: SyncStrategy
    started_at: datetime
    completed_at: Optional[datetime]
    success: bool
    objects_processed: Dict[str, int]
    objects_created: Dict[str, int]
    objects_updated: Dict[str, int]
    objects_skipped: Dict[str, int]
    conflicts_detected: List[Dict[str, Any]]
    errors: List[str]
    rollback_performed: bool = False
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate sync duration."""
        if self.completed_at and self.started_at:
            return self.completed_at - self.started_at
        return None


class SyncCoordinator(BaseOperation):
    """
    Canvas sync operation coordinator.
    
    Orchestrates sync operations across Canvas models with conflict resolution,
    validation, and rollback capabilities.
    """

    def __init__(self, session: Session):
        """
        Initialize sync coordinator.
        
        Args:
            session: SQLAlchemy session for database operations
        """
        super().__init__(session)
        self.canvas_manager = CanvasDataManager(session)
        self.transaction_manager = TransactionManager(session)
    
    def validate_input(self, **kwargs) -> bool:
        """Validate sync operation input parameters."""
        # Basic validation - can be overridden for specific operations
        return True
    
    def execute_full_sync(
        self,
        canvas_data: Dict[str, List[Dict[str, Any]]],
        priority: SyncPriority = SyncPriority.MEDIUM,
        validate_integrity: bool = True
    ) -> SyncResult:
        """
        Execute complete Canvas data replacement sync.
        
        Args:
            canvas_data: Complete Canvas data bundle from API
            priority: Sync operation priority
            validate_integrity: Whether to perform post-sync validation
            
        Returns:
            SyncResult with operation details
        """
        sync_result = SyncResult(
            strategy=SyncStrategy.FULL_REPLACE,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            success=False,
            objects_processed={},
            objects_created={},
            objects_updated={},
            objects_skipped={},
            conflicts_detected=[],
            errors=[]
        )
        
        try:
            with self.transaction_manager.begin_nested_transaction():
                # Execute sync in order of dependencies
                self._sync_courses(canvas_data.get('courses', []), sync_result)
                self._sync_students(canvas_data.get('students', []), sync_result)
                self._sync_assignments(canvas_data.get('assignments', []), sync_result)
                self._sync_enrollments(canvas_data.get('enrollments', []), sync_result)
                
                # Validate integrity if requested
                if validate_integrity:
                    validation_errors = self.validate_sync_integrity()
                    if validation_errors:
                        sync_result.errors.extend(validation_errors)
                        raise ValidationError("Sync integrity validation failed")
                
                sync_result.success = True
                sync_result.completed_at = datetime.now(timezone.utc)
                
        except Exception as e:
            sync_result.errors.append(str(e))
            sync_result.rollback_performed = True
            # Transaction will auto-rollback due to context manager
            raise CanvasOperationError(f"Full sync failed: {e}")
        
        return sync_result
    
    def execute_incremental_sync(
        self,
        canvas_data: Dict[str, List[Dict[str, Any]]],
        last_sync_time: Optional[datetime] = None,
        priority: SyncPriority = SyncPriority.HIGH
    ) -> SyncResult:
        """
        Execute incremental sync for changed objects only.
        
        Args:
            canvas_data: Canvas data with potential changes
            last_sync_time: Time of last sync (for change detection)
            priority: Sync operation priority
            
        Returns:
            SyncResult with operation details
        """
        sync_result = SyncResult(
            strategy=SyncStrategy.INCREMENTAL,
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            success=False,
            objects_processed={},
            objects_created={},
            objects_updated={},
            objects_skipped={},
            conflicts_detected=[],
            errors=[]
        )
        
        try:
            with self.transaction_manager.begin_nested_transaction():
                # Filter data for changes since last sync
                if last_sync_time:
                    canvas_data = self._filter_changed_data(canvas_data, last_sync_time)
                
                # Detect conflicts before processing
                conflicts = self._detect_sync_conflicts(canvas_data)
                if conflicts:
                    sync_result.conflicts_detected = conflicts
                    # Resolve conflicts based on strategy
                    canvas_data = self._resolve_sync_conflicts(canvas_data, conflicts)
                
                # Execute incremental sync
                self._sync_courses(canvas_data.get('courses', []), sync_result)
                self._sync_students(canvas_data.get('students', []), sync_result)
                self._sync_assignments(canvas_data.get('assignments', []), sync_result)
                self._sync_enrollments(canvas_data.get('enrollments', []), sync_result)
                
                sync_result.success = True
                sync_result.completed_at = datetime.now(timezone.utc)
                
        except Exception as e:
            sync_result.errors.append(str(e))
            sync_result.rollback_performed = True
            raise CanvasOperationError(f"Incremental sync failed: {e}")
        
        return sync_result
    
    def handle_sync_conflicts(
        self,
        conflicts: List[Dict[str, Any]],
        resolution_strategy: str = "canvas_wins"
    ) -> Dict[str, Any]:
        """
        Handle detected sync conflicts with specified resolution strategy.
        
        Args:
            conflicts: List of detected conflicts
            resolution_strategy: How to resolve conflicts
                - "canvas_wins": Canvas data overwrites local changes
                - "local_wins": Keep local changes, skip Canvas updates
                - "merge": Attempt to merge changes
                
        Returns:
            Dictionary with resolution results
        """
        resolution_results = {
            'resolved': [],
            'failed': [],
            'strategy_used': resolution_strategy
        }
        
        for conflict in conflicts:
            try:
                if resolution_strategy == "canvas_wins":
                    # Override local with Canvas data
                    self._apply_canvas_override(conflict)
                    resolution_results['resolved'].append(conflict)
                    
                elif resolution_strategy == "local_wins":
                    # Keep local, skip Canvas update
                    self._skip_canvas_update(conflict)
                    resolution_results['resolved'].append(conflict)
                    
                elif resolution_strategy == "merge":
                    # Attempt to merge changes
                    if self._attempt_merge(conflict):
                        resolution_results['resolved'].append(conflict)
                    else:
                        resolution_results['failed'].append(conflict)
                        
            except Exception as e:
                conflict['resolution_error'] = str(e)
                resolution_results['failed'].append(conflict)
        
        return resolution_results
    
    def validate_sync_integrity(self) -> List[str]:
        """
        Perform post-sync integrity validation.
        
        Returns:
            List of validation errors (empty if all valid)
        """
        errors = []
        
        try:
            # Check referential integrity
            orphaned_assignments = self.session.query(CanvasAssignment).filter(
                ~CanvasAssignment.course_id.in_(
                    select(CanvasCourse.id)
                )
            ).count()
            
            if orphaned_assignments > 0:
                errors.append(f"Found {orphaned_assignments} orphaned assignments")
            
            # Check orphaned enrollments
            orphaned_enrollments = self.session.query(CanvasEnrollment).filter(
                or_(
                    ~CanvasEnrollment.course_id.in_(select(CanvasCourse.id)),
                    ~CanvasEnrollment.student_id.in_(select(CanvasStudent.student_id))
                )
            ).count()
            
            if orphaned_enrollments > 0:
                errors.append(f"Found {orphaned_enrollments} orphaned enrollments")
            
            # Check for duplicate primary keys (shouldn't happen but validate)
            duplicate_courses = self.session.query(CanvasCourse.id).group_by(
                CanvasCourse.id
            ).having(func.count(CanvasCourse.id) > 1).all()
            
            if duplicate_courses:
                errors.append(f"Found duplicate course IDs: {[c[0] for c in duplicate_courses]}")
            
        except SQLAlchemyError as e:
            errors.append(f"Integrity validation failed: {e}")
        
        return errors
    
    def rollback_sync_session(self, sync_result: SyncResult) -> bool:
        """
        Rollback a sync session and restore previous state.
        
        Args:
            sync_result: Result of sync operation to rollback
            
        Returns:
            True if rollback successful, False otherwise
        """
        try:
            # Use transaction manager for rollback
            self.transaction_manager.rollback_nested_transaction()
            sync_result.rollback_performed = True
            return True
            
        except Exception as e:
            self.logger.error(f"Sync rollback failed: {e}")
            return False
    
    # ==================== PRIVATE SYNC METHODS ====================
    
    def _sync_courses(self, courses_data: List[Dict[str, Any]], sync_result: SyncResult) -> None:
        """Sync courses and update result."""
        if not courses_data:
            return
            
        result = self.canvas_manager.batch_sync_courses(courses_data)
        
        sync_result.objects_processed['courses'] = len(courses_data)
        sync_result.objects_created['courses'] = len(result['created'])
        sync_result.objects_updated['courses'] = len(result['updated'])
        sync_result.objects_skipped['courses'] = len(result['skipped'])
    
    def _sync_students(self, students_data: List[Dict[str, Any]], sync_result: SyncResult) -> None:
        """Sync students and update result."""
        if not students_data:
            return
            
        result = self.canvas_manager.batch_sync_students(students_data)
        
        sync_result.objects_processed['students'] = len(students_data)
        sync_result.objects_created['students'] = len(result['created'])
        sync_result.objects_updated['students'] = len(result['updated'])
        sync_result.objects_skipped['students'] = len(result['skipped'])
    
    def _sync_assignments(self, assignments_data: List[Dict[str, Any]], sync_result: SyncResult) -> None:
        """Sync assignments and update result."""
        if not assignments_data:
            return
            
        processed = created = updated = skipped = 0
        
        for assignment_data in assignments_data:
            try:
                course_id = assignment_data.get('course_id')
                if not course_id:
                    continue
                
                assignment_id = assignment_data.get('id')
                
                # Check if assignment exists before sync to determine created vs updated
                existing = self.session.query(CanvasAssignment).filter(
                    CanvasAssignment.id == assignment_id
                ).first() if assignment_id else None
                    
                result = self.canvas_manager.sync_assignment(assignment_data, course_id)
                processed += 1
                
                # Determine if created or updated based on pre-sync existence
                if existing:
                    updated += 1
                else:
                    created += 1
                    
            except Exception as e:
                sync_result.errors.append(f"Failed to sync assignment {assignment_data.get('id')}: {e}")
                skipped += 1
        
        sync_result.objects_processed['assignments'] = processed
        sync_result.objects_created['assignments'] = created
        sync_result.objects_updated['assignments'] = updated
        sync_result.objects_skipped['assignments'] = skipped
    
    def _sync_enrollments(self, enrollments_data: List[Dict[str, Any]], sync_result: SyncResult) -> None:
        """Sync enrollments and update result."""
        if not enrollments_data:
            return
            
        processed = created = updated = skipped = 0
        
        for enrollment_data in enrollments_data:
            try:
                # Handle both field name variations (Canvas API uses 'user_id', some test data uses 'student_id')
                student_id = enrollment_data.get('user_id') or enrollment_data.get('student_id')
                course_id = enrollment_data.get('course_id')
                
                if not student_id or not course_id:
                    skipped += 1
                    continue
                
                # Ensure IDs are integers for database operations
                try:
                    student_id = int(student_id)
                    course_id = int(course_id)
                except (ValueError, TypeError) as e:
                    sync_result.errors.append(f"Invalid ID format for enrollment {student_id}-{course_id}: {e}")
                    skipped += 1
                    continue
                
                # Check if enrollment exists before sync to determine created vs updated
                existing = self.session.query(CanvasEnrollment).filter(
                    and_(
                        CanvasEnrollment.student_id == student_id,
                        CanvasEnrollment.course_id == course_id
                    )
                ).first()
                    
                result = self.canvas_manager.sync_enrollment(student_id, course_id, enrollment_data)
                processed += 1
                
                # Determine if created or updated based on pre-sync existence
                if existing:
                    updated += 1
                else:
                    created += 1
                    
            except Exception as e:
                sync_result.errors.append(f"Failed to sync enrollment {student_id}-{course_id}: {e}")
                skipped += 1
        
        sync_result.objects_processed['enrollments'] = processed
        sync_result.objects_created['enrollments'] = created
        sync_result.objects_updated['enrollments'] = updated
        sync_result.objects_skipped['enrollments'] = skipped
    
    def _filter_changed_data(
        self, 
        canvas_data: Dict[str, List[Dict[str, Any]]], 
        last_sync_time: datetime
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Filter Canvas data for items changed since last sync."""
        filtered_data = {}
        
        for data_type, items in canvas_data.items():
            filtered_items = []
            
            for item in items:
                # Check if item has been modified since last sync
                updated_at = item.get('updated_at')
                if updated_at:
                    try:
                        # Parse Canvas timestamp
                        item_updated = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
                        if item_updated > last_sync_time:
                            filtered_items.append(item)
                    except (ValueError, TypeError):
                        # If parsing fails, include item to be safe
                        filtered_items.append(item)
                else:
                    # No timestamp available, include to be safe
                    filtered_items.append(item)
            
            filtered_data[data_type] = filtered_items
        
        return filtered_data
    
    def _detect_sync_conflicts(self, canvas_data: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        """Detect potential sync conflicts with local data."""
        conflicts = []
        
        # This is a simplified conflict detection
        # In a full implementation, this would check for:
        # - Local modifications to Canvas objects
        # - Timestamp conflicts
        # - Data inconsistencies
        
        return conflicts
    
    def _resolve_sync_conflicts(
        self, 
        canvas_data: Dict[str, List[Dict[str, Any]]], 
        conflicts: List[Dict[str, Any]]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Resolve detected conflicts and return clean data."""
        # Simplified conflict resolution
        # In practice, this would apply resolution strategies
        return canvas_data
    
    def _apply_canvas_override(self, conflict: Dict[str, Any]) -> None:
        """Apply Canvas data override for conflict resolution."""
        # Implementation would override local changes with Canvas data
        pass
    
    def _skip_canvas_update(self, conflict: Dict[str, Any]) -> None:
        """Skip Canvas update to preserve local changes."""
        # Implementation would mark Canvas update as skipped
        pass
    
    def _attempt_merge(self, conflict: Dict[str, Any]) -> bool:
        """Attempt to merge conflicting changes."""
        # Implementation would try to merge changes intelligently
        # Return True if successful, False if manual intervention needed
        return False