/**
 * API Call-Centric Staging Architecture
 * 
 * Organizes Canvas data by API endpoint calls rather than entity types.
 * This aligns better with database ingestion and enables modular rebuilding.
 * Supports configuration-driven selective data collection.
 */

import { SyncConfiguration, FULL_SYNC_PROFILE } from '../types/sync-configuration';

// Base interfaces for API call results
interface ApiCallMetadata {
  endpoint: string;
  timestamp: Date;
  responseTime: number;
  recordCount: number;
  apiCallsUsed: number;
  success: boolean;
  errors?: string[];
}

interface CanvasApiCallResult<T = any> {
  callType: string;
  endpoint: string;
  data: T[];
  metadata: ApiCallMetadata;
}


// Specific API call result types
interface CourseInfoCall extends CanvasApiCallResult {
  callType: 'course_info';
  endpoint: string; // /courses/{id}
  data: [CourseInfoRecord]; // Single course record
}

interface EnrollmentsCall extends CanvasApiCallResult {
  callType: 'enrollments';
  endpoint: string; // /courses/{id}/enrollments
  data: EnrollmentRecord[]; // Array of enrollment records
}

interface AssignmentsCall extends CanvasApiCallResult {
  callType: 'assignments';
  endpoint: string; // /courses/{id}/assignments?per_page=100
  data: AssignmentRecord[]; // Array of assignment records
}

interface ModulesCall extends CanvasApiCallResult {
  callType: 'modules';
  endpoint: string; // /courses/{id}/modules?per_page=100&include[]=items&include[]=content_details
  data: ModuleRecord[]; // Array of module records
}

interface StudentAnalyticsCall extends CanvasApiCallResult {
  callType: 'student_analytics';
  endpoint: string; // /courses/{id}/analytics/users/{student_id}/assignments?per_page=100
  data: StudentAnalyticsRecord[]; // Analytics for one student
  studentId: number;
}

// Raw record types (direct API response structures)
interface CourseInfoRecord {
  id: number;
  name: string;
  course_code: string;
  workflow_state: string;
  start_at: string;
  end_at: string;
  calendar?: { ics?: string };
  created_at: string;
  updated_at: string;
}

interface EnrollmentRecord {
  id: number;
  user_id: number;
  course_id: number;
  created_at: string;
  last_activity_at: string;
  grades?: {
    current_score: number;
    final_score: number;
  };
  user: {
    id: number;
    name: string;
    login_id: string;
    email?: string;
    sortable_name: string;
  };
  enrollment_state: string;
}

interface AssignmentRecord {
  id: number;
  course_id: number;
  name: string;
  points_possible: number;
  workflow_state: string;
  created_at: string;
  updated_at: string;
  due_at?: string;
  assignment_group_id?: number;
}

interface ModuleRecord {
  id: number;
  course_id: number;
  name: string;
  position: number;
  workflow_state: string;
  items?: ModuleItemRecord[];
}

interface ModuleItemRecord {
  id: number;
  module_id: number;
  type: string; // 'Assignment', 'Quiz', etc.
  title: string;
  position: number;
  url: string;
  published: boolean;
  content_details?: {
    points_possible: number;
  };
}

interface StudentAnalyticsRecord {
  assignment_id: number;
  title: string;
  status: string; // 'on_time', 'late', 'missing', etc.
  submission?: {
    score: number;
    submitted_at: string;
    posted_at: string;
  };
  points_possible: number;
  excused: boolean;
}

/**
 * Main data set class that holds all API call results for a course
 * Supports configuration-driven selective data collection
 */
export class CanvasCourseApiDataSet {
  courseId: number;
  config: SyncConfiguration;
  
  // API call results
  courseInfo?: CourseInfoCall;
  enrollments?: EnrollmentsCall;
  assignments?: AssignmentsCall;
  modules?: ModulesCall;
  studentAnalytics: Map<number, StudentAnalyticsCall>; // keyed by student_id
  
  // Metadata
  constructionStartTime: Date;
  constructionEndTime?: Date;
  totalApiCalls: number = 0;
  totalProcessingTime: number = 0;

  constructor(courseId: number, config?: SyncConfiguration) {
    this.courseId = courseId;
    this.config = config || FULL_SYNC_PROFILE;
    this.studentAnalytics = new Map();
    this.constructionStartTime = new Date();
  }

  // ===========================================
  // API CALL COLLECTION METHODS
  // ===========================================
  /**
   * Add course info API call result
   */
  addCourseInfo(data: CourseInfoRecord, metadata: ApiCallMetadata): void {
    this.courseInfo = {
      callType: 'course_info',
      endpoint: metadata.endpoint,
      data: [data],
      metadata
    };
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
  }

  /**
   * Add enrollments API call result
   */
  addEnrollments(data: EnrollmentRecord[], metadata: ApiCallMetadata): void {
    this.enrollments = {
      callType: 'enrollments',
      endpoint: metadata.endpoint,
      data,
      metadata
    };
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
  }

  /**
   * Add assignments API call result
   */
  addAssignments(data: AssignmentRecord[], metadata: ApiCallMetadata): void {
    this.assignments = {
      callType: 'assignments',
      endpoint: metadata.endpoint,
      data,
      metadata
    };
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
  }

  /**
   * Add modules API call result
   */
  addModules(data: ModuleRecord[], metadata: ApiCallMetadata): void {
    this.modules = {
      callType: 'modules',
      endpoint: metadata.endpoint,
      data,
      metadata
    };
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
  }

  /**
   * Add student analytics API call result
   */
  addStudentAnalytics(studentId: number, data: StudentAnalyticsRecord[], metadata: ApiCallMetadata): void {
    this.studentAnalytics.set(studentId, {
      callType: 'student_analytics',
      endpoint: metadata.endpoint,
      data,
      metadata,
      studentId
    });
    this.totalApiCalls += metadata.apiCallsUsed;
    this.totalProcessingTime += metadata.responseTime;
  }

  // ===========================================
  // DATABASE RECONSTRUCTION METHODS
  // ===========================================

  /**
   * Reconstruct course records for database insertion
   */
  reconstructCourses(): DatabaseCourseRecord[] {
    if (!this.courseInfo) {
      return [];
    }

    const courseData = this.courseInfo.data[0];
    return [{
      id: courseData.id,
      name: courseData.name,
      course_code: courseData.course_code,
      calendar_ics: courseData.calendar?.ics || '',
      workflow_state: courseData.workflow_state,
      start_at: courseData.start_at,
      end_at: courseData.end_at,
      created_at: courseData.created_at,
      updated_at: courseData.updated_at,
      last_synced: new Date().toISOString()
    }];
  }

  /**
   * Reconstruct student records for database insertion
   */
  reconstructStudents(): DatabaseStudentRecord[] {
    if (!this.enrollments) {
      return [];
    }

    return this.enrollments.data.map(enrollment => ({
      student_id: enrollment.user_id,
      user_id: enrollment.user_id,
      course_id: enrollment.course_id || this.courseId, // Add course_id for bulk import context
      name: enrollment.user.name,
      login_id: enrollment.user.login_id,
      email: enrollment.user.email || enrollment.email || '', // Check both locations for email
      current_score: enrollment.grades?.current_score || 0,
      final_score: enrollment.grades?.final_score || 0,
      enrollment_date: enrollment.created_at,
      last_activity: enrollment.last_activity_at,
      created_at: enrollment.created_at,
      updated_at: enrollment.updated_at, // Preserve original Canvas timestamp
      last_synced: new Date().toISOString()
    }));
  }

  /**
   * Reconstruct assignment records for database insertion
   */
  reconstructAssignments(): DatabaseAssignmentRecord[] {
    const assignments: DatabaseAssignmentRecord[] = [];

    // Add assignments from direct assignments API call
    if (this.assignments) {
      this.assignments.data.forEach(assignment => {
        assignments.push({
          id: assignment.id,
          course_id: assignment.course_id,
          module_id: 0, // Will be updated when modules are processed
          name: assignment.name,
          points_possible: assignment.points_possible,
          assignment_type: 'Assignment', // Default type
          published: assignment.workflow_state === 'published',
          url: '', // Not available in assignments API
          module_position: null,
          created_at: assignment.created_at,
          updated_at: assignment.updated_at,
          last_synced: new Date().toISOString()
        });
      });
    }

    // Add assignments from modules API call
    if (this.modules) {
      this.modules.data.forEach(module => {
        module.items?.forEach(item => {
          if (item.type === 'Assignment' || item.type === 'Quiz') {
            // Extract item ID from URL (assignments or quizzes)
            let itemId: number | null = null;
            if (item.type === 'Assignment') {
              itemId = this.extractAssignmentIdFromUrl(item.url);
            } else if (item.type === 'Quiz') {
              itemId = this.extractQuizIdFromUrl(item.url);
            }
            
            if (itemId) {
              // Check if we already have this assignment from assignments API
              const existingAssignment = assignments.find(a => a.id === itemId);
              if (existingAssignment) {
                // Update with module information
                existingAssignment.module_id = module.id;
                existingAssignment.module_position = item.position;
                existingAssignment.url = item.url;
                existingAssignment.assignment_type = item.type;
              } else {
                // Create new assignment record from module item
                assignments.push({
                  id: itemId,
                  course_id: this.courseId,
                  module_id: module.id,
                  name: item.title,
                  points_possible: item.content_details?.points_possible || 0,
                  assignment_type: item.type,
                  published: item.published,
                  url: item.url,
                  module_position: item.position,
                  created_at: item.created_at || null, // Preserve Canvas timestamp, null if missing
                  updated_at: item.updated_at || null, // Preserve Canvas timestamp, null if missing
                  last_synced: new Date().toISOString()
                });
              }
            }
          }
        });
      });
    }

    return assignments;
  }

  /**
   * Reconstruct enrollment records for database insertion
   */
  reconstructEnrollments(): DatabaseEnrollmentRecord[] {
    if (!this.enrollments) {
      return [];
    }

    return this.enrollments.data.map(enrollment => ({
      student_id: enrollment.user_id,
      course_id: enrollment.course_id,
      enrollment_date: enrollment.created_at,
      enrollment_status: enrollment.enrollment_state,
      created_at: enrollment.created_at,
      updated_at: enrollment.updated_at, // Preserve original Canvas timestamp
      last_synced: new Date().toISOString()
    }));
  }

  // ===========================================
  // MODULAR REBUILD METHODS
  // ===========================================

  /**
   * Rebuild specific data type by refreshing its API call
   */
  async rebuildCourseInfo(dataConstructor: any): Promise<void> {
    console.log(`🔄 Rebuilding course info for course ${this.courseId}...`);
    const startTime = Date.now();
    
    try {
      const courseData = await dataConstructor.getCourseInfo(this.courseId);
      
      if (courseData) {
        const metadata: ApiCallMetadata = {
          endpoint: `/courses/${this.courseId}`,
          timestamp: new Date(),
          responseTime: Date.now() - startTime,
          recordCount: 1,
          apiCallsUsed: 1,
          success: true
        };
        
        this.addCourseInfo(courseData, metadata);
        console.log(`✅ Course info rebuilt in ${Date.now() - startTime}ms`);
      } else {
        // Course not found - this is handled gracefully
        console.log(`⚠️ Course ${this.courseId} not found or not accessible - handled gracefully`);
        // Don't add any course info, reconstruction will return empty array
      }
    } catch (error) {
      console.error(`❌ Failed to rebuild course info: ${error}`);
      throw error;
    }
  }

  async rebuildEnrollments(dataConstructor: any): Promise<void> {
    // Skip if student data collection is disabled
    if (!this.config.students) {
      console.log(`⏭️ Skipping enrollment rebuild (students disabled in config)`);
      return;
    }
    
    console.log(`🔄 Rebuilding enrollments for course ${this.courseId}...`);
    const startTime = Date.now();
    
    try {
      const enrollmentsData = await dataConstructor.getStudentsData(this.courseId);
      const metadata: ApiCallMetadata = {
        endpoint: `/courses/${this.courseId}/enrollments`,
        timestamp: new Date(),
        responseTime: Date.now() - startTime,
        recordCount: enrollmentsData.length,
        apiCallsUsed: 1,
        success: true
      };
      
      this.addEnrollments(enrollmentsData, metadata);
      console.log(`✅ Enrollments rebuilt: ${enrollmentsData.length} records in ${Date.now() - startTime}ms`);
    } catch (error) {
      console.error(`❌ Failed to rebuild enrollments: ${error}`);
      throw error;
    }
  }

  async rebuildAssignments(dataConstructor: any): Promise<void> {
    // Skip if both assignments and modules are disabled
    if (!this.config.assignments && !this.config.modules) {
      console.log(`⏭️ Skipping assignment rebuild (assignments/modules disabled in config)`);
      return;
    }
    
    console.log(`🔄 Rebuilding assignments for course ${this.courseId}...`);
    const startTime = Date.now();
    
    try {
      const modulesData = await dataConstructor.getModulesData(this.courseId);
      const metadata: ApiCallMetadata = {
        endpoint: `/courses/${this.courseId}/modules`,
        timestamp: new Date(),
        responseTime: Date.now() - startTime,
        recordCount: modulesData.length,
        apiCallsUsed: 1,
        success: true
      };
      
      this.addModules(modulesData, metadata);
      console.log(`✅ Assignments rebuilt from ${modulesData.length} modules in ${Date.now() - startTime}ms`);
    } catch (error) {
      console.error(`❌ Failed to rebuild assignments: ${error}`);
      throw error;
    }
  }

  // ===========================================
  // UTILITY METHODS
  // ===========================================

  private extractAssignmentIdFromUrl(url: string): number | null {
    const match = url.match(/\/assignments\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  private extractQuizIdFromUrl(url: string): number | null {
    const match = url.match(/\/quizzes\/(\d+)/);
    return match ? parseInt(match[1], 10) : null;
  }

  /**
   * Get summary of data collection status
   */
  getCollectionSummary() {
    return {
      courseId: this.courseId,
      hasCompleteCourseInfo: !!this.courseInfo,
      enrollmentCount: this.enrollments?.data.length || 0,
      assignmentCount: this.assignments?.data.length || 0,
      moduleCount: this.modules?.data.length || 0,
      studentAnalyticsCount: this.studentAnalytics.size,
      totalApiCalls: this.totalApiCalls,
      totalProcessingTime: this.totalProcessingTime,
      constructionTime: this.constructionEndTime ? 
        this.constructionEndTime.getTime() - this.constructionStartTime.getTime() : null
    };
  }

  /**
   * Mark construction as complete
   */
  completeConstruction(): void {
    this.constructionEndTime = new Date();
  }
}

// Database record interfaces (what gets sent to database)
interface DatabaseCourseRecord {
  id: number;
  name: string;
  course_code: string;
  calendar_ics: string;
  workflow_state: string;
  start_at: string;
  end_at: string;
  created_at: string;
  updated_at: string;
  last_synced: string;
}

interface DatabaseStudentRecord {
  student_id: number;
  user_id: number;
  name: string;
  login_id: string;
  email: string;
  current_score: number;
  final_score: number;
  enrollment_date: string;
  last_activity: string;
  created_at: string;
  updated_at: string;
  last_synced: string;
}

interface DatabaseAssignmentRecord {
  id: number;
  course_id: number;
  module_id: number;
  name: string;
  points_possible: number;
  assignment_type: string;
  published: boolean;
  url: string;
  module_position: number | null;
  created_at: string;
  updated_at: string;
  last_synced: string;
}

interface DatabaseEnrollmentRecord {
  student_id: number;
  course_id: number;
  enrollment_date: string;
  enrollment_status: string;
  created_at: string;
  updated_at: string;
  last_synced: string;
}

export {
  CanvasCourseApiDataSet,
  CourseInfoCall,
  EnrollmentsCall,
  AssignmentsCall,
  ModulesCall,
  StudentAnalyticsCall,
  DatabaseCourseRecord,
  DatabaseStudentRecord, 
  DatabaseAssignmentRecord,
  DatabaseEnrollmentRecord,
  ApiCallMetadata
};
