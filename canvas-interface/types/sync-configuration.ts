/**
 * Configuration system for selective Canvas data synchronization
 * 
 * This module defines the configuration schema that controls what data gets
 * collected from Canvas API and how it gets processed. It enables fine-grained
 * control over API usage and processing time by allowing users to specify
 * exactly what data they need.
 */

// ============================================================================
// Core Configuration Interfaces
// ============================================================================

/**
 * Field-level configuration for student data collection
 */
export interface StudentFieldConfiguration {
  /** Basic student information: name, email, login_id */
  basicInfo: boolean;
  
  /** Grade information: current_score, final_score */
  scores: boolean;
  
  /** Activity analytics: last_activity, enrollment_date, participation */
  analytics: boolean;
  
  /** Enrollment details: enrollment_status, section_id */
  enrollmentDetails: boolean;
}

/**
 * Field-level configuration for assignment data collection
 */
export interface AssignmentFieldConfiguration {
  /** Basic assignment info: name, points_possible, due_date */
  basicInfo: boolean;
  
  /** Timestamp information: created_at, updated_at */
  timestamps: boolean;
  
  /** Submission data: submission_types, grading_type */
  submissions: boolean;
  
  /** Assignment URLs and external references */
  urls: boolean;
  
  /** Module positioning and organization data */
  moduleInfo: boolean;
}

/**
 * Processing options that control how data is enhanced and filtered
 */
export interface ProcessingConfiguration {
  /** Whether to enhance assignments with detailed timestamp data from Canvas API */
  enhanceWithTimestamps: boolean;
  
  /** Whether to filter out ungraded quiz assignments */
  filterUngradedQuizzes: boolean;
  
  /** Whether to resolve quiz assignments to their underlying assignment data */
  resolveQuizAssignments: boolean;
  
  /** Whether to include unpublished assignments in the collection */
  includeUnpublished: boolean;
}

/**
 * Main synchronization configuration interface
 * 
 * This configuration controls what data categories get collected and how
 * they are processed. It provides both high-level toggles for major data
 * types and fine-grained field-level controls.
 */
export interface SyncConfiguration {
  // ========================================
  // High-Level Data Categories
  // ========================================
  
  /** Whether to collect course information */
  courseInfo: boolean;
  
  /** Whether to collect student enrollment data */
  students: boolean;
  
  /** Whether to collect assignment data */
  assignments: boolean;
  
  /** Whether to collect module organization data */
  modules: boolean;
  
  /** Whether to collect grade/score data */
  grades: boolean;
  
  // ========================================
  // Field-Level Controls
  // ========================================
  
  /** Fine-grained control over student data fields */
  studentFields: StudentFieldConfiguration;
  
  /** Fine-grained control over assignment data fields */
  assignmentFields: AssignmentFieldConfiguration;
  
  // ========================================
  // Processing Options
  // ========================================
  
  /** Processing and enhancement options */
  processing: ProcessingConfiguration;
}

// ============================================================================
// Predefined Configuration Profiles
// ============================================================================

/**
 * Full synchronization profile - collects all available data
 * 
 * This profile maximizes data collection but also uses the most API calls
 * and processing time. Suitable when you need complete Canvas data.
 */
export const FULL_SYNC_PROFILE: SyncConfiguration = {
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
    urls: true,
    moduleInfo: true
  },
  processing: {
    enhanceWithTimestamps: true,
    filterUngradedQuizzes: true,
    resolveQuizAssignments: true,
    includeUnpublished: false
  }
};

/**
 * Students-only synchronization profile
 * 
 * Collects only student enrollment and grade data. Skips all assignment
 * and module collection. Ideal for gradebook-focused applications.
 * 
 * Performance: ~60-70% fewer API calls compared to full sync
 */
export const STUDENTS_ONLY_PROFILE: SyncConfiguration = {
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

/**
 * Assignments-only synchronization profile
 * 
 * Collects only assignment and module data. Skips student enrollment
 * information. Ideal for curriculum analysis or assignment tracking.
 * 
 * Performance: ~40-50% fewer API calls compared to full sync
 */
export const ASSIGNMENTS_ONLY_PROFILE: SyncConfiguration = {
  courseInfo: true,
  students: false,
  assignments: true,
  modules: true,
  grades: false,
  studentFields: {
    basicInfo: false,
    scores: false,
    analytics: false,
    enrollmentDetails: false
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
    filterUngradedQuizzes: true,
    resolveQuizAssignments: true,
    includeUnpublished: false
  }
};

/**
 * Lightweight synchronization profile
 * 
 * Minimal data collection focusing on essential information only.
 * Optimized for speed and minimal API usage.
 * 
 * Performance: ~70-80% fewer API calls compared to full sync
 */
export const LIGHTWEIGHT_PROFILE: SyncConfiguration = {
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
    filterUngradedQuizzes: false, // Temporarily disabled to test assignment issues
    resolveQuizAssignments: false,
    includeUnpublished: false
  }
};

/**
 * Analytics-focused synchronization profile
 * 
 * Optimized for collecting data needed for analytics and reporting.
 * Includes detailed timestamps and activity data.
 */
export const ANALYTICS_PROFILE: SyncConfiguration = {
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
    filterUngradedQuizzes: false, // Keep all for analytics
    resolveQuizAssignments: true,
    includeUnpublished: true // Include for comprehensive analysis
  }
};

// ============================================================================
// Profile Registry and Utilities
// ============================================================================

/**
 * Registry of all available configuration profiles
 */
export const SYNC_PROFILES = {
  FULL: FULL_SYNC_PROFILE,
  STUDENTS_ONLY: STUDENTS_ONLY_PROFILE,
  ASSIGNMENTS_ONLY: ASSIGNMENTS_ONLY_PROFILE,
  LIGHTWEIGHT: LIGHTWEIGHT_PROFILE,
  ANALYTICS: ANALYTICS_PROFILE
} as const;

/**
 * Type for profile names
 */
export type ProfileName = keyof typeof SYNC_PROFILES;

/**
 * Get a configuration profile by name
 */
export function getProfile(name: ProfileName): SyncConfiguration {
  return SYNC_PROFILES[name];
}

/**
 * Validate that a configuration object has all required properties
 */
export function validateConfiguration(config: Partial<SyncConfiguration>): SyncConfiguration {
  // Merge with FULL profile as default to ensure all properties exist
  return {
    ...FULL_SYNC_PROFILE,
    ...config,
    studentFields: {
      ...FULL_SYNC_PROFILE.studentFields,
      ...(config.studentFields || {})
    },
    assignmentFields: {
      ...FULL_SYNC_PROFILE.assignmentFields,
      ...(config.assignmentFields || {})
    },
    processing: {
      ...FULL_SYNC_PROFILE.processing,
      ...(config.processing || {})
    }
  };
}

/**
 * Create a custom configuration by merging a base profile with overrides
 */
export function createCustomConfiguration(
  baseProfile: ProfileName,
  overrides: Partial<SyncConfiguration>
): SyncConfiguration {
  const base = getProfile(baseProfile);
  return validateConfiguration({
    ...base,
    ...overrides,
    studentFields: {
      ...base.studentFields,
      ...(overrides.studentFields || {})
    },
    assignmentFields: {
      ...base.assignmentFields,
      ...(overrides.assignmentFields || {})
    },
    processing: {
      ...base.processing,
      ...(overrides.processing || {})
    }
  });
}

// ============================================================================
// Performance Estimation Utilities
// ============================================================================

/**
 * Estimate the relative performance impact of a configuration
 * Returns a score from 0 (fastest) to 1 (slowest/full sync)
 */
export function estimatePerformanceImpact(config: SyncConfiguration): number {
  let score = 0;
  
  // Major data categories (70% of performance impact)
  if (config.courseInfo) score += 0.05;
  if (config.students) score += 0.25;
  if (config.assignments) score += 0.30;
  if (config.modules) score += 0.15;
  
  // Processing options (30% of performance impact)
  if (config.processing.enhanceWithTimestamps) score += 0.20;
  if (config.processing.resolveQuizAssignments) score += 0.03;
  if (config.processing.includeUnpublished) score += 0.02;
  
  return Math.min(score, 1.0);
}

/**
 * Get a human-readable performance description
 */
export function getPerformanceDescription(config: SyncConfiguration): string {
  const impact = estimatePerformanceImpact(config);
  
  if (impact <= 0.35) return "Very Fast";
  if (impact <= 0.55) return "Fast";
  if (impact <= 0.75) return "Moderate";
  if (impact <= 0.95) return "Slow";
  return "Full Sync";
}
