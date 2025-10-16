/**
 * API Field Mapping Configurations
 * 
 * Configuration-driven mapping from sync configuration to Canvas API parameters.
 * Eliminates 70+ lines of conditional API parameter building logic.
 */

import { SyncConfiguration } from '../types/sync-configuration';

// ============================================================================
// API Field Mapping Interface
// ============================================================================

/**
 * Interface for mapping sync configuration paths to API parameters
 */
export interface ApiFieldMapping {
  /** API parameter name to include */
  apiParam: string;
  
  /** Path in SyncConfiguration that enables this parameter */
  configPath: string;
  
  /** Additional API parameters that must be included when this field is enabled */
  dependencies?: string[];
  
  /** Description of what this mapping does */
  description?: string;
}

// ============================================================================
// Student API Field Mappings
// ============================================================================

/**
 * Maps student field configuration to Canvas Enrollments API parameters
 */
export const STUDENT_API_MAPPINGS: ApiFieldMapping[] = [
  {
    apiParam: 'grades',
    configPath: 'studentFields.scores',
    description: 'Include grade information (current_score, final_score)'
  },
  {
    apiParam: 'grades',
    configPath: 'grades',
    description: 'Include grades when general grade collection is enabled'
  },
  {
    apiParam: 'user',
    configPath: 'studentFields.basicInfo',
    description: 'Include basic user information (name, email, login_id)'
  },
  {
    apiParam: 'email',
    configPath: 'studentFields.basicInfo',
    dependencies: ['user'],
    description: 'Include email address (requires user info)'
  },
  {
    apiParam: 'avatar_url',
    configPath: 'studentFields.basicInfo',
    dependencies: ['user'],
    description: 'Include avatar URL (requires user info)'
  },
  {
    apiParam: 'last_activity_at',
    configPath: 'studentFields.analytics',
    description: 'Include last activity timestamp for analytics'
  },
  {
    apiParam: 'last_attended_at',
    configPath: 'studentFields.analytics',
    description: 'Include last attendance timestamp'
  },
  {
    apiParam: 'current_points',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include current points earned'
  },
  {
    apiParam: 'total_points',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include total points possible'
  },
  {
    apiParam: 'unposted_current_score',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include unposted current score'
  },
  {
    apiParam: 'unposted_final_score',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include unposted final score'
  },
  {
    apiParam: 'current_grade',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include current letter grade'
  },
  {
    apiParam: 'final_grade',
    configPath: 'studentFields.scores',
    dependencies: ['grades'],
    description: 'Include final letter grade'
  }
];

// ============================================================================
// Course API Field Mappings
// ============================================================================

/**
 * Maps course field configuration to Canvas Courses API parameters
 */
export const COURSE_API_MAPPINGS: ApiFieldMapping[] = [
  {
    apiParam: 'syllabus_body',
    configPath: 'courseFields.extended',
    description: 'Include course syllabus content'
  },
  {
    apiParam: 'term',
    configPath: 'courseFields.term',
    description: 'Include term information'
  },
  {
    apiParam: 'course_progress',
    configPath: 'courseFields.progress',
    description: 'Include course progress information'
  },
  {
    apiParam: 'storage_quota_mb',
    configPath: 'courseFields.storage',
    description: 'Include storage quota information'
  },
  {
    apiParam: 'permissions',
    configPath: 'courseFields.permissions',
    description: 'Include user permissions for this course'
  },
  {
    apiParam: 'course_image',
    configPath: 'courseFields.image',
    description: 'Include course image/banner'
  },
  {
    apiParam: 'banner_image',
    configPath: 'courseFields.image',
    description: 'Include course banner image'
  },
  {
    apiParam: 'concluded',
    configPath: 'courseFields.state',
    description: 'Include concluded courses in results'
  },
  {
    apiParam: 'teachers',
    configPath: 'courseFields.instructors',
    description: 'Include teacher/instructor information'
  },
  {
    apiParam: 'account',
    configPath: 'courseFields.account',
    description: 'Include parent account information'
  }
];

// ============================================================================
// Assignment API Field Mappings
// ============================================================================

/**
 * Maps assignment field configuration to Canvas Assignments API parameters
 */
export const ASSIGNMENT_API_MAPPINGS: ApiFieldMapping[] = [
  {
    apiParam: 'submission',
    configPath: 'assignmentFields.submissions',
    description: 'Include submission information and types'
  },
  {
    apiParam: 'assignment_visibility',
    configPath: 'assignmentFields.visibility',
    description: 'Include assignment visibility settings'
  },
  {
    apiParam: 'overrides',
    configPath: 'assignmentFields.overrides',
    description: 'Include assignment overrides for different sections/students'
  },
  {
    apiParam: 'all_dates',
    configPath: 'assignmentFields.timestamps',
    description: 'Include all date-related fields (due, lock, unlock)'
  },
  {
    apiParam: 'discussion_topic',
    configPath: 'assignmentFields.discussions',
    description: 'Include discussion topic information for discussion assignments'
  },
  {
    apiParam: 'quiz',
    configPath: 'assignmentFields.quizzes',
    description: 'Include quiz information for quiz assignments'
  },
  {
    apiParam: 'rubric',
    configPath: 'assignmentFields.rubrics',
    description: 'Include rubric information and criteria'
  },
  {
    apiParam: 'rubric_assessment',
    configPath: 'assignmentFields.rubrics',
    dependencies: ['rubric'],
    description: 'Include rubric assessments'
  }
];

// ============================================================================
// Module API Field Mappings  
// ============================================================================

/**
 * Maps module field configuration to Canvas Modules API parameters
 */
export const MODULE_API_MAPPINGS: ApiFieldMapping[] = [
  {
    apiParam: 'items',
    configPath: 'modules',
    description: 'Include module items (assignments, pages, etc.)'
  },
  {
    apiParam: 'content_details',
    configPath: 'assignmentFields.basicInfo',
    dependencies: ['items'],
    description: 'Include content details for module items'
  },
  {
    apiParam: 'completion_requirements',
    configPath: 'moduleFields.completion',
    description: 'Include module completion requirements'
  },
  {
    apiParam: 'prerequisite_module_ids',
    configPath: 'moduleFields.prerequisites',
    description: 'Include prerequisite module information'
  },
  {
    apiParam: 'state',
    configPath: 'moduleFields.state',
    description: 'Include module state information'
  }
];

// ============================================================================
// Specialized Configuration Sets
// ============================================================================

/**
 * Complete mapping set for full data synchronization
 */
export const FULL_SYNC_MAPPINGS = {
  student: STUDENT_API_MAPPINGS,
  course: COURSE_API_MAPPINGS,
  assignment: ASSIGNMENT_API_MAPPINGS,
  module: MODULE_API_MAPPINGS
};

/**
 * Lightweight mapping set for essential data only
 */
export const LIGHTWEIGHT_MAPPINGS = {
  student: STUDENT_API_MAPPINGS.filter(mapping => 
    ['grades', 'user', 'email'].includes(mapping.apiParam)
  ),
  course: COURSE_API_MAPPINGS.filter(mapping => 
    ['term'].includes(mapping.apiParam)
  ),
  assignment: ASSIGNMENT_API_MAPPINGS.filter(mapping => 
    ['all_dates'].includes(mapping.apiParam)
  ),
  module: MODULE_API_MAPPINGS.filter(mapping => 
    ['items', 'content_details'].includes(mapping.apiParam)
  )
};

/**
 * Analytics-focused mapping set
 */
export const ANALYTICS_MAPPINGS = {
  student: STUDENT_API_MAPPINGS.filter(mapping => 
    mapping.configPath.includes('analytics') || mapping.configPath.includes('scores')
  ),
  course: COURSE_API_MAPPINGS,
  assignment: ASSIGNMENT_API_MAPPINGS.filter(mapping => 
    ['submission', 'all_dates', 'overrides'].includes(mapping.apiParam)
  ),
  module: MODULE_API_MAPPINGS
};