/**
 * Canvas Timestamp Parser Utility
 * 
 * Centralized utility for parsing and handling Canvas API timestamps
 * to standardize datetime parsing across the entire Canvas interface.
 */

export interface ParsedTimestamp {
  original: string | null;
  parsed: Date | null;
  isValid: boolean;
  error?: string;
}

export interface TimestampParseOptions {
  allowNull?: boolean;
  defaultToNow?: boolean;
  timezone?: string;
  strict?: boolean;
}

export class CanvasTimestampParser {
  
  /**
   * Parse a Canvas API timestamp string to Date object
   * 
   * Canvas API returns timestamps in ISO 8601 format:
   * - "2023-10-14T15:30:00Z" (UTC)
   * - "2023-10-14T15:30:00.123Z" (UTC with milliseconds)
   * - "2023-10-14T15:30:00-07:00" (with timezone)
   * - null for unset timestamps
   * 
   * @param timestamp - Canvas timestamp string or null
   * @param options - Parsing options
   * @returns Date object or null if invalid/null
   */
  static parseCanvasTimestamp(
    timestamp: string | null | undefined, 
    options: TimestampParseOptions = {}
  ): Date | null {
    const result = this.parseCanvasTimestampWithDetails(timestamp, options);
    return result.parsed;
  }

  /**
   * Parse Canvas timestamp with detailed result information
   * 
   * @param timestamp - Canvas timestamp string or null
   * @param options - Parsing options
   * @returns Detailed parsing result
   */
  static parseCanvasTimestampWithDetails(
    timestamp: string | null | undefined,
    options: TimestampParseOptions = {}
  ): ParsedTimestamp {
    const { 
      allowNull = true, 
      defaultToNow = false, 
      strict = false 
    } = options;

    // Handle null/undefined cases
    if (timestamp === null || timestamp === undefined || timestamp === '') {
      if (allowNull && !defaultToNow) {
        return {
          original: timestamp as string | null,
          parsed: null,
          isValid: true
        };
      }
      
      if (defaultToNow) {
        return {
          original: timestamp as string | null,
          parsed: new Date(),
          isValid: true
        };
      }
      
      return {
        original: timestamp as string | null,
        parsed: null,
        isValid: false,
        error: 'Timestamp is null/undefined and not allowed'
      };
    }

    // Must be a string at this point
    if (typeof timestamp !== 'string') {
      return {
        original: String(timestamp),
        parsed: null,
        isValid: false,
        error: `Expected string timestamp, got ${typeof timestamp}`
      };
    }

    try {
      // Handle common Canvas timestamp formats
      let normalizedTimestamp = timestamp.trim();
      
      // Canvas often returns "Z" for UTC, but some libraries need "+00:00"
      // Try original format first, then normalized
      let parsedDate: Date;
      
      if (normalizedTimestamp.endsWith('Z')) {
        // ISO format with Z suffix - should work with Date constructor
        parsedDate = new Date(normalizedTimestamp);
      } else if (normalizedTimestamp.includes('+') || normalizedTimestamp.match(/-\d{2}:\d{2}$/)) {
        // Has timezone offset - should work with Date constructor
        parsedDate = new Date(normalizedTimestamp);
      } else if (this.isISODateLike(normalizedTimestamp)) {
        // Looks like ISO date without timezone - assume UTC
        if (!normalizedTimestamp.endsWith('Z') && !normalizedTimestamp.includes('+')) {
          normalizedTimestamp += 'Z';
        }
        parsedDate = new Date(normalizedTimestamp);
      } else {
        // Try parsing as-is
        parsedDate = new Date(normalizedTimestamp);
      }

      // Validate the parsed date
      if (isNaN(parsedDate.getTime())) {
        return {
          original: timestamp,
          parsed: null,
          isValid: false,
          error: `Invalid date: "${timestamp}"`
        };
      }

      // Additional validation for strict mode
      if (strict) {
        // Check if the date is reasonable (not too far in past/future)
        const now = new Date();
        const maxPastYears = 50;
        const maxFutureYears = 10;
        
        const minDate = new Date(now.getFullYear() - maxPastYears, 0, 1);
        const maxDate = new Date(now.getFullYear() + maxFutureYears, 11, 31);
        
        if (parsedDate < minDate || parsedDate > maxDate) {
          return {
            original: timestamp,
            parsed: null,
            isValid: false,
            error: `Date outside reasonable range: "${timestamp}"`
          };
        }
      }

      return {
        original: timestamp,
        parsed: parsedDate,
        isValid: true
      };

    } catch (error) {
      return {
        original: timestamp,
        parsed: null,
        isValid: false,
        error: `Parse error: ${error instanceof Error ? error.message : String(error)}`
      };
    }
  }

  /**
   * Parse multiple Canvas timestamps efficiently
   * 
   * @param timestamps - Array of timestamp strings
   * @param options - Parsing options
   * @returns Array of parsed dates (null for invalid ones)
   */
  static parseMultipleTimestamps(
    timestamps: (string | null)[],
    options: TimestampParseOptions = {}
  ): (Date | null)[] {
    return timestamps.map(ts => this.parseCanvasTimestamp(ts, options));
  }

  /**
   * Convert a Canvas timestamp to a specific timezone
   * 
   * @param timestamp - Canvas timestamp string
   * @param timezone - Target timezone (e.g., 'America/New_York')
   * @returns Formatted date string in target timezone
   */
  static toTimezone(
    timestamp: string | null, 
    timezone: string = 'UTC'
  ): string | null {
    const parsed = this.parseCanvasTimestamp(timestamp);
    if (!parsed) return null;

    try {
      return parsed.toLocaleString('en-US', { 
        timeZone: timezone,
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false
      });
    } catch (error) {
      // Fallback to ISO string if timezone conversion fails
      return parsed.toISOString();
    }
  }

  /**
   * Format Canvas timestamp for display
   * 
   * @param timestamp - Canvas timestamp string
   * @param format - Display format ('short', 'medium', 'long', 'iso')
   * @returns Formatted date string
   */
  static formatForDisplay(
    timestamp: string | null, 
    format: 'short' | 'medium' | 'long' | 'iso' = 'medium'
  ): string {
    const parsed = this.parseCanvasTimestamp(timestamp);
    if (!parsed) return 'Not set';

    switch (format) {
      case 'short':
        return parsed.toLocaleDateString('en-US');
      case 'medium':
        return parsed.toLocaleDateString('en-US', {
          year: 'numeric',
          month: 'short',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit'
        });
      case 'long':
        return parsed.toLocaleDateString('en-US', {
          weekday: 'long',
          year: 'numeric',
          month: 'long',
          day: 'numeric',
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        });
      case 'iso':
        return parsed.toISOString();
      default:
        return parsed.toLocaleDateString('en-US');
    }
  }

  /**
   * Check if timestamp is within a specific time range
   * 
   * @param timestamp - Canvas timestamp to check
   * @param startDate - Range start date
   * @param endDate - Range end date
   * @returns True if timestamp is within range
   */
  static isWithinRange(
    timestamp: string | null,
    startDate: Date,
    endDate: Date
  ): boolean {
    const parsed = this.parseCanvasTimestamp(timestamp);
    if (!parsed) return false;
    
    return parsed >= startDate && parsed <= endDate;
  }

  /**
   * Calculate age of timestamp in various units
   * 
   * @param timestamp - Canvas timestamp string
   * @param unit - Unit for age calculation
   * @returns Age in specified units, or null if invalid timestamp
   */
  static getAge(
    timestamp: string | null,
    unit: 'milliseconds' | 'seconds' | 'minutes' | 'hours' | 'days' = 'hours'
  ): number | null {
    const parsed = this.parseCanvasTimestamp(timestamp);
    if (!parsed) return null;

    const now = new Date();
    const diffMs = now.getTime() - parsed.getTime();

    switch (unit) {
      case 'milliseconds':
        return diffMs;
      case 'seconds':
        return Math.floor(diffMs / 1000);
      case 'minutes':
        return Math.floor(diffMs / (1000 * 60));
      case 'hours':
        return Math.floor(diffMs / (1000 * 60 * 60));
      case 'days':
        return Math.floor(diffMs / (1000 * 60 * 60 * 24));
      default:
        return null;
    }
  }

  /**
   * Convert Date object back to Canvas API format
   * 
   * @param date - Date object to convert
   * @returns Canvas API timestamp string
   */
  static toCanvasFormat(date: Date): string {
    return date.toISOString();
  }

  /**
   * Validate Canvas timestamp format without parsing
   * 
   * @param timestamp - String to validate
   * @returns True if format looks like a Canvas timestamp
   */
  static isValidFormat(timestamp: string | null): boolean {
    if (!timestamp || typeof timestamp !== 'string') {
      return false;
    }

    return this.isISODateLike(timestamp.trim());
  }

  /**
   * Helper: Check if string looks like an ISO date
   */
  private static isISODateLike(str: string): boolean {
    // Basic ISO date pattern matching
    const isoPattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}/;
    return isoPattern.test(str);
  }

  /**
   * Compare two Canvas timestamps
   * 
   * @param timestamp1 - First timestamp
   * @param timestamp2 - Second timestamp
   * @returns -1 if ts1 < ts2, 0 if equal, 1 if ts1 > ts2, null if either invalid
   */
  static compare(
    timestamp1: string | null,
    timestamp2: string | null
  ): number | null {
    const date1 = this.parseCanvasTimestamp(timestamp1);
    const date2 = this.parseCanvasTimestamp(timestamp2);
    
    if (!date1 || !date2) return null;
    
    if (date1 < date2) return -1;
    if (date1 > date2) return 1;
    return 0;
  }

  /**
   * Get current timestamp in Canvas format
   * 
   * @returns Current timestamp as Canvas API string
   */
  static now(): string {
    return new Date().toISOString();
  }
}

/**
 * Convenience functions for common timestamp operations
 */
export const CanvasTimestamps = {
  parse: CanvasTimestampParser.parseCanvasTimestamp,
  parseWithDetails: CanvasTimestampParser.parseCanvasTimestampWithDetails,
  parseMultiple: CanvasTimestampParser.parseMultipleTimestamps,
  format: CanvasTimestampParser.formatForDisplay,
  toTimezone: CanvasTimestampParser.toTimezone,
  getAge: CanvasTimestampParser.getAge,
  isValid: CanvasTimestampParser.isValidFormat,
  compare: CanvasTimestampParser.compare,
  now: CanvasTimestampParser.now,
  toCanvas: CanvasTimestampParser.toCanvasFormat
};