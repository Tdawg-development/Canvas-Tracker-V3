"""
Timezone handling utilities for Canvas Tracker V3.

Provides consistent timezone-aware datetime handling across the application,
specifically designed to work with Canvas API datetime formats (ISO 8601 with Z suffix).
Ensures proper storage and retrieval of datetime values from the database.
"""

from datetime import datetime, timezone
from typing import Optional


class CanvasTimezoneHandler:
    """Handle Canvas-compatible timezone-aware datetime operations for database storage."""
    
    # Canvas datetime format: "2025-07-28T16:31:18Z"
    CANVAS_DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
    
    @staticmethod
    def parse_canvas_datetime(canvas_datetime: str) -> datetime:
        """
        Parse Canvas API datetime string to timezone-aware datetime.
        
        Args:
            canvas_datetime: Canvas datetime string (e.g., "2025-07-28T16:31:18Z")
            
        Returns:
            Timezone-aware UTC datetime object
            
        Example:
            >>> dt = CanvasTimezoneHandler.parse_canvas_datetime("2025-07-28T16:31:18Z")
            >>> dt.isoformat()
            '2025-07-28T16:31:18+00:00'
        """
        # Parse the Canvas format and add UTC timezone
        naive_dt = datetime.strptime(canvas_datetime, CanvasTimezoneHandler.CANVAS_DATETIME_FORMAT)
        return naive_dt.replace(tzinfo=timezone.utc)
    
    @staticmethod
    def to_canvas_format(dt: datetime) -> str:
        """
        Convert datetime to Canvas API format string.
        
        Args:
            dt: Timezone-aware datetime
            
        Returns:
            Canvas-formatted datetime string (e.g., "2025-07-28T16:31:18Z")
            
        Example:
            >>> dt = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
            >>> CanvasTimezoneHandler.to_canvas_format(dt)
            '2025-07-28T16:31:18Z'
        """
        # Convert to UTC if not already, then format for Canvas
        utc_dt = dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        return utc_dt.strftime(CanvasTimezoneHandler.CANVAS_DATETIME_FORMAT)
    
    @staticmethod
    def to_utc(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert datetime to UTC, handling both timezone-aware and naive datetimes.
        
        Args:
            dt: Input datetime (can be timezone-aware or naive)
            
        Returns:
            Datetime converted to UTC, or None if input is None
            
        Notes:
            - If datetime is already timezone-aware, converts to UTC
            - If datetime is naive, assumes it's already in UTC
            - Returns None for None input (handles nullable columns)
        """
        if dt is None:
            return None
            
        if dt.tzinfo is None:
            # Naive datetime - assume it's already UTC and add timezone info
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Timezone-aware datetime - convert to UTC
            return dt.astimezone(timezone.utc)
    
    @staticmethod
    def from_database(dt: Optional[datetime]) -> Optional[datetime]:
        """
        Convert datetime from database storage to timezone-aware UTC datetime.
        
        Args:
            dt: Datetime from database (typically timezone-naive in SQLite)
            
        Returns:
            Timezone-aware UTC datetime, or None if input is None
            
        Notes:
            - SQLite strips timezone info, so we re-add UTC timezone
            - Other databases may behave differently but this ensures consistency
        """
        if dt is None:
            return None
            
        if dt.tzinfo is None:
            # Database returned naive datetime - assume it's UTC
            return dt.replace(tzinfo=timezone.utc)
        else:
            # Database returned timezone-aware datetime - ensure it's UTC
            return dt.astimezone(timezone.utc)
    
    @staticmethod
    def now_utc() -> datetime:
        """
        Get current UTC datetime with timezone info.
        
        Returns:
            Current datetime in UTC timezone
        """
        return datetime.now(timezone.utc)
    
    @staticmethod
    def compare_datetimes(dt1: Optional[datetime], dt2: Optional[datetime]) -> bool:
        """
        Compare two datetimes, handling timezone differences properly.
        
        Args:
            dt1: First datetime for comparison
            dt2: Second datetime for comparison
            
        Returns:
            True if datetimes represent the same moment in time
            
        Notes:
            - Handles timezone-aware vs timezone-naive comparisons
            - Converts both to UTC for accurate comparison
            - Ignores microseconds for database compatibility
        """
        if dt1 is None and dt2 is None:
            return True
        if dt1 is None or dt2 is None:
            return False
            
        # Convert both to UTC for comparison
        utc_dt1 = CanvasTimezoneHandler.to_utc(dt1)
        utc_dt2 = CanvasTimezoneHandler.to_utc(dt2)
        
        # Compare the UTC versions (ignoring microseconds for database compatibility)
        return (utc_dt1.replace(microsecond=0) == utc_dt2.replace(microsecond=0))


def canvas_datetime(datetime_string: str) -> datetime:
    """
    Helper function to create timezone-aware datetime from Canvas format string.
    
    Args:
        datetime_string: Canvas datetime string (e.g., "2025-07-28T16:31:18Z")
        
    Returns:
        Timezone-aware UTC datetime
        
    Example:
        >>> dt = canvas_datetime("2025-07-28T16:31:18Z")
        >>> dt.tzinfo
        datetime.timezone.utc
    """
    return CanvasTimezoneHandler.parse_canvas_datetime(datetime_string)


def utc_datetime(year: int, month: int, day: int, 
                hour: int = 0, minute: int = 0, second: int = 0) -> datetime:
    """
    Helper function to create UTC timezone-aware datetime objects.
    
    Args:
        year, month, day, hour, minute, second: Date/time components
        
    Returns:
        Timezone-aware UTC datetime
    """
    return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)