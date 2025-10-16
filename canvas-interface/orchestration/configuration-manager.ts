/**
 * Configuration Manager for Pipeline Orchestrator
 * 
 * Manages and validates sync configurations for the Canvas pipeline.
 * Provides configuration validation, defaults, and optimization suggestions.
 */

import { 
  SyncConfiguration, 
  FULL_SYNC_PROFILE, 
  validateConfiguration as validateSyncConfig,
  estimatePerformanceImpact,
  getPerformanceDescription
} from '../types/sync-configuration';

// ============================================================================
// Configuration Validation Interfaces
// ============================================================================

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
  performance: {
    impact: number;
    description: string;
    estimatedApiCalls: number;
    recommendedForBulk: boolean;
  };
}

// ============================================================================
// Configuration Manager Class
// ============================================================================

export class ConfigurationManager {
  private config: SyncConfiguration;
  private validationCache: Map<string, ValidationResult> = new Map();

  constructor(config?: SyncConfiguration) {
    this.config = config ? validateSyncConfig(config) : FULL_SYNC_PROFILE;
  }

  // ========================================================================
  // Configuration Access
  // ========================================================================

  /**
   * Get current configuration (returns a copy to prevent mutations)
   */
  getConfig(): SyncConfiguration {
    return JSON.parse(JSON.stringify(this.config));
  }

  /**
   * Update configuration with validation
   */
  updateConfig(updates: Partial<SyncConfiguration>): void {
    // Clear validation cache when config changes
    this.validationCache.clear();

    // Merge updates with current config
    const newConfig = {
      ...this.config,
      ...updates,
      studentFields: {
        ...this.config.studentFields,
        ...(updates.studentFields || {})
      },
      assignmentFields: {
        ...this.config.assignmentFields,
        ...(updates.assignmentFields || {})
      },
      processing: {
        ...this.config.processing,
        ...(updates.processing || {})
      }
    };

    // Validate the new configuration
    const validation = this.validateConfiguration(newConfig);
    if (!validation.valid) {
      throw new Error(`Invalid configuration: ${validation.errors.join(', ')}`);
    }

    this.config = validateSyncConfig(newConfig);
  }

  /**
   * Reset to default configuration
   */
  resetToDefault(): void {
    this.validationCache.clear();
    this.config = FULL_SYNC_PROFILE;
  }

  // ========================================================================
  // Configuration Validation
  // ========================================================================

  /**
   * Validate current or provided configuration
   */
  validateConfiguration(config?: SyncConfiguration): ValidationResult {
    const targetConfig = config || this.config;
    const configKey = this.generateConfigKey(targetConfig);

    // Check cache first
    if (this.validationCache.has(configKey)) {
      return this.validationCache.get(configKey)!;
    }

    const errors: string[] = [];
    const warnings: string[] = [];

    // Basic structure validation
    this.validateStructure(targetConfig, errors);

    // Logical consistency validation
    this.validateConsistency(targetConfig, errors, warnings);

    // Performance validation
    this.validatePerformance(targetConfig, warnings);

    // Calculate performance metrics
    const performanceImpact = estimatePerformanceImpact(targetConfig);
    const performanceDescription = getPerformanceDescription(targetConfig);
    const estimatedApiCalls = this.estimateApiCalls(targetConfig);

    const result: ValidationResult = {
      valid: errors.length === 0,
      errors,
      warnings,
      performance: {
        impact: performanceImpact,
        description: performanceDescription,
        estimatedApiCalls,
        recommendedForBulk: performanceImpact <= 0.6 // Recommend for bulk if impact is moderate or less
      }
    };

    // Cache the result
    this.validationCache.set(configKey, result);
    return result;
  }

  // ========================================================================
  // Configuration Analysis
  // ========================================================================

  /**
   * Get configuration analysis and recommendations
   */
  analyzeConfiguration(config?: SyncConfiguration): {
    validation: ValidationResult;
    recommendations: string[];
    optimizations: string[];
    entityBreakdown: {[key: string]: boolean};
  } {
    const targetConfig = config || this.config;
    const validation = this.validateConfiguration(targetConfig);
    
    const recommendations: string[] = [];
    const optimizations: string[] = [];

    // Generate recommendations based on configuration
    if (targetConfig.students && !targetConfig.studentFields.scores) {
      recommendations.push("Consider enabling student scores if grade data is needed");
    }

    if (targetConfig.assignments && !targetConfig.assignmentFields.basicInfo) {
      recommendations.push("Assignment basic info should be enabled when collecting assignments");
    }

    if (targetConfig.processing.enhanceWithTimestamps && !targetConfig.assignmentFields.timestamps) {
      recommendations.push("Enable assignment timestamps field to make use of timestamp enhancement");
    }

    // Generate optimizations
    if (validation.performance.impact > 0.8) {
      optimizations.push("Consider using LIGHTWEIGHT_PROFILE for faster processing");
      optimizations.push("Disable analytics fields if not needed for reporting");
    }

    if (targetConfig.modules && !targetConfig.assignments) {
      optimizations.push("Modules provide limited value without assignments - consider enabling assignments");
    }

    const entityBreakdown = {
      courseInfo: targetConfig.courseInfo,
      students: targetConfig.students,
      assignments: targetConfig.assignments,
      modules: targetConfig.modules,
      grades: targetConfig.grades
    };

    return {
      validation,
      recommendations,
      optimizations,
      entityBreakdown
    };
  }

  /**
   * Compare two configurations
   */
  compareConfigurations(config1: SyncConfiguration, config2: SyncConfiguration): {
    differences: string[];
    performanceDiff: number;
    apiCallsDiff: number;
    recommendation: string;
  } {
    const differences: string[] = [];
    
    // Compare major entities
    const entities = ['courseInfo', 'students', 'assignments', 'modules', 'grades'] as const;
    entities.forEach(entity => {
      if (config1[entity] !== config2[entity]) {
        differences.push(`${entity}: ${config1[entity]} -> ${config2[entity]}`);
      }
    });

    // Compare student fields
    Object.keys(config1.studentFields).forEach(field => {
      if (config1.studentFields[field as keyof typeof config1.studentFields] !== 
          config2.studentFields[field as keyof typeof config2.studentFields]) {
        differences.push(`studentFields.${field}: ${config1.studentFields[field as keyof typeof config1.studentFields]} -> ${config2.studentFields[field as keyof typeof config2.studentFields]}`);
      }
    });

    // Compare performance
    const perf1 = estimatePerformanceImpact(config1);
    const perf2 = estimatePerformanceImpact(config2);
    const performanceDiff = perf2 - perf1;

    const apiCalls1 = this.estimateApiCalls(config1);
    const apiCalls2 = this.estimateApiCalls(config2);
    const apiCallsDiff = apiCalls2 - apiCalls1;

    let recommendation = "Configurations are equivalent";
    if (performanceDiff > 0.1) {
      recommendation = "Second configuration is significantly slower";
    } else if (performanceDiff < -0.1) {
      recommendation = "Second configuration is significantly faster";
    }

    return {
      differences,
      performanceDiff,
      apiCallsDiff,
      recommendation
    };
  }

  // ========================================================================
  // Private Validation Methods
  // ========================================================================

  private validateStructure(config: SyncConfiguration, errors: string[]): void {
    // Check required top-level properties
    const requiredProps = ['courseInfo', 'students', 'assignments', 'modules', 'grades'];
    requiredProps.forEach(prop => {
      if (typeof config[prop as keyof SyncConfiguration] !== 'boolean') {
        errors.push(`Missing or invalid property: ${prop}`);
      }
    });

    // Check nested objects
    if (!config.studentFields || typeof config.studentFields !== 'object') {
      errors.push('Missing or invalid studentFields configuration');
    }

    if (!config.assignmentFields || typeof config.assignmentFields !== 'object') {
      errors.push('Missing or invalid assignmentFields configuration');
    }

    if (!config.processing || typeof config.processing !== 'object') {
      errors.push('Missing or invalid processing configuration');
    }
  }

  private validateConsistency(config: SyncConfiguration, errors: string[], warnings: string[]): void {
    // If students are disabled, student fields should be mostly disabled
    if (!config.students) {
      const studentFieldsEnabled = Object.values(config.studentFields).some(field => field);
      if (studentFieldsEnabled) {
        warnings.push('Student fields are enabled but student collection is disabled');
      }
    }

    // If assignments are disabled, assignment fields should be disabled
    if (!config.assignments) {
      const assignmentFieldsEnabled = Object.values(config.assignmentFields).some(field => field);
      if (assignmentFieldsEnabled) {
        warnings.push('Assignment fields are enabled but assignment collection is disabled');
      }
    }

    // If modules are enabled but assignments are disabled, warn about limited utility
    if (config.modules && !config.assignments) {
      warnings.push('Modules are enabled but assignments are disabled - modules provide limited value without assignments');
    }

    // Processing validation
    if (config.processing.enhanceWithTimestamps && !config.assignmentFields.timestamps) {
      warnings.push('Timestamp enhancement is enabled but assignment timestamp fields are disabled');
    }

    if (config.processing.resolveQuizAssignments && !config.assignments) {
      warnings.push('Quiz assignment resolution is enabled but assignment collection is disabled');
    }
  }

  private validatePerformance(config: SyncConfiguration, warnings: string[]): void {
    const impact = estimatePerformanceImpact(config);
    
    if (impact > 0.9) {
      warnings.push('Configuration has very high performance impact - consider using a lighter profile for bulk operations');
    } else if (impact > 0.75) {
      warnings.push('Configuration has high performance impact - monitor API rate limits');
    }

    // Check for potentially expensive combinations
    if (config.students && config.studentFields.analytics && config.assignments && config.assignmentFields.timestamps) {
      warnings.push('Full analytics + timestamps combination is expensive - consider for targeted operations only');
    }
  }

  private estimateApiCalls(config: SyncConfiguration): number {
    let calls = 0;

    // Base course info call
    if (config.courseInfo) calls += 1;

    // Student-related calls
    if (config.students) {
      calls += 1; // Basic enrollment call
      if (config.studentFields.analytics) calls += 0.5; // Additional data
      if (config.grades) calls += 0.5; // Grade data
    }

    // Assignment-related calls
    if (config.assignments) {
      calls += 1; // Basic assignments call
      if (config.assignmentFields.timestamps || config.processing.enhanceWithTimestamps) {
        calls += 1; // Additional detailed assignment call
      }
    }

    // Module calls
    if (config.modules) {
      calls += 1; // Modules with items
    }

    return Math.ceil(calls);
  }

  private generateConfigKey(config: SyncConfiguration): string {
    return JSON.stringify(config);
  }

  // ========================================================================
  // Configuration Presets and Utilities
  // ========================================================================

  /**
   * Get optimal configuration for specific use cases
   */
  getOptimalConfiguration(useCase: 'bulk' | 'single' | 'analytics' | 'gradebook'): SyncConfiguration {
    switch (useCase) {
      case 'bulk':
        return {
          courseInfo: true,
          students: true,
          assignments: true,
          modules: false,
          grades: true,
          studentFields: {
            basicInfo: true,
            scores: true,
            analytics: false,
            enrollmentDetails: false
          },
          assignmentFields: {
            basicInfo: true,
            timestamps: false,
            submissions: false,
            urls: false,
            moduleInfo: false
          },
          processing: {
            enhanceWithTimestamps: false,
            filterUngradedQuizzes: true,
            resolveQuizAssignments: false,
            includeUnpublished: false
          }
        };

      case 'analytics':
        return {
          courseInfo: true,
          students: true,
          assignments: true,
          modules: true,
          grades: true,
          studentFields: {
            basicInfo: true,
            scores: true,
            analytics: true,
            enrollmentDetails: true
          },
          assignmentFields: {
            basicInfo: true,
            timestamps: true,
            submissions: true,
            urls: false,
            moduleInfo: true
          },
          processing: {
            enhanceWithTimestamps: true,
            filterUngradedQuizzes: false,
            resolveQuizAssignments: true,
            includeUnpublished: true
          }
        };

      case 'gradebook':
        return {
          courseInfo: true,
          students: true,
          assignments: false,
          modules: false,
          grades: true,
          studentFields: {
            basicInfo: true,
            scores: true,
            analytics: false,
            enrollmentDetails: true
          },
          assignmentFields: {
            basicInfo: false,
            timestamps: false,
            submissions: false,
            urls: false,
            moduleInfo: false
          },
          processing: {
            enhanceWithTimestamps: false,
            filterUngradedQuizzes: false,
            resolveQuizAssignments: false,
            includeUnpublished: false
          }
        };

      case 'single':
      default:
        return FULL_SYNC_PROFILE;
    }
  }
}