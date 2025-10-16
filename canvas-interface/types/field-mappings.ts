/**
 * Canvas Field Interface Definitions
 * 
 * Type-safe field definitions for Canvas entities that eliminate manual field management
 * in staging classes. These interfaces define exactly what fields each entity should have.
 */

// ============================================================================
// Course Field Interface
// ============================================================================

/**
 * Interface defining all possible fields for Canvas Course staging objects
 */
export interface CanvasCourseFields {
  // Required fields
  id: number;
  name: string;
  course_code: string;
  
  // Optional timestamp fields
  created_at?: string;
  start_at?: string;
  end_at?: string;
  
  // Optional state and configuration fields
  workflow_state?: string;
  calendar?: {
    ics?: string;
  };
  
  // Extended course information
  enrollment_term_id?: number;
  grading_standard_id?: number;
  grade_passback_setting?: string;
  public_syllabus?: boolean;
  public_syllabus_to_auth?: boolean;
  
  // Canvas course settings
  default_view?: string;
  syllabus_body?: string;
  course_format?: string;
  restrict_enrollments_to_course_dates?: boolean;
  
  // Term information
  term?: {
    id?: number;
    name?: string;
    start_at?: string;
    end_at?: string;
  };
}

// ============================================================================
// Student Field Interface  
// ============================================================================

/**
 * Interface defining all possible fields for Canvas Student staging objects
 */
export interface CanvasStudentFields {
  // Required enrollment fields
  id: number;
  user_id: number;
  course_id?: number;
  type?: string;
  enrollment_state?: string;
  
  // Optional timestamp fields
  created_at?: string;
  updated_at?: string;
  last_activity_at?: string;
  last_attended_at?: string;
  
  // Grade information
  current_score?: number;
  final_score?: number;
  current_grade?: string;
  final_grade?: string;
  
  // User information
  user?: {
    id: number;
    name: string;
    sortable_name?: string;
    short_name?: string;
    login_id: string;
    email?: string;
    avatar_url?: string;
    pronouns?: string;
    locale?: string;
    effective_locale?: string;
    time_zone?: string;
  };
  
  // Grade details (nested structure from Canvas API)
  grades?: {
    current_score?: number;
    final_score?: number;
    current_grade?: string;
    final_grade?: string;
    override_score?: number;
    override_grade?: string;
    unposted_current_score?: number;
    unposted_final_score?: number;
    unposted_current_grade?: string;
    unposted_final_grade?: string;
  };
  
  // Section and enrollment details
  course_section_id?: number;
  section_integration_id?: string;
  limit_privileges_to_course_section?: boolean;
  
  // Advanced enrollment information
  enrollment_role?: string;
  role_id?: number;
  associated_user_id?: number;
  sis_account_id?: string;
  sis_course_id?: string;
  sis_section_id?: string;
  sis_user_id?: string;
  
  // Canvas-specific fields
  html_url?: string;
  start_at?: string;
  end_at?: string;
  completed_at?: string;
}

// ============================================================================
// Assignment Field Interface
// ============================================================================

/**
 * Interface defining all possible fields for Canvas Assignment staging objects  
 */
export interface CanvasAssignmentFields {
  // Required fields
  id: number;
  title: string;
  position: number;
  published: boolean;
  type: string; // "assignment" || "quiz"
  url: string;
  
  // Content details
  content_details?: {
    points_possible: number;
    due_at?: string;
    lock_at?: string;
    unlock_at?: string;
  };
  
  // Optional timestamp fields
  created_at?: string;
  updated_at?: string;
  
  // Assignment state and configuration
  workflow_state?: string;
  assignment_type?: string;
  
  // Detailed assignment information
  name?: string;
  description?: string;
  due_at?: string;
  lock_at?: string;
  unlock_at?: string;
  points_possible?: number;
  
  // Grading configuration
  grading_type?: string;
  submission_types?: string[];
  has_submitted_submissions?: boolean;
  
  // Assignment settings
  assignment_group_id?: number;
  grade_group_students_individually?: boolean;
  external_tool_tag_attributes?: any;
  peer_reviews?: boolean;
  automatic_peer_reviews?: boolean;
  
  // URLs and external references
  html_url?: string;
  external_tool_attributes?: any;
  
  // Module positioning
  module_id?: number;
  module_item_id?: number;
  assignment_id?: number; // For resolved quiz assignments
  
  // Quiz-specific fields
  quiz_id?: number;
  quiz?: {
    id?: number;
    title?: string;
    description?: string;
    quiz_type?: string;
    assignment_group_id?: number;
    time_limit?: number;
    shuffle_answers?: boolean;
    show_correct_answers?: boolean;
  };
}

// ============================================================================
// Module Field Interface
// ============================================================================

/**
 * Interface defining all possible fields for Canvas Module staging objects
 */
export interface CanvasModuleFields {
  // Required fields
  id: number;
  name: string;
  position: number;
  published: boolean;
  
  // Optional module information
  workflow_state?: string;
  unlock_at?: string;
  require_sequential_progress?: boolean;
  prerequisite_module_ids?: number[];
  items_count?: number;
  items_url?: string;
  
  // Module completion requirements
  completion_requirements?: Array<{
    id: number;
    type: string;
    min_score?: number;
    completed?: boolean;
  }>;
  
  // State information
  state?: string;
  completed_at?: string;
  items?: any[]; // Will contain processed assignment items
}

// ============================================================================
// Composite Entity Interfaces
// ============================================================================

/**
 * Combined interface for complete course staging data
 */
export interface CompleteCourseFields extends CanvasCourseFields {
  students?: CanvasStudentFields[];
  modules?: CanvasModuleFields[];
  assignments?: CanvasAssignmentFields[];
}

/**
 * Interface for field mapping configuration that specifies which fields
 * should be included based on sync configuration
 */
export interface FieldMappingConfig {
  course?: Partial<Record<keyof CanvasCourseFields, boolean>>;
  student?: Partial<Record<keyof CanvasStudentFields, boolean>>;
  assignment?: Partial<Record<keyof CanvasAssignmentFields, boolean>>;
  module?: Partial<Record<keyof CanvasModuleFields, boolean>>;
}