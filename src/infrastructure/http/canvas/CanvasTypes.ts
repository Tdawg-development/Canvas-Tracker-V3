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

// Canvas Course - Core curriculum component
export interface CanvasCourse {
  id: number;
  name: string;
  course_code: string;
  workflow_state: 'unpublished' | 'available' | 'completed' | 'deleted';
  account_id: number;
  start_at: string | null;
  end_at: string | null;
  enrollment_term_id: number;
  sis_course_id: string | null;
  sis_import_id: number | null;
  integration_id: string | null;
  grading_standard_id: number | null;
  created_at: string;
  default_view: 'feed' | 'wiki' | 'modules' | 'assignments' | 'syllabus';
  syllabus_body: string | null;
  enrollments_count?: number;
  total_students?: number;
  public_syllabus: boolean;
  public_syllabus_to_auth: boolean;
  storage_quota_mb: number;
  is_public: boolean;
  is_public_to_auth_users: boolean;
  public_description: string | null;
  allow_student_wiki_edits: boolean;
  allow_wiki_comments: boolean;
  allow_student_forum_attachments: boolean;
  open_enrollment: boolean;
  self_enrollment: boolean;
  restrict_enrollments_to_course_dates: boolean;
  time_zone: string;
}

// Canvas Student (User with student enrollment)
export interface CanvasStudent {
  id: number;
  name: string;
  sortable_name: string;
  short_name: string;
  sis_user_id: string | null;
  sis_import_id: number | null;
  integration_id: string | null;
  login_id: string;
  avatar_url: string | null;
  enrollments?: CanvasEnrollment[];
  email?: string;
  locale?: string;
  effective_locale?: string;
  last_login?: string | null;
  time_zone?: string;
}

// Canvas Enrollment - Links students to courses
export interface CanvasEnrollment {
  id: number;
  course_id: number;
  sis_course_id: string | null;
  course_integration_id: string | null;
  course_section_id: number;
  section_integration_id: string | null;
  sis_account_id: string | null;
  sis_section_id: string | null;
  sis_user_id: string | null;
  enrollment_state: 'active' | 'invited' | 'creation_pending' | 'deleted' | 'rejected' | 'completed' | 'inactive';
  limit_privileges_to_course_section: boolean;
  sis_import_id: number | null;
  root_account_id: number;
  type: 'StudentEnrollment' | 'TeacherEnrollment' | 'TaEnrollment' | 'DesignerEnrollment' | 'ObserverEnrollment';
  user_id: number;
  associated_user_id: number | null;
  role: string;
  role_id: number;
  created_at: string;
  updated_at: string;
  start_at: string | null;
  end_at: string | null;
  last_activity_at: string | null;
  last_attended_at: string | null;
  total_activity_time: number;
  html_url: string;
  grades: {
    html_url: string;
    current_score: number | null;
    current_grade: string | null;
    final_score: number | null;
    final_grade: string | null;
  };
  user: CanvasStudent;
  override_grade: string | null;
  override_score: number | null;
  unposted_current_grade: string | null;
  unposted_final_grade: string | null;
  unposted_current_score: number | null;
  unposted_final_score: number | null;
}

// Canvas Assignment - Key tracking component
export interface CanvasAssignment {
  id: number;
  name: string;
  description: string | null;
  created_at: string;
  updated_at: string;
  due_at: string | null;
  lock_at: string | null;
  unlock_at: string | null;
  has_overrides: boolean;
  all_dates?: CanvasAssignmentDate[];
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
  peer_reviews_assign_at: string | null;
  intra_group_peer_reviews: boolean;
  group_category_id: number | null;
  needs_grading_count: number;
  needs_grading_count_by_section?: Array<{
    section_id: string;
    needs_grading_count: number;
  }>;
  position: number;
  post_to_sis: boolean;
  integration_id: string | null;
  integration_data?: any;
  points_possible: number | null;
  submission_types: string[];
  has_submitted_submissions: boolean;
  grading_type: 'pass_fail' | 'percent' | 'letter_grade' | 'gpa_scale' | 'points';
  grading_standard_id: number | null;
  published: boolean;
  unpublishable: boolean;
  only_visible_to_overrides: boolean;
  locked_for_user: boolean;
  lock_info?: any;
  lock_explanation: string | null;
  quiz_id?: number;
  anonymous_submissions: boolean;
  discussion_topic?: any;
  freeze_on_copy: boolean;
  frozen: boolean;
  frozen_attributes?: string[];
  submission?: CanvasSubmission;
  use_rubric_for_grading: boolean;
  rubric_settings?: any;
  rubric?: any;
  assignment_visibility?: number[];
  overrides?: CanvasAssignmentOverride[];
  omit_from_final_grade: boolean;
  hide_in_gradebook: boolean;
  moderated_grading: boolean;
  grader_count: number | null;
  final_grader_id: number | null;
  grader_comments_visible_to_graders: boolean;
  graders_anonymous_to_graders: boolean;
  grader_names_visible_to_final_grader: boolean;
  anonymous_grading: boolean;
  allowed_attempts: number;
  post_manually: boolean;
  score_statistics?: {
    min: number;
    max: number;
    mean: number;
  };
  can_submit: boolean;
}

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

// Canvas Submission - Assignment completion tracking
export interface CanvasSubmission {
  assignment_id: number;
  assignment: CanvasAssignment;
  course: CanvasCourse;
  attempt: number;
  body: string | null;
  grade: string | null;
  grade_matches_current_submission: boolean;
  html_url: string;
  preview_url: string;
  score: number | null;
  submission_comments?: CanvasSubmissionComment[];
  submission_type: string | null;
  submitted_at: string | null;
  url: string | null;
  user_id: number;
  grader_id: number | null;
  graded_at: string | null;
  user: CanvasStudent;
  late: boolean;
  assignment_visible: boolean;
  excused: boolean | null;
  missing: boolean;
  late_policy_status: string | null;
  points_deducted: number | null;
  seconds_late: number;
  workflow_state: 'submitted' | 'unsubmitted' | 'graded' | 'pending_review';
  extra_attempts: number | null;
  anonymous_id: string | null;
  posted_at: string | null;
  read_status: string;
  redo_request: boolean;
}

export interface CanvasSubmissionComment {
  id: number;
  author_id: number;
  author_name: string;
  author: CanvasStudent;
  comment: string;
  created_at: string;
  edited_at: string | null;
  media_comment?: any;
  attachments?: any[];
}

// Canvas API Configuration
export interface CanvasApiConfig {
  baseUrl: string;
  token: string;
  rateLimitRequestsPerHour?: number;
  timeout?: number;
  retryAttempts?: number;
  retryDelay?: number;
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

// Curriculum-specific types (our domain concepts)
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