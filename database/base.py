"""
SQLAlchemy Base and common mixins for Canvas Tracker V3 database.

This module provides:
- Declarative Base for all models
- Common field mixins (timestamps, Canvas IDs)
- Base model functionality shared across layers
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, DateTime, String, Boolean, Text, Float
from sqlalchemy.orm import declarative_base, declared_attr
from sqlalchemy.sql import func


# Create the declarative base that all models will inherit from
Base = declarative_base()


class TimestampMixin:
    """
    Mixin to add created_at and updated_at timestamps to any model.
    
    Automatically sets created_at on insert and updated_at on update.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, default=func.now(), nullable=False)
    
    @declared_attr  
    def updated_at(cls):
        return Column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)


class CanvasTimestampMixin:
    """
    Mixin for Canvas models that need to preserve Canvas API timestamps.
    
    Unlike TimestampMixin, this doesn't auto-set timestamps - they should be
    explicitly set from Canvas API data.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, nullable=False)
    
    @declared_attr  
    def updated_at(cls):
        return Column(DateTime, nullable=False)


class CourseTimestampMixin:
    """
    Mixin for Canvas course models that only have created_at timestamp.
    
    Canvas courses API doesn't provide updated_at field, only created_at.
    """
    
    @declared_attr
    def created_at(cls):
        return Column(DateTime, nullable=False)


class SyncTrackingMixin:
    """
    Mixin to track when Canvas data was last synchronized.
    
    Used by Layer 1 (Canvas) models to track sync operations.
    """
    
    @declared_attr
    def last_synced(cls):
        return Column(DateTime, nullable=True)


class CanvasObjectMixin:
    """
    Mixin for models that represent Canvas objects.
    
    Provides common Canvas object patterns like names and IDs.
    """
    
    @declared_attr
    def name(cls):
        return Column(String(255), nullable=False)


class MetadataMixin:
    """
    Mixin for user metadata models.
    
    Provides common user-generated content fields and tag management methods.
    """
    
    @declared_attr
    def notes(cls):
        return Column(Text, nullable=True)
    
    @declared_attr
    def custom_tags(cls):
        return Column(Text, nullable=True)  # JSON string of tags
    
    def add_tag(self, tag):
        """
        Add a tag to the custom_tags JSON field.
        
        Args:
            tag (str): Tag to add
        """
        import json
        
        if not self.custom_tags:
            tags = []
        else:
            tags = json.loads(self.custom_tags)
        
        if tag not in tags:
            tags.append(tag)
            self.custom_tags = json.dumps(tags)
    
    def remove_tag(self, tag):
        """
        Remove a tag from the custom_tags JSON field.
        
        Args:
            tag (str): Tag to remove
        """
        import json
        
        if not self.custom_tags:
            return
            
        tags = json.loads(self.custom_tags)
        if tag in tags:
            tags.remove(tag)
            self.custom_tags = json.dumps(tags)
    
    def get_tags(self):
        """
        Get list of tags from custom_tags JSON field.
        
        Returns:
            list: List of tag strings
        """
        import json
        
        if not self.custom_tags:
            return []
        return json.loads(self.custom_tags)


class BaseModel(Base, TimestampMixin):
    """
    Abstract base model that provides common functionality for all tables.
    
    Includes:
    - Auto-incrementing integer primary key
    - Automatic timestamp tracking
    - Common utility methods
    """
    
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    def __repr__(self):
        """Default string representation showing class and primary key."""
        return f"<{self.__class__.__name__}(id={self.id})>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create model instance from dictionary.
        
        Args:
            data (dict): Dictionary with model field values
            
        Returns:
            BaseModel: New instance of the model
        """
        # Filter out keys that don't correspond to table columns
        valid_keys = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


class CanvasBaseModel(BaseModel, SyncTrackingMixin, CanvasObjectMixin):
    """
    Base model for Layer 1 Canvas data models.
    
    Combines BaseModel functionality with Canvas-specific mixins:
    - Timestamp tracking (created_at, updated_at)
    - Sync tracking (last_synced)
    - Canvas object patterns (name field)
    
    Note: This includes an auto-incrementing id field from BaseModel.
    For Canvas objects that need Canvas IDs as primary keys, use CanvasEntityModel instead.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class, Canvas name, and sync status."""
        sync_status = "synced" if self.last_synced else "never synced"
        return f"<{self.__class__.__name__}(name='{self.name}', {sync_status})>"
    
    def mark_synced(self, sync_time=None):
        """
        Mark this object as synchronized.
        
        Args:
            sync_time (datetime, optional): Sync timestamp. Defaults to now.
        """
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)
        self.last_synced = sync_time
    
    def is_recently_synced(self, threshold_minutes=60):
        """
        Check if object was synced recently.
        
        Args:
            threshold_minutes (int): Minutes threshold for "recent"
            
        Returns:
            bool: True if synced within threshold, False otherwise
        """
        if not self.last_synced:
            return False
        
        now = datetime.now(timezone.utc)
        threshold = now.timestamp() - (threshold_minutes * 60)
        return self.last_synced.timestamp() > threshold


class CanvasEntityModel(Base, CanvasTimestampMixin, SyncTrackingMixin, CanvasObjectMixin):
    """
    Base model for Canvas entities that use Canvas IDs as primary keys.
    
    Unlike CanvasBaseModel, this does NOT include an auto-incrementing id field.
    Canvas entities define their own primary key structure using Canvas IDs.
    
    Uses CanvasTimestampMixin to preserve Canvas API timestamps instead of
    auto-setting database insertion timestamps.
    
    Provides:
    - Timestamp tracking (created_at, updated_at)
    - Sync tracking (last_synced)
    - Canvas object patterns (name field)
    - Utility methods for Canvas-specific operations
    
    Use this for Layer 1 Canvas data models like courses, students, assignments.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class, Canvas name, and sync status."""
        sync_status = "synced" if self.last_synced else "never synced"
        # Try to get the primary key value for display
        pk_columns = [col for col in self.__table__.columns if col.primary_key]
        if pk_columns:
            pk_value = getattr(self, pk_columns[0].name, 'unknown')
            return f"<{self.__class__.__name__}({pk_columns[0].name}={pk_value}, name='{self.name}', {sync_status})>"
        return f"<{self.__class__.__name__}(name='{self.name}', {sync_status})>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create model instance from dictionary.
        
        Args:
            data (dict): Dictionary with model field values
            
        Returns:
            CanvasEntityModel: New instance of the model
        """
        # Filter out keys that don't correspond to table columns
        valid_keys = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
    
    def mark_synced(self, sync_time=None):
        """
        Mark this object as synchronized.
        
        Args:
            sync_time (datetime, optional): Sync timestamp. Defaults to now.
        """
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)
        self.last_synced = sync_time
    
    def is_recently_synced(self, threshold_minutes=60):
        """
        Check if object was synced recently.
        
        Args:
            threshold_minutes (int): Minutes threshold for "recent"
            
        Returns:
            bool: True if synced within threshold, False otherwise
        """
        if not self.last_synced:
            return False
        
        now = datetime.now(timezone.utc)
        threshold = now.timestamp() - (threshold_minutes * 60)
        return self.last_synced.timestamp() > threshold


class CanvasCourseModel(Base, CourseTimestampMixin, SyncTrackingMixin, CanvasObjectMixin):
    """
    Base model for Canvas courses that only have created_at timestamp.
    
    Canvas courses API doesn't provide updated_at field, unlike other Canvas entities.
    
    Provides:
    - Course timestamp tracking (created_at only)
    - Sync tracking (last_synced)
    - Canvas object patterns (name field)
    - Utility methods for Canvas-specific operations
    
    Use this specifically for CanvasCourse model.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class, Canvas name, and sync status."""
        sync_status = "synced" if self.last_synced else "never synced"
        # Try to get the primary key value for display
        pk_columns = [col for col in self.__table__.columns if col.primary_key]
        if pk_columns:
            pk_value = getattr(self, pk_columns[0].name, 'unknown')
            return f"<{self.__class__.__name__}({pk_columns[0].name}={pk_value}, name='{self.name}', {sync_status})>"
        return f"<{self.__class__.__name__}(name='{self.name}', {sync_status})>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create model instance from dictionary.
        
        Args:
            data (dict): Dictionary with model field values
            
        Returns:
            CanvasCourseModel: New instance of the model
        """
        # Filter out keys that don't correspond to table columns
        valid_keys = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
    
    def mark_synced(self, sync_time=None):
        """
        Mark this object as synchronized.
        
        Args:
            sync_time (datetime, optional): Sync timestamp. Defaults to now.
        """
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)
        self.last_synced = sync_time
    
    def is_recently_synced(self, threshold_minutes=60):
        """
        Check if object was synced recently.
        
        Args:
            threshold_minutes (int): Minutes threshold for "recent"
            
        Returns:
            bool: True if synced within threshold, False otherwise
        """
        if not self.last_synced:
            return False
        
        now = datetime.now(timezone.utc)
        threshold = now.timestamp() - (threshold_minutes * 60)
        return self.last_synced.timestamp() > threshold


class CanvasRelationshipModel(Base, CanvasTimestampMixin, SyncTrackingMixin):
    """
    Base model for Canvas relationship models (like enrollments).
    
    Unlike CanvasEntityModel, this does NOT include the name field or other
    Canvas object patterns, since relationships don't have names.
    
    Provides:
    - Canvas timestamp tracking (created_at, updated_at from Canvas API)
    - Sync tracking (last_synced)
    - Utility methods for Canvas-specific operations
    
    Use this for relationship models like CanvasEnrollment.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class and sync status."""
        sync_status = "synced" if self.last_synced else "never synced"
        # Try to get the primary key values for display
        pk_columns = [col for col in self.__table__.columns if col.primary_key]
        if pk_columns:
            pk_values = [f"{col.name}={getattr(self, col.name, 'unknown')}" for col in pk_columns]
            pk_str = ", ".join(pk_values)
            return f"<{self.__class__.__name__}({pk_str}, {sync_status})>"
        return f"<{self.__class__.__name__}({sync_status})>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create model instance from dictionary.
        
        Args:
            data (dict): Dictionary with model field values
            
        Returns:
            CanvasRelationshipModel: New instance of the model
        """
        # Filter out keys that don't correspond to table columns
        valid_keys = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)
    
    def mark_synced(self, sync_time=None):
        """
        Mark this object as synchronized.
        
        Args:
            sync_time (datetime, optional): Sync timestamp. Defaults to now.
        """
        if sync_time is None:
            sync_time = datetime.now(timezone.utc)
        self.last_synced = sync_time
    
    def is_recently_synced(self, threshold_minutes=60):
        """
        Check if object was synced recently.
        
        Args:
            threshold_minutes (int): Minutes threshold for "recent"
            
        Returns:
            bool: True if synced within threshold, False otherwise
        """
        if not self.last_synced:
            return False
        
        now = datetime.now(timezone.utc)
        threshold = now.timestamp() - (threshold_minutes * 60)
        return self.last_synced.timestamp() > threshold


class HistoricalBaseModel(BaseModel):
    """
    Base model for Layer 2 historical data models.
    
    Includes timestamp tracking and recorded_at field for historical snapshots.
    """
    
    __abstract__ = True
    
    @declared_attr
    def recorded_at(cls):
        return Column(DateTime, nullable=False, default=func.now())
    
    def __repr__(self):
        """String representation showing class and recording time."""
        return f"<{self.__class__.__name__}(recorded_at={self.recorded_at})>"


class MetadataBaseModel(BaseModel, MetadataMixin):
    """
    Base model for Layer 3 user metadata models that need auto-incrementing IDs.
    
    Combines BaseModel functionality with user metadata patterns:
    - Auto-incrementing id primary key
    - Timestamp tracking
    - Notes and custom tags fields
    
    Use MetadataEntityModel instead for metadata models that use natural keys as primary keys.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class and whether it has notes."""
        has_notes = "with notes" if self.notes else "no notes"
        return f"<{self.__class__.__name__}({has_notes})>"


class MetadataEntityModel(Base, TimestampMixin, MetadataMixin):
    """
    Base model for Layer 3 metadata entities that use natural keys as primary keys.
    
    Unlike MetadataBaseModel, this does NOT include an auto-incrementing id field.
    Metadata entities define their own primary key structure using Canvas object IDs.
    
    Provides:
    - Timestamp tracking (created_at, updated_at)
    - User metadata patterns (notes, custom_tags, tag methods)
    - Utility methods for metadata operations
    
    Use this for Layer 3 metadata models like StudentMetadata, AssignmentMetadata, CourseMetadata.
    """
    
    __abstract__ = True
    
    def __repr__(self):
        """String representation showing class and whether it has notes."""
        has_notes = "with notes" if self.notes else "no notes"
        # Try to get the primary key value for display
        pk_columns = [col for col in self.__table__.columns if col.primary_key]
        if pk_columns:
            pk_value = getattr(self, pk_columns[0].name, 'unknown')
            return f"<{self.__class__.__name__}({pk_columns[0].name}={pk_value}, {has_notes})>"
        return f"<{self.__class__.__name__}({has_notes})>"
    
    def to_dict(self):
        """
        Convert model instance to dictionary.
        
        Returns:
            dict: Dictionary representation of the model
        """
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data):
        """
        Create model instance from dictionary.
        
        Args:
            data (dict): Dictionary with model field values
            
        Returns:
            MetadataEntityModel: New instance of the model
        """
        # Filter out keys that don't correspond to table columns
        valid_keys = {column.name for column in cls.__table__.columns}
        filtered_data = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered_data)


# Common column types that will be reused across models
class CommonColumns:
    """
    Reusable column definitions for common patterns.
    """
    
    @staticmethod
    def canvas_id(nullable=False):
        """Canvas object ID column."""
        return Column(Integer, nullable=nullable)
    
    @staticmethod
    def percentage_grade():
        """Grade percentage column (0-100)."""
        return Column(Float, nullable=True)
    
    @staticmethod
    def points_column():
        """Points earned/possible column."""
        return Column(Float, nullable=True)
    
    @staticmethod
    def status_column():
        """Generic status string column."""
        return Column(String(50), nullable=True)
    
    @staticmethod
    def url_column():
        """URL string column."""
        return Column(String(500), nullable=True)
    
    @staticmethod
    def json_column():
        """JSON data storage column."""
        return Column(Text, nullable=True)