/**
 * API Parameter Builder
 * 
 * Configuration-driven API parameter generation that eliminates 70+ lines 
 * of conditional logic in the data constructor.
 */

import { SyncConfiguration } from '../types/sync-configuration';
import { 
  ApiFieldMapping,
  STUDENT_API_MAPPINGS,
  COURSE_API_MAPPINGS,
  ASSIGNMENT_API_MAPPINGS,
  MODULE_API_MAPPINGS
} from '../config/api-field-mappings';

// ============================================================================
// API Parameter Builder Class
// ============================================================================

export class ApiParameterBuilder {
  
  /**
   * Build API parameters for a specific entity type using configuration mappings
   * 
   * @param mappings Array of field mappings for the entity type
   * @param config Sync configuration object
   * @returns Array of unique API parameter strings
   */
  static buildParameters(
    mappings: ApiFieldMapping[], 
    config: SyncConfiguration
  ): string[] {
    const params = new Set<string>();
    
    mappings.forEach(mapping => {
      if (this.shouldIncludeField(mapping.configPath, config)) {
        params.add(mapping.apiParam);
        
        // Add dependencies if specified
        if (mapping.dependencies) {
          mapping.dependencies.forEach(dep => params.add(dep));
        }
      }
    });
    
    return Array.from(params);
  }

  /**
   * Build parameters specifically for student/enrollment API calls
   */
  static buildStudentParameters(config: SyncConfiguration): string[] {
    return this.buildParameters(STUDENT_API_MAPPINGS, config);
  }

  /**
   * Build parameters specifically for course API calls
   */
  static buildCourseParameters(config: SyncConfiguration): string[] {
    return this.buildParameters(COURSE_API_MAPPINGS, config);
  }

  /**
   * Build parameters specifically for assignment API calls
   */
  static buildAssignmentParameters(config: SyncConfiguration): string[] {
    return this.buildParameters(ASSIGNMENT_API_MAPPINGS, config);
  }

  /**
   * Build parameters specifically for module API calls
   */
  static buildModuleParameters(config: SyncConfiguration): string[] {
    return this.buildParameters(MODULE_API_MAPPINGS, config);
  }

  /**
   * Build parameters for multiple entity types at once
   */
  static buildAllParameters(config: SyncConfiguration): {
    student: string[];
    course: string[];
    assignment: string[];
    module: string[];
  } {
    return {
      student: this.buildStudentParameters(config),
      course: this.buildCourseParameters(config),
      assignment: this.buildAssignmentParameters(config),
      module: this.buildModuleParameters(config)
    };
  }

  // ========================================================================
  // Advanced Parameter Building
  // ========================================================================

  /**
   * Build parameters with filtering and validation
   */
  static buildParametersAdvanced(
    mappings: ApiFieldMapping[],
    config: SyncConfiguration,
    options?: {
      /** Validate that all required config paths exist */
      validateConfig?: boolean;
      /** Filter out duplicate parameters */
      removeDuplicates?: boolean;
      /** Add debug information */
      debug?: boolean;
    }
  ): {
    parameters: string[];
    mappingsUsed: ApiFieldMapping[];
    missingConfigPaths?: string[];
    debugInfo?: any;
  } {
    const params = new Set<string>();
    const mappingsUsed: ApiFieldMapping[] = [];
    const missingConfigPaths: string[] = [];

    mappings.forEach(mapping => {
      const shouldInclude = this.shouldIncludeField(mapping.configPath, config);
      
      if (options?.validateConfig && !this.configPathExists(mapping.configPath, config)) {
        missingConfigPaths.push(mapping.configPath);
      }
      
      if (shouldInclude) {
        params.add(mapping.apiParam);
        mappingsUsed.push(mapping);
        
        // Add dependencies
        if (mapping.dependencies) {
          mapping.dependencies.forEach(dep => params.add(dep));
        }
      }
    });

    const result: any = {
      parameters: Array.from(params),
      mappingsUsed
    };

    if (options?.validateConfig && missingConfigPaths.length > 0) {
      result.missingConfigPaths = missingConfigPaths;
    }

    if (options?.debug) {
      result.debugInfo = {
        totalMappings: mappings.length,
        appliedMappings: mappingsUsed.length,
        skippedMappings: mappings.length - mappingsUsed.length,
        finalParameterCount: params.size,
        duplicatesRemoved: options.removeDuplicates ? 
          mappings.length - params.size : 0
      };
    }

    return result;
  }

  /**
   * Create parameter string for Canvas API include parameter
   */
  static buildIncludeParameterString(
    mappings: ApiFieldMapping[],
    config: SyncConfiguration
  ): string {
    const parameters = this.buildParameters(mappings, config);
    return parameters.join(',');
  }

  /**
   * Build parameters optimized for specific sync profiles
   */
  static buildParametersForProfile(
    profileName: 'full' | 'lightweight' | 'analytics' | 'students_only' | 'assignments_only',
    entityType: 'student' | 'course' | 'assignment' | 'module',
    config: SyncConfiguration
  ): string[] {
    let mappings: ApiFieldMapping[];

    // Select mappings based on entity type
    switch (entityType) {
      case 'student':
        mappings = STUDENT_API_MAPPINGS;
        break;
      case 'course':
        mappings = COURSE_API_MAPPINGS;
        break;
      case 'assignment':
        mappings = ASSIGNMENT_API_MAPPINGS;
        break;
      case 'module':
        mappings = MODULE_API_MAPPINGS;
        break;
      default:
        throw new Error(`Unknown entity type: ${entityType}`);
    }

    // Filter mappings based on profile
    switch (profileName) {
      case 'lightweight':
        mappings = mappings.filter(m => 
          m.configPath.includes('basicInfo') || 
          m.configPath.includes('scores') ||
          m.apiParam === 'grades' ||
          m.apiParam === 'user'
        );
        break;
      case 'analytics':
        mappings = mappings.filter(m => 
          m.configPath.includes('analytics') || 
          m.configPath.includes('scores') ||
          m.configPath.includes('timestamps')
        );
        break;
      case 'students_only':
        if (entityType !== 'student') return [];
        break;
      case 'assignments_only':
        if (entityType === 'student') return [];
        break;
      // 'full' uses all mappings
    }

    return this.buildParameters(mappings, config);
  }

  // ========================================================================
  // Utility Methods
  // ========================================================================

  /**
   * Check if a field should be included based on configuration path
   */
  private static shouldIncludeField(configPath: string, config: SyncConfiguration): boolean {
    const keys = configPath.split('.');
    let current: any = config;
    
    for (const key of keys) {
      if (current[key] === undefined) {
        return false;
      }
      current = current[key];
    }
    
    return Boolean(current);
  }

  /**
   * Check if a configuration path exists (for validation)
   */
  private static configPathExists(configPath: string, config: SyncConfiguration): boolean {
    const keys = configPath.split('.');
    let current: any = config;
    
    for (const key of keys) {
      if (typeof current !== 'object' || current === null || !(key in current)) {
        return false;
      }
      current = current[key];
    }
    
    return true;
  }

  /**
   * Get all possible parameters for an entity type (for documentation/debugging)
   */
  static getAllPossibleParameters(entityType: 'student' | 'course' | 'assignment' | 'module'): string[] {
    let mappings: ApiFieldMapping[];
    
    switch (entityType) {
      case 'student':
        mappings = STUDENT_API_MAPPINGS;
        break;
      case 'course':
        mappings = COURSE_API_MAPPINGS;
        break;
      case 'assignment':
        mappings = ASSIGNMENT_API_MAPPINGS;
        break;
      case 'module':
        mappings = MODULE_API_MAPPINGS;
        break;
      default:
        return [];
    }

    const allParams = new Set<string>();
    mappings.forEach(mapping => {
      allParams.add(mapping.apiParam);
      if (mapping.dependencies) {
        mapping.dependencies.forEach(dep => allParams.add(dep));
      }
    });

    return Array.from(allParams).sort();
  }

  /**
   * Create a parameter report for debugging
   */
  static createParameterReport(
    config: SyncConfiguration,
    entityType?: 'student' | 'course' | 'assignment' | 'module'
  ): {
    entityType?: string;
    configurationActive: boolean;
    parameters: string[];
    mappingCount: number;
    description: string;
  } {
    if (!entityType) {
      const allParams = this.buildAllParameters(config);
      return {
        configurationActive: true,
        parameters: [
          ...allParams.student,
          ...allParams.course, 
          ...allParams.assignment,
          ...allParams.module
        ],
        mappingCount: allParams.student.length + allParams.course.length + 
                     allParams.assignment.length + allParams.module.length,
        description: 'All entity types combined'
      };
    }

    const parameters = this.buildParametersForProfile('full', entityType, config);
    
    return {
      entityType,
      configurationActive: parameters.length > 0,
      parameters,
      mappingCount: parameters.length,
      description: `Parameters for ${entityType} API calls`
    };
  }
}

// ============================================================================
// Convenience Functions
// ============================================================================

/**
 * Quick function to build student enrollment API parameters
 */
export function buildStudentIncludeParams(config: SyncConfiguration): string[] {
  return ApiParameterBuilder.buildStudentParameters(config);
}

/**
 * Quick function to build course API parameters  
 */
export function buildCourseIncludeParams(config: SyncConfiguration): string[] {
  return ApiParameterBuilder.buildCourseParameters(config);
}

/**
 * Quick function to build assignment API parameters
 */
export function buildAssignmentIncludeParams(config: SyncConfiguration): string[] {
  return ApiParameterBuilder.buildAssignmentParameters(config);
}

/**
 * Quick function to build module API parameters
 */
export function buildModuleIncludeParams(config: SyncConfiguration): string[] {
  return ApiParameterBuilder.buildModuleParameters(config);
}

/**
 * Create Canvas API include parameter string
 */
export function createIncludeString(parameters: string[]): string {
  return parameters.length > 0 ? parameters.join(',') : '';
}