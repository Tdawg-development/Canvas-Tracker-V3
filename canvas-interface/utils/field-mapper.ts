/**
 * Field Mapper Utility
 * 
 * Provides automatic field mapping from Canvas API responses to typed interface objects.
 * Eliminates manual field assignments in staging classes by using interface-driven mapping.
 */

import { 
  CanvasCourseFields, 
  CanvasStudentFields, 
  CanvasAssignmentFields, 
  CanvasModuleFields,
  FieldMappingConfig
} from '../types/field-mappings';

// ============================================================================
// Core Field Mapping Types
// ============================================================================

/**
 * Configuration for field mapping that supports nested object mapping
 */
export type FieldMapping<T> = {
  [K in keyof T]?: {
    sourcePath: string;
    transform?: (value: any) => T[K];
    required?: boolean;
    defaultValue?: T[K];
  }
}

/**
 * Result of field mapping operation with validation info
 */
export interface FieldMappingResult<T> {
  mappedData: T;
  missingRequiredFields: string[];
  mappingErrors: Array<{ field: string; error: string; }>;
  fieldsProcessed: number;
  fieldsSkipped: number;
}

// ============================================================================
// FieldMapper Class
// ============================================================================

export class FieldMapper {
  
  /**
   * Maps fields from raw Canvas API data to a typed interface object
   * Uses automatic field detection based on interface properties
   */
  static mapFields<T>(data: any, targetInterface: new () => T): T {
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid data provided for field mapping');
    }

    const mapped: Partial<T> = {};
    
    // Create a sample instance to get field names
    // Note: This approach works for interfaces with concrete implementations
    try {
      const sampleInstance = new targetInterface();
      const fieldNames = Object.keys(sampleInstance);
      
      fieldNames.forEach(field => {
        if (field in data && data[field] !== undefined) {
          (mapped as any)[field] = data[field];
        }
      });
      
    } catch (error) {
      // Fallback: Direct property mapping from data object
      Object.keys(data).forEach(field => {
        if (data[field] !== undefined) {
          (mapped as any)[field] = data[field];
        }
      });
    }
    
    return mapped as T;
  }

  /**
   * Maps fields using explicit field mapping configuration
   * Supports nested object paths and field transformations
   */
  static mapNestedFields<T>(data: any, mapping: FieldMapping<T>): FieldMappingResult<T> {
    const result: Partial<T> = {};
    const missingRequiredFields: string[] = [];
    const mappingErrors: Array<{ field: string; error: string; }> = [];
    let fieldsProcessed = 0;
    let fieldsSkipped = 0;

    if (!data || typeof data !== 'object') {
      throw new Error('Invalid data provided for nested field mapping');
    }

    Object.entries(mapping).forEach(([targetField, config]: [string, any]) => {
      try {
        const value = this.getNestedValue(data, config.sourcePath);
        
        if (value !== undefined) {
          // Apply transformation if specified
          const transformedValue = config.transform ? config.transform(value) : value;
          (result as any)[targetField] = transformedValue;
          fieldsProcessed++;
        } else if (config.required) {
          missingRequiredFields.push(targetField);
          // Use default value if provided
          if (config.defaultValue !== undefined) {
            (result as any)[targetField] = config.defaultValue;
          }
        } else if (config.defaultValue !== undefined) {
          (result as any)[targetField] = config.defaultValue;
          fieldsProcessed++;
        } else {
          fieldsSkipped++;
        }
      } catch (error) {
        mappingErrors.push({
          field: targetField,
          error: error instanceof Error ? error.message : 'Unknown mapping error'
        });
      }
    });
    
    return {
      mappedData: result as T,
      missingRequiredFields,
      mappingErrors,
      fieldsProcessed,
      fieldsSkipped
    };
  }

  /**
   * Smart field mapping that combines automatic detection with configuration overrides
   */
  static mapFieldsWithConfig<T>(
    data: any, 
    targetInterface: new () => T, 
    config?: FieldMapping<T>
  ): FieldMappingResult<T> {
    let baseMapping: T;
    let configResult: FieldMappingResult<T> | undefined;

    // First, try automatic mapping
    try {
      baseMapping = this.mapFields(data, targetInterface);
    } catch (error) {
      // If automatic mapping fails, start with empty object
      baseMapping = {} as T;
    }

    // Apply configuration overrides if provided
    if (config) {
      configResult = this.mapNestedFields(data, config);
      // Merge configuration results into base mapping
      Object.assign(baseMapping, configResult.mappedData);
    }

    return {
      mappedData: baseMapping,
      missingRequiredFields: configResult?.missingRequiredFields || [],
      mappingErrors: configResult?.mappingErrors || [],
      fieldsProcessed: configResult?.fieldsProcessed || Object.keys(baseMapping).length,
      fieldsSkipped: configResult?.fieldsSkipped || 0
    };
  }

  /**
   * Canvas-specific field mapper for Course entities
   */
  static mapCanvasCourse(data: any): CanvasCourseFields {
    if (!data || typeof data !== 'object') {
      throw new Error('Invalid data provided for course mapping');
    }

    // Direct field mapping from data
    const mapped: CanvasCourseFields = {
      id: data.id,
      name: data.name,
      course_code: data.course_code
    };

    // Add optional fields if they exist
    Object.keys(data).forEach(field => {
      if (data[field] !== undefined) {
        (mapped as any)[field] = data[field];
      }
    });

    return mapped;
  }

  /**
   * Canvas-specific field mapper for Student entities
   */
  static mapCanvasStudent(data: any): CanvasStudentFields {
    return this.mapFields(data, Object as any) as CanvasStudentFields;
  }

  /**
   * Canvas-specific field mapper for Assignment entities
   */
  static mapCanvasAssignment(data: any): CanvasAssignmentFields {
    return this.mapFields(data, Object as any) as CanvasAssignmentFields;
  }

  /**
   * Canvas-specific field mapper for Module entities
   */
  static mapCanvasModule(data: any): CanvasModuleFields {
    return this.mapFields(data, Object as any) as CanvasModuleFields;
  }

  // ========================================================================
  // Specialized Canvas Mappings
  // ========================================================================

  /**
   * Maps Canvas course data with enhanced field selection based on sync configuration
   */
  static mapCanvasCourseAdvanced(
    data: any, 
    fieldConfig?: FieldMappingConfig['course']
  ): CanvasCourseFields {
    const baseFields: CanvasCourseFields = {
      id: data.id,
      name: data.name || '',
      course_code: data.course_code || ''
    };

    // Apply field filtering based on configuration
    if (fieldConfig) {
      const result: Partial<CanvasCourseFields> = { ...baseFields };
      
      Object.keys(fieldConfig).forEach(field => {
        if (fieldConfig[field as keyof CanvasCourseFields] && data[field] !== undefined) {
          (result as any)[field] = data[field];
        }
      });
      
      return result as CanvasCourseFields;
    }

    // Include all available fields if no config specified
    return this.mapCanvasCourse(data);
  }

  /**
   * Maps Canvas student data with enhanced nested object handling
   */
  static mapCanvasStudentAdvanced(
    data: any, 
    fieldConfig?: FieldMappingConfig['student']
  ): CanvasStudentFields {
    const baseFields: CanvasStudentFields = {
      id: data.id || data.user_id,
      user_id: data.user_id || data.id
    };

    // Handle nested user object
    if (data.user) {
      baseFields.user = {
        id: data.user.id,
        name: data.user.name || 'Unknown',
        login_id: data.user.login_id || '',
        email: data.user.email,
        sortable_name: data.user.sortable_name,
        short_name: data.user.short_name,
        avatar_url: data.user.avatar_url,
        pronouns: data.user.pronouns,
        locale: data.user.locale,
        effective_locale: data.user.effective_locale,
        time_zone: data.user.time_zone
      };
    }

    // Handle nested grades object
    if (data.grades) {
      baseFields.grades = {
        current_score: data.grades.current_score,
        final_score: data.grades.final_score,
        current_grade: data.grades.current_grade,
        final_grade: data.grades.final_grade,
        override_score: data.grades.override_score,
        override_grade: data.grades.override_grade,
        unposted_current_score: data.grades.unposted_current_score,
        unposted_final_score: data.grades.unposted_final_score,
        unposted_current_grade: data.grades.unposted_current_grade,
        unposted_final_grade: data.grades.unposted_final_grade
      };
    }

    // Apply field filtering based on configuration
    if (fieldConfig) {
      const result: Partial<CanvasStudentFields> = { ...baseFields };
      
      Object.keys(fieldConfig).forEach(field => {
        if (fieldConfig[field as keyof CanvasStudentFields] && data[field] !== undefined) {
          (result as any)[field] = data[field];
        }
      });
      
      return result as CanvasStudentFields;
    }

    // Add remaining fields from data
    const allFields = { ...baseFields };
    Object.keys(data).forEach(field => {
      if (!(field in allFields) && data[field] !== undefined) {
        (allFields as any)[field] = data[field];
      }
    });

    return allFields;
  }

  // ========================================================================
  // Utility Methods
  // ========================================================================

  /**
   * Safely retrieves nested value from object using dot notation path
   */
  private static getNestedValue(obj: any, path: string): any {
    if (!obj || !path) return undefined;
    
    return path.split('.').reduce((current, key) => {
      if (current && typeof current === 'object' && key in current) {
        return current[key];
      }
      return undefined;
    }, obj);
  }

  /**
   * Validates that all required fields are present in mapped data
   */
  static validateRequiredFields<T>(
    mappedData: T, 
    requiredFields: (keyof T)[]
  ): { isValid: boolean; missingFields: string[] } {
    const missingFields: string[] = [];
    
    requiredFields.forEach(field => {
      if (mappedData[field] === undefined || mappedData[field] === null) {
        missingFields.push(field as string);
      }
    });
    
    return {
      isValid: missingFields.length === 0,
      missingFields
    };
  }

  /**
   * Creates a field mapping report for debugging
   */
  static createMappingReport<T>(
    originalData: any,
    mappedData: T,
    targetInterface: string
  ): {
    originalFieldCount: number;
    mappedFieldCount: number;
    unmappedFields: string[];
    targetInterface: string;
  } {
    const originalFields = Object.keys(originalData || {});
    const mappedFields = Object.keys(mappedData || {});
    const unmappedFields = originalFields.filter(field => !mappedFields.includes(field));
    
    return {
      originalFieldCount: originalFields.length,
      mappedFieldCount: mappedFields.length,
      unmappedFields,
      targetInterface
    };
  }
}

// ============================================================================
// Export Utilities
// ============================================================================

/**
 * Convenience function for mapping Canvas course data
 */
export function mapCourse(data: any, config?: FieldMappingConfig['course']): CanvasCourseFields {
  return FieldMapper.mapCanvasCourseAdvanced(data, config);
}

/**
 * Convenience function for mapping Canvas student data
 */
export function mapStudent(data: any, config?: FieldMappingConfig['student']): CanvasStudentFields {
  return FieldMapper.mapCanvasStudentAdvanced(data, config);
}

/**
 * Convenience function for mapping Canvas assignment data
 */
export function mapAssignment(data: any, config?: FieldMappingConfig['assignment']): CanvasAssignmentFields {
  return FieldMapper.mapCanvasAssignment(data);
}

/**
 * Convenience function for mapping Canvas module data
 */
export function mapModule(data: any, config?: FieldMappingConfig['module']): CanvasModuleFields {
  return FieldMapper.mapCanvasModule(data);
}