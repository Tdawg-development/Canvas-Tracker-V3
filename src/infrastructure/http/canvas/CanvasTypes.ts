/**
 * Canvas API Type Definitions
 * Defines the shape of data returned from Canvas API endpoints
 * Focuses on Curriculum core objects: Courses, Students, Assignments
 */

// Base Canvas API response structure
export interface CanvasApiResponse<T> {
  data?: T;
  errors?: CanvasApiError[];
  links?: CanvasApiLinks;
}

export interface CanvasApiError {
  message: string;
  error_code?: string;
}

export interface CanvasApiLinks {
  current?: string;
  next?: string;
  prev?: string;
  first?: string;
  last?: string;
}

// Canvas Course - Core curriculum component (slimmed to essential properties)
export interface CanvasCourse {
  // Core identification
  id: number;
  name: string;
  course_code: string;
  workflow_state: 'unpublished' | 'available' | 'completed' | 'deleted';
  
  // Commonly used properties
  total_students?: number;
  start_at: string | null;
  end_at: string | null;
  
  // Optional properties that may be useful
  account_id?: number;
  enrollment_term_id?: number;
  sis_course_id?: string | null;
  created_at?: string;
  time_zone?: string;
}

// Canvas Student (User with student enrollment) - slimmed to essential properties
export interface CanvasStudent {
  // Core identification
  id: number;
  name: string;
  sortable_name: string;
  login_id: string;
  
  // Optional properties that may be useful
  sis_user_id?: string | null;
  email?: string;
  last_login?: string | null;
  enrollments?: CanvasEnrollment[];
}

// Canvas Enrollment - Links students to courses (slimmed to minimal properties)
// This interface was extremely bloated with 42+ properties, most unused
export interface CanvasEnrollment {
  // Core identification
  id: number;
  course_id: number;
  user_id: number;
  
  // Essential enrollment data
  enrollment_state: 'active' | 'invited' | 'creation_pending' | 'deleted' | 'rejected' | 'completed' | 'inactive';
  type: 'StudentEnrollment' | 'TeacherEnrollment' | 'TaEnrollment' | 'DesignerEnrollment' | 'ObserverEnrollment';
  
  // Grade data (if needed)
  grades?: {
    current_score: number | null;
    final_score: number | null;
    current_grade: string | null;
    final_grade: string | null;
  };
  
  // Optional user reference
  user?: CanvasStudent;
}

// Canvas Assignment - Key tracking component
// Focused CanvasAssignment interface with only properties used in this codebase
// This reduces complexity and improves maintainability while preserving all functionality
export interface CanvasAssignment {
  // Core identification
  id: number;
  name: string;
  course_id: number;
  
  // Points and grading (essential for grade calculations)
  points_possible: number | null;
  
  // Publishing and visibility (used in assignment filtering)
  published: boolean;
  locked_for_user: boolean;
  only_visible_to_overrides: boolean;
  workflow_state?: string; // Added as it's used in filtering
  
  // Date-based filtering
  due_at: string | null;
  lock_at: string | null;
  unlock_at: string | null;
  
  // Optional: commonly referenced properties that may be useful
  description?: string | null;
  html_url?: string;
  assignment_group_id?: number;
  submission?: CanvasSubmission;
}

// If you need the full Canvas Assignment data structure in the future,
// you can always extend this interface or create a CanvasAssignmentFull interface

// Canvas Assignment Due Dates and Overrides
export interface CanvasAssignmentDate {
  id?: number;
  base: boolean;
  title: string;
  due_at: string | null;
  unlock_at: string | null;
  lock_at: string | null;
}

export interface CanvasAssignmentOverride {
  id: number;
  assignment_id: number;
  student_ids?: number[];
  group_id?: number;
  course_section_id?: number;
  title: string;
  due_at: string | null;
  unlock_at: string | null;
  lock_at: string | null;
  all_day: boolean;
  all_day_date: string | null;
}

// Canvas Submission - Assignment completion tracking (slimmed to essential properties)
export interface CanvasSubmission {
  // Core identification
  assignment_id: number;
  user_id: number;
  
  // Grade data (essential for tracking)
  score: number | null;
  grade: string | null;
  workflow_state: 'submitted' | 'unsubmitted' | 'graded' | 'pending_review';
  
  // Submission status (essential for tracking)
  submitted_at: string | null;
  late: boolean;
  missing: boolean;
  excused: boolean | null;
  
  // Optional properties that may be useful
  graded_at?: string | null;
  grader_id?: number | null;
  assignment?: CanvasAssignment;
  user?: CanvasStudent;
  submission_comments?: CanvasSubmissionComment[];
}

// Canvas Submission Comment - rarely used, kept minimal
export interface CanvasSubmissionComment {
  id: number;
  author_id: number;
  author_name: string;
  comment: string;
  created_at: string;
  // Simplified - removed rarely used properties
}

// Canvas API Configuration
export interface CanvasApiConfig {
  baseUrl: string;
  token: string;
  rateLimitRequestsPerHour?: number;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
  // Canvas Free specific settings
  accountType?: 'free' | 'paid' | 'enterprise';
  maxConcurrentRequests?: number;
  batchSizeLimit?: number;
  requiresPolling?: boolean;
}

// Canvas API Request Options
export interface CanvasApiRequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  params?: Record<string, string | number | boolean>;
  headers?: Record<string, string>;
  timeout?: number;
  includeEnrollments?: boolean;
  includeSubmissions?: boolean;
  perPage?: number;
  page?: number;
}

// =============================================================================
// DOMAIN-SPECIFIC TYPES (Application Layer)
// =============================================================================
// Note: These are not Canvas API types, consider moving to domain layer

export interface CurriculumConfig {
  id: string;
  name: string;
  courseIds: number[];
  syncSettings: {
    syncCourses: boolean;
    syncStudents: boolean;
    syncAssignments: boolean;
    syncSubmissions: boolean;
    syncInterval: number; // minutes
  };
}

export interface CurriculumSyncStatus {
  curriculumId: string;
  lastSyncAt: string | null;
  lastSuccessfulSyncAt: string | null;
  syncInProgress: boolean;
  errors: string[];
  coursesCount: number;
  studentsCount: number;
  assignmentsCount: number;
}

// =============================================================================
// UNUSED/RARELY USED INTERFACES (Consider removal)
// =============================================================================
// These interfaces are either unused or only referenced as optional properties:
// - CanvasAssignmentDate: Only used as optional property in CanvasAssignment
// - CanvasAssignmentOverride: Only used as optional property in CanvasAssignment
// They are kept for completeness but could be removed if never actually used.
