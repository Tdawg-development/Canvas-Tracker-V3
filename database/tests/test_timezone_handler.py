"""
Unit tests for Canvas timezone handler utilities.

Tests timezone-aware datetime handling, Canvas format parsing,
and database compatibility for datetime operations.
"""

import pytest
from datetime import datetime, timezone, timedelta

from database.utils.timezone_handler import (
    CanvasTimezoneHandler, 
    canvas_datetime,
    utc_datetime
)


class TestCanvasTimezoneHandler:
    """Test CanvasTimezoneHandler functionality."""
    
    def test_parse_canvas_datetime(self):
        """Test parsing Canvas datetime format."""
        canvas_dt_str = "2025-07-28T16:31:18Z"
        result = CanvasTimezoneHandler.parse_canvas_datetime(canvas_dt_str)
        
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 28
        assert result.hour == 16
        assert result.minute == 31
        assert result.second == 18
        assert result.tzinfo == timezone.utc
    
    def test_to_canvas_format(self):
        """Test converting datetime to Canvas format."""
        dt = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
        result = CanvasTimezoneHandler.to_canvas_format(dt)
        
        assert result == "2025-07-28T16:31:18Z"
    
    def test_to_canvas_format_with_naive_datetime(self):
        """Test converting naive datetime to Canvas format (assumes UTC)."""
        dt = datetime(2025, 7, 28, 16, 31, 18)  # naive
        result = CanvasTimezoneHandler.to_canvas_format(dt)
        
        assert result == "2025-07-28T16:31:18Z"
    
    def test_roundtrip_canvas_format(self):
        """Test parsing Canvas format and converting back."""
        original = "2025-07-28T16:31:18Z"
        parsed = CanvasTimezoneHandler.parse_canvas_datetime(original)
        back_to_string = CanvasTimezoneHandler.to_canvas_format(parsed)
        
        assert back_to_string == original
    
    def test_to_utc_with_timezone_aware(self):
        """Test converting timezone-aware datetime to UTC."""
        # Create datetime in different timezone (EST = UTC-5)
        est = timezone(timedelta(hours=-5))
        dt = datetime(2025, 7, 28, 11, 31, 18, tzinfo=est)  # 11 AM EST
        
        result = CanvasTimezoneHandler.to_utc(dt)
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 16  # 11 AM EST = 4 PM UTC
    
    def test_to_utc_with_naive_datetime(self):
        """Test converting naive datetime to UTC (assumes already UTC)."""
        dt = datetime(2025, 7, 28, 16, 31, 18)  # naive
        result = CanvasTimezoneHandler.to_utc(dt)
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 16  # Same hour, just add UTC timezone
    
    def test_to_utc_with_none(self):
        """Test handling None input."""
        result = CanvasTimezoneHandler.to_utc(None)
        assert result is None
    
    def test_from_database_with_naive_datetime(self):
        """Test converting database datetime to timezone-aware (typical SQLite case)."""
        dt = datetime(2025, 7, 28, 16, 31, 18)  # naive from SQLite
        result = CanvasTimezoneHandler.from_database(dt)
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 16
    
    def test_from_database_with_timezone_aware(self):
        """Test handling timezone-aware datetime from database."""
        dt = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
        result = CanvasTimezoneHandler.from_database(dt)
        
        assert result.tzinfo == timezone.utc
        assert result.hour == 16
    
    def test_from_database_with_none(self):
        """Test handling None from database (nullable columns)."""
        result = CanvasTimezoneHandler.from_database(None)
        assert result is None
    
    def test_now_utc(self):
        """Test getting current UTC datetime."""
        result = CanvasTimezoneHandler.now_utc()
        
        assert result.tzinfo == timezone.utc
        # Verify it's recent (within 1 second)
        now = datetime.now(timezone.utc)
        time_diff = abs((now - result).total_seconds())
        assert time_diff < 1
    
    def test_compare_datetimes_both_none(self):
        """Test comparing two None datetimes."""
        assert CanvasTimezoneHandler.compare_datetimes(None, None) is True
    
    def test_compare_datetimes_one_none(self):
        """Test comparing None with datetime."""
        dt = datetime.now(timezone.utc)
        assert CanvasTimezoneHandler.compare_datetimes(None, dt) is False
        assert CanvasTimezoneHandler.compare_datetimes(dt, None) is False
    
    def test_compare_datetimes_same_moment(self):
        """Test comparing datetimes representing same moment."""
        # Same moment in different timezones
        utc_dt = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
        est = timezone(timedelta(hours=-5))
        est_dt = datetime(2025, 7, 28, 11, 31, 18, tzinfo=est)  # Same moment
        
        assert CanvasTimezoneHandler.compare_datetimes(utc_dt, est_dt) is True
    
    def test_compare_datetimes_naive_vs_aware(self):
        """Test comparing naive datetime with timezone-aware (assumes naive is UTC)."""
        naive_dt = datetime(2025, 7, 28, 16, 31, 18)  # naive
        aware_dt = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
        
        assert CanvasTimezoneHandler.compare_datetimes(naive_dt, aware_dt) is True
    
    def test_compare_datetimes_different_moments(self):
        """Test comparing datetimes representing different moments."""
        dt1 = datetime(2025, 7, 28, 16, 31, 18, tzinfo=timezone.utc)
        dt2 = datetime(2025, 7, 28, 16, 31, 19, tzinfo=timezone.utc)  # 1 second later
        
        assert CanvasTimezoneHandler.compare_datetimes(dt1, dt2) is False
    
    def test_compare_datetimes_ignores_microseconds(self):
        """Test that comparison ignores microseconds (for database compatibility)."""
        dt1 = datetime(2025, 7, 28, 16, 31, 18, 123456, tzinfo=timezone.utc)
        dt2 = datetime(2025, 7, 28, 16, 31, 18, 654321, tzinfo=timezone.utc)
        
        assert CanvasTimezoneHandler.compare_datetimes(dt1, dt2) is True


class TestHelperFunctions:
    """Test helper functions."""
    
    def test_canvas_datetime_helper(self):
        """Test canvas_datetime helper function."""
        result = canvas_datetime("2025-07-28T16:31:18Z")
        
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 28
        assert result.hour == 16
        assert result.minute == 31
        assert result.second == 18
        assert result.tzinfo == timezone.utc
    
    def test_utc_datetime_helper(self):
        """Test utc_datetime helper function."""
        result = utc_datetime(2025, 7, 28, 16, 31, 18)
        
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 28
        assert result.hour == 16
        assert result.minute == 31
        assert result.second == 18
        assert result.tzinfo == timezone.utc
    
    def test_utc_datetime_helper_defaults(self):
        """Test utc_datetime helper with default time components."""
        result = utc_datetime(2025, 7, 28)
        
        assert result.year == 2025
        assert result.month == 7
        assert result.day == 28
        assert result.hour == 0
        assert result.minute == 0
        assert result.second == 0
        assert result.tzinfo == timezone.utc


class TestCanvasIntegration:
    """Test integration with Canvas datetime scenarios."""
    
    def test_typical_canvas_api_response(self):
        """Test handling typical Canvas API datetime responses."""
        canvas_datetimes = [
            "2025-01-15T08:00:00Z",  # Course start
            "2025-05-15T17:00:00Z",  # Course end
            "2025-02-01T12:30:00Z",  # Assignment due
            "2024-12-20T09:15:30Z",  # Enrollment date
        ]
        
        for canvas_dt_str in canvas_datetimes:
            parsed = canvas_datetime(canvas_dt_str)
            back_to_canvas = CanvasTimezoneHandler.to_canvas_format(parsed)
            
            assert parsed.tzinfo == timezone.utc
            assert back_to_canvas == canvas_dt_str
    
    def test_database_storage_simulation(self):
        """Test simulation of storing/retrieving from database."""
        # Original Canvas datetime
        original_canvas = "2025-07-28T16:31:18Z"
        parsed = canvas_datetime(original_canvas)
        
        # Simulate database storage (SQLite strips timezone)
        stored_in_db = parsed.replace(tzinfo=None)  # What SQLite would store
        
        # Simulate retrieval from database
        retrieved = CanvasTimezoneHandler.from_database(stored_in_db)
        
        # Should be equivalent to original
        assert CanvasTimezoneHandler.compare_datetimes(parsed, retrieved) is True
        assert retrieved.tzinfo == timezone.utc