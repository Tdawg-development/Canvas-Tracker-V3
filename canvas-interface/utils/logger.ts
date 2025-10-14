/**
 * Canvas Interface Logging Utility
 * 
 * Provides structured logging for Canvas interface components with:
 * - Different log levels (debug, info, warn, error)
 * - Consistent formatting with emojis and timestamps
 * - Component-based logging (respects architectural boundaries)
 * - No file system operations (console-based only)
 */

export enum LogLevel {
  DEBUG = 0,
  INFO = 1,
  WARN = 2,
  ERROR = 3
}

export interface LogContext {
  courseId?: number;
  studentId?: number;
  assignmentId?: number;
  operation?: string;
  duration?: number;
  [key: string]: any;
}

export class CanvasLogger {
  private componentName: string;
  private logLevel: LogLevel;

  constructor(componentName: string, logLevel: LogLevel = LogLevel.INFO) {
    this.componentName = componentName;
    this.logLevel = logLevel;
  }

  /**
   * Log debug information (only shown in development)
   */
  debug(message: string, context?: LogContext): void {
    if (this.logLevel <= LogLevel.DEBUG) {
      this.log('🔍', 'DEBUG', message, context);
    }
  }

  /**
   * Log general information
   */
  info(message: string, context?: LogContext): void {
    if (this.logLevel <= LogLevel.INFO) {
      this.log('ℹ️', 'INFO', message, context);
    }
  }

  /**
   * Log warnings
   */
  warn(message: string, context?: LogContext): void {
    if (this.logLevel <= LogLevel.WARN) {
      this.log('⚠️', 'WARN', message, context);
    }
  }

  /**
   * Log errors
   */
  error(message: string, error?: Error, context?: LogContext): void {
    if (this.logLevel <= LogLevel.ERROR) {
      let fullMessage = message;
      if (error) {
        fullMessage += ` - ${error.message}`;
      }
      
      this.log('❌', 'ERROR', fullMessage, context);
      
      // Log stack trace for errors if available
      if (error && error.stack) {
        console.error('   Stack:', error.stack);
      }
    }
  }

  /**
   * Log operation start with timing
   */
  startOperation(operation: string, context?: LogContext): number {
    const startTime = Date.now();
    this.info(`Starting ${operation}`, { ...context, operation });
    return startTime;
  }

  /**
   * Log operation completion with duration
   */
  completeOperation(operation: string, startTime: number, context?: LogContext): void {
    const duration = Date.now() - startTime;
    this.info(`✅ Completed ${operation}`, { 
      ...context, 
      operation, 
      duration: `${duration}ms` 
    });
  }

  /**
   * Log operation failure with duration
   */
  failOperation(operation: string, startTime: number, error: Error, context?: LogContext): void {
    const duration = Date.now() - startTime;
    this.error(`Failed ${operation}`, error, { 
      ...context, 
      operation, 
      duration: `${duration}ms` 
    });
  }

  /**
   * Log API call details
   */
  apiCall(method: string, endpoint: string, context?: LogContext): void {
    this.debug(`API: ${method} ${endpoint}`, context);
  }

  /**
   * Log data processing information
   */
  dataProcessing(message: string, count?: number, context?: LogContext): void {
    const contextWithCount = count !== undefined ? { ...context, count } : context;
    this.info(`📊 ${message}`, contextWithCount);
  }

  /**
   * Log Canvas-specific operations
   */
  canvasOperation(message: string, context?: LogContext): void {
    this.info(`🎨 ${message}`, context);
  }

  /**
   * Core logging method with consistent formatting
   */
  private log(emoji: string, level: string, message: string, context?: LogContext): void {
    const timestamp = new Date().toISOString();
    const component = `[${this.componentName}]`;
    
    let logMessage = `${emoji} ${timestamp} ${component} ${message}`;
    
    if (context && Object.keys(context).length > 0) {
      const contextStr = this.formatContext(context);
      logMessage += ` ${contextStr}`;
    }

    // Use appropriate console method based on level
    switch (level) {
      case 'ERROR':
        console.error(logMessage);
        break;
      case 'WARN':
        console.warn(logMessage);
        break;
      case 'DEBUG':
        console.debug(logMessage);
        break;
      default:
        console.log(logMessage);
    }
  }

  /**
   * Format context object for logging
   */
  private formatContext(context: LogContext): string {
    const parts: string[] = [];
    
    // Handle common Canvas context fields with special formatting
    if (context.courseId) parts.push(`Course:${context.courseId}`);
    if (context.studentId) parts.push(`Student:${context.studentId}`);
    if (context.assignmentId) parts.push(`Assignment:${context.assignmentId}`);
    if (context.operation) parts.push(`Op:${context.operation}`);
    if (context.duration) parts.push(`Duration:${context.duration}`);
    if (context.count !== undefined) parts.push(`Count:${context.count}`);
    
    // Add any other context fields
    for (const [key, value] of Object.entries(context)) {
      if (!['courseId', 'studentId', 'assignmentId', 'operation', 'duration', 'count'].includes(key)) {
        parts.push(`${key}:${value}`);
      }
    }
    
    return parts.length > 0 ? `(${parts.join(', ')})` : '';
  }

  /**
   * Create a child logger with additional context
   */
  createChildLogger(childName: string): CanvasLogger {
    return new CanvasLogger(`${this.componentName}.${childName}`, this.logLevel);
  }

  /**
   * Set the minimum log level
   */
  setLogLevel(level: LogLevel): void {
    this.logLevel = level;
  }
}

/**
 * Factory function to create loggers for different Canvas components
 */
export function createCanvasLogger(componentName: string, logLevel?: LogLevel): CanvasLogger {
  // Default to DEBUG in development, INFO in production
  const defaultLevel = process.env.NODE_ENV === 'development' ? LogLevel.DEBUG : LogLevel.INFO;
  return new CanvasLogger(componentName, logLevel || defaultLevel);
}

/**
 * Pre-configured loggers for common Canvas interface components
 */
export const Loggers = {
  CanvasDataConstructor: createCanvasLogger('CanvasDataConstructor'),
  CanvasCalls: createCanvasLogger('CanvasCalls'),
  CanvasStaging: createCanvasLogger('CanvasStaging'),
  PullStudentGrades: createCanvasLogger('PullStudentGrades')
};