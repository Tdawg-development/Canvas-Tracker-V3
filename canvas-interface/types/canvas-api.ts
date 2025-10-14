/**
 * Canvas API Type Definitions
 * 
 * TypeScript interfaces for Canvas API responses and internal data structures
 * to improve type safety and code clarity throughout the Canvas interface.
 */

// ==================== COMMON TYPES ====================

export type CanvasWorkflowState = 'unpublished' | 'available' | 'completed' | 'deleted';
export type EnrollmentState = 'active' | 'inactive' | 'completed' | 'deleted';
export type EnrollmentType = 'StudentEnrollment' | 'TeacherEnrollment' | 'TaEnrollment' | 'DesignerEnrollment' | 'ObserverEnrollment';
export type AssignmentType = 'Assignment' | 'Quiz' | 'DiscussionTopic' | 'ExternalTool';
export type SubmissionStatus = 'submitted' | 'unsubmitted' | 'graded' | 'pending_review';
export type AssignmentStatus = 'on_time' | 'floating' | 'late' | 'missing';

// ==================== CANVAS API RESPONSE INTERFACES ====================

export interface CanvasCourseResponse {
  id: number;
  name: string;
  course_code: string;
  workflow_state: CanvasWorkflowState;
  account_id: number;
  start_at?: string | null;
  end_at?: string | null;
  enrollment_term_id: number;
  is_public: boolean;
  is_public_to_auth_users: boolean;
  public_syllabus: boolean;
  public_syllabus_to_auth: boolean;
  public_description?: string;
  storage_quota_mb: number;
  is_favorite: boolean;
  apply_assignment_group_weights: boolean;
  calendar: {
    ics: string;
  };
  time_zone: string;
  blueprint: boolean;
  template: boolean;
  sis_course_id?: string | null;
  integration_id?: string | null;
  hide_final_grades: boolean;
  workflow_state_transitions?: any;
  restrict_enrollments_to_course_dates: boolean;
  created_at: string;
  updated_at: string;
}

export interface CanvasUserResponse {
  id: number;
  name: string;
  sortable_name: string;
  short_name: string;
  sis_user_id?: string | null;
  integration_id?: string | null;
  sis_import_id?: number | null;
  login_id: string;
  email?: string;
  locale?: string;
  effective_locale?: string;
  time_zone?: string;
  avatar_url?: string;
  enrollments?: CanvasEnrollmentResponse[];
  bio?: string;
  pronunciation?: string;
  created_at: string;
  updated_at: string;
}

export interface CanvasEnrollmentResponse {
  id: number;
  user_id: number;
  course_id: number;
  type: EnrollmentType;
  created_at: string;
  updated_at: string;
  associated_user_id?: number | null;
  start_at?: string | null;
  end_at?: string | null;
  course_section_id: number;
  root_account_id: number;
  limit_privileges_to_course_section: boolean;
  enrollment_state: EnrollmentState;
  role: string;
  role_id: number;
  last_activity_at?: string | null;
  last_attended_at?: string | null;
  total_activity_time: number;
  sis_account_id?: string | null;
  sis_course_id?: string | null;
  course_integration_id?: string | null;
  sis_section_id?: string | null;
  section_integration_id?: string | null;
  sis_user_id?: string | null;
  user_integration_id?: string | null;
  html_url: string;
  grades?: {
    html_url: string;
    current_score?: number | null;
    current_grade?: string | null;
    final_score?: number | null;
    final_grade?: string | null;
    unposted_current_score?: number | null;
    unposted_current_grade?: string | null;
    unposted_final_score?: number | null;
    unposted_final_grade?: string | null;
  };
  user?: CanvasUserResponse;
  override_grade?: string | null;
  override_score?: number | null;
  unposted_current_grade?: string | null;
  unposted_final_grade?: string | null;
  unposted_current_score?: number | null;
  unposted_final_score?: number | null;
}

export interface CanvasModuleResponse {
  id: number;
  workflow_state: CanvasWorkflowState;
  position: number;
  name: string;
  unlock_at?: string | null;
  require_sequential_progress: boolean;
  prerequisite_module_ids: number[];
  items_count: number;
  items_url: string;
  items?: CanvasModuleItemResponse[];
  state?: 'locked' | 'unlocked' | 'started' | 'completed';
  completed_at?: string | null;
  publish_final_grade?: boolean;
  published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CanvasModuleItemResponse {
  id: number;
  module_id: number;
  position: number;
  title: string;
  indent: number;
  type: 'File' | 'Page' | 'Discussion' | 'Assignment' | 'Quiz' | 'SubHeader' | 'ExternalUrl' | 'ExternalTool';
  content_id?: number;
  html_url?: string;
  url?: string;
  page_url?: string;
  external_url?: string;
  new_tab?: boolean;
  completion_requirement?: {
    type: 'must_view' | 'must_contribute' | 'must_submit' | 'must_mark_done' | 'min_score';
    min_score?: number;
    completed?: boolean;
  };
  content_details?: {
    points_possible?: number;
    due_at?: string | null;
    unlock_at?: string | null;
    lock_at?: string | null;
    locked_for_user?: boolean;
    lock_explanation?: string;
    lock_info?: any;
  };
  published: boolean;
  created_at: string;
  updated_at: string;
}

export interface CanvasAssignmentResponse {
  id: number;
  name: string;
  description?: string | null;
  created_at: string;
  updated_at: string;
  due_at?: string | null;
  lock_at?: string | null;
  unlock_at?: string | null;
  has_overrides: boolean;
  all_dates?: any[];
  course_id: number;
  html_url: string;
  submissions_download_url: string;
  assignment_group_id: number;
  due_date_required: boolean;
  allowed_extensions?: string[];
  max_name_length: number;
  turnitin_enabled: boolean;
  vericite_enabled: boolean;
  turnitin_settings?: any;
  grade_group_students_individually: boolean;
  external_tool_tag_attributes?: any;
  peer_reviews: boolean;
  automatic_peer_reviews: boolean;
  peer_review_count: number;
  peer_reviews_assign_at?: string | null;
  intra_group_peer_reviews: boolean;
  group_category_id?: number | null;
  needs_grading_count: number;
  needs_grading_count_by_section?: any[];
  position: number;
  post_to_sis: boolean;
  integration_id?: string | null;
  integration_data?: any;
  points_possible?: number | null;
  submission_types: string[];
  has_submitted_submissions: boolean;
  grading_type: 'pass_fail' | 'percent' | 'letter_grade' | 'gpa_scale' | 'points' | 'not_graded';
  grading_standard_id?: number | null;
  published: boolean;
  unpublishable: boolean;
  only_visible_to_overrides: boolean;
  locked_for_user: boolean;
  lock_info?: any;
  lock_explanation?: string;
  quiz_id?: number;
  anonymous_submissions: boolean;
  discussion_topic?: any;
  freeze_on_copy: boolean;
  frozen: boolean;
  frozen_attributes?: string[];
  submission?: CanvasSubmissionResponse;
  use_rubric_for_grading: boolean;
  rubric_settings?: any;
  rubric?: any[];
  assignment_visibility?: number[];
  overrides?: any[];
  omit_from_final_grade: boolean;
  moderated_grading: boolean;
  grader_count?: number | null;
  final_grader_id?: number | null;
  grader_comments_visible_to_graders: boolean;
  graders_anonymous_to_graders: boolean;
  grader_names_visible_to_final_grader: boolean;
  anonymous_grading: boolean;
  allowed_attempts: number;
  post_manually: boolean;
  score_statistics?: any;
  can_submit: boolean;
  workflow_state: CanvasWorkflowState;
}

export interface CanvasSubmissionResponse {
  id: number;
  user_id: number;
  assignment_id: number;
  submitted_at?: string | null;
  score?: number | null;
  grade?: string | null;
  grade_matches_current_submission: boolean;
  html_url: string;
  preview_url: string;
  body?: string | null;
  url?: string | null;
  submission_type?: string | null;
  workflow_state: SubmissionStatus;
  grade_state?: 'needs_grading' | 'excused' | 'needs_review' | 'graded';
  graded_at?: string | null;
  grader_id?: number | null;
  attempt: number;
  cached_due_date?: string | null;
  excused: boolean;
  late_policy_status?: 'late' | 'missing' | 'extended' | null;
  points_deducted?: number | null;
  grading_period_id?: number | null;
  extra_attempts?: number | null;
  posted_at?: string | null;
  late: boolean;
  missing: boolean;
  seconds_late: number;
  entered_grade?: string | null;
  entered_score?: number | null;
  preview_url_submission_id?: number;
  submission_comments?: any[];
  attachments?: any[];
  created_at: string;
  updated_at: string;
}

export interface CanvasAnalyticsAssignmentResponse {
  assignment_id: number;
  title: string;
  points_possible: number;
  due_at?: string | null;
  unlock_at?: string | null;
  muted: boolean;
  status: AssignmentStatus;
  submission?: {
    score?: number | null;
    submitted_at?: string | null;
    posted_at?: string | null;
    late: boolean;
    missing: boolean;
    excused: boolean;
    workflow_state: SubmissionStatus;
  };
  tardiness_breakdown?: {
    missing: number;
    late: number;
    on_time: number;
    floating: number;
    total: number;
  };
  excused: boolean;
  non_digital_submission: boolean;
}

// ==================== INTERNAL DATA STRUCTURES ====================

export interface ProcessedCourseData {
  id: number;
  name: string;
  course_code: string;
  calendar_ics: string;
  workflow_state: CanvasWorkflowState;
  students: ProcessedStudentData[];
  modules: ProcessedModuleData[];
  created_at: string;
  updated_at: string;
}

export interface ProcessedStudentData {
  id: number;
  user_id: number;
  name: string;
  login_id: string;
  email?: string;
  current_score: number;
  final_score: number;
  enrollment_state: EnrollmentState;
  enrollment_date: string;
  last_activity?: string | null;
  submitted_assignments: ProcessedAssignmentAnalytics[];
  missing_assignments: ProcessedAssignmentAnalytics[];
  created_at: string;
  updated_at: string;
}

export interface ProcessedModuleData {
  id: number;
  name: string;
  position: number;
  published: boolean;
  assignments: ProcessedAssignmentData[];
  workflow_state: CanvasWorkflowState;
  created_at: string;
  updated_at: string;
}

export interface ProcessedAssignmentData {
  id: number;
  title: string;
  type: AssignmentType;
  position: number;
  published: boolean;
  url: string;
  points_possible?: number;
  assignment_type?: string;
  workflow_state?: CanvasWorkflowState;
  content_details?: {
    points_possible?: number;
    due_at?: string | null;
    unlock_at?: string | null;
    lock_at?: string | null;
  };
  created_at?: string;
  updated_at?: string;
}

export interface ProcessedAssignmentAnalytics {
  assignment_id: number;
  title: string;
  status: AssignmentStatus;
  submission: {
    score?: number | null;
    submitted_at?: string | null;
    posted_at?: string | null;
  };
  points_possible: number;
  excused: boolean;
}

// ==================== API GATEWAY INTERFACES ====================

export interface CanvasGatewayConfig {
  baseUrl: string;
  apiKey: string;
  timeout: number;
  retries: number;
}

export interface CanvasApiResponse<T> {
  data: T;
  status: number;
  statusText: string;
  headers: Record<string, string>;
  url: string;
}

export interface CanvasApiError {
  message: string;
  status: number;
  errors?: Array<{
    attribute: string;
    type: string;
    message: string;
  }>;
}

// ==================== STAGING DATA INTERFACES ====================

export interface CourseSummary {
  students_count: number;
  modules_count: number;
  total_assignments: number;
  published_assignments: number;
  total_possible_points: number;
  average_score?: number;
  students_with_missing_assignments: number;
}

export interface StudentAnalyticsOptions {
  includeSubmissions?: boolean;
  includeMissingAssignments?: boolean;
  forceRefresh?: boolean;
}

export interface DataConstructorOptions {
  validateInput?: boolean;
  useCache?: boolean;
  timeoutMs?: number;
  retryAttempts?: number;
}

// ==================== UTILITY TYPES ====================

export type CanvasId = number;
export type CourseId = CanvasId;
export type StudentId = CanvasId;
export type AssignmentId = CanvasId;
export type ModuleId = CanvasId;

export interface TimestampFields {
  created_at: string;
  updated_at: string;
}

export interface CanvasEntity extends TimestampFields {
  id: CanvasId;
  name: string;
}

export interface SyncableEntity extends CanvasEntity {
  last_synced?: string;
}

// ==================== VALIDATION INTERFACES ====================

export interface ValidationResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface CanvasDataValidation {
  validateCourse(data: any): ValidationResult;
  validateStudent(data: any): ValidationResult;
  validateAssignment(data: any): ValidationResult;
  validateModule(data: any): ValidationResult;
}