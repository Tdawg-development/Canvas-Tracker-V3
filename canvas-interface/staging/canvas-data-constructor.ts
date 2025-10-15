/**
 * Canvas Data Constructor
 * 
 * Orchestrates Canvas API calls to build complete staging data objects.
 * Takes a course ID input and returns fully constructed class structures.
 */

import dotenv from 'dotenv';
dotenv.config();

import { CanvasCalls } from '../core/canvas-calls';
import { CanvasCourseStaging, CanvasStudentStaging, CanvasModuleStaging, CanvasAssignmentStaging } from './canvas-staging-data';
import { SyncConfiguration, FULL_SYNC_PROFILE } from '../types/sync-configuration';

export class CanvasDataConstructor {
  private canvasCalls: CanvasCalls;
  private mockCanvasApi?: any;
  private config: SyncConfiguration;

  constructor(options?: { canvasApi?: any; config?: SyncConfiguration }) {
    // Set configuration with default to full sync for backward compatibility
    this.config = options?.config || FULL_SYNC_PROFILE;
    
    if (options?.canvasApi) {
      // Use injected mock for testing
      this.mockCanvasApi = options.canvasApi;
    } else {
      // Use CanvasCalls which handles Canvas configuration internally
      this.canvasCalls = new CanvasCalls();
    }
  }

  /**
   * Get course information (public method for staging)
   */
  async getCourseInfo(courseId: number) {
    return await this.canvasCalls.getCourseInfo(courseId);
  }

  /**
   * Main constructor method - builds complete course staging data
   */
  async constructCourseData(courseId: number): Promise<CanvasCourseStaging> {
    if (this.mockCanvasApi) {
      // Testing mode - use mock API
      return await this.constructCourseDataWithMockApi(courseId);
    }
    
    console.log(`🏗️ Canvas Data Constructor: Building data for course   ${courseId}`);
    console.log('==============================================================');
    
    const startTime = Date.now();
    
    try {
      // Step 1: Get course information (always required)
      console.log('📋 Step 1: Getting course information...');
      const course = await this.getCourseData(courseId);
      
      // Step 2: Get students with enrollment data (conditional)
      let studentsData: any[] = [];
      if (this.config.students) {
        console.log('👥 Step 2: Getting student enrollment data...');
        studentsData = await this.getStudentsData(courseId);
      } else {
        console.log('👥 Step 2: Skipping student data (disabled in config)');
      }
      
      // Step 3: Get modules with assignments (conditional)
      let modulesData: any[] = [];
      if (this.config.assignments || this.config.modules) {
        console.log('📚 Step 3: Getting modules and assignments data...');
        modulesData = await this.getModulesData(courseId);
      } else {
        console.log('📚 Step 3: Skipping modules/assignments (disabled in config)');
      }
      
      // Step 4: Construct the complete staging object
      console.log('🔨 Step 4: Constructing staging data objects...');
      if (studentsData.length > 0) {
        course.addStudents(studentsData, this);
      }
      if (modulesData.length > 0) {
        course.addModules(modulesData);
      }
      
      const processingTime = Date.now() - startTime;
      const apiCalls = this.canvasCalls.getApiStatus().schedulerMetrics.totalRequests;
      
      console.log('\n🎉 CONSTRUCTION COMPLETED!');
      console.log('===========================');
      console.log(`⚡ Processing time: ${processingTime}ms`);
      console.log(`📞 API calls made: ${apiCalls}`);
      console.log(`🎯 Average time per API call: ${(processingTime / apiCalls).toFixed(1)}ms`);
      
      return course;
      
    } catch (error) {
      console.error('💥 Canvas data construction failed:', error);
      throw error;
    }
  }

  /**
   * Get course basic information using CanvasCalls
   */
  private async getCourseData(courseId: number): Promise<CanvasCourseStaging> {
    try {
      const courseInfo = await this.canvasCalls.getCourseInfo(courseId);
      
      if (!courseInfo) {
        throw new Error(`Course ${courseId} not found or not accessible`);
      }
      
      console.log(`   ✅ Course: ${courseInfo.name} (${courseInfo.course_code})`);
      
      // Convert CanvasCalls course info to full course data for staging
      const courseData = {
        id: courseInfo.id,
        name: courseInfo.name,
        course_code: courseInfo.course_code,
        workflow_state: courseInfo.workflow_state,
        start_at: courseInfo.start_at,
        end_at: courseInfo.end_at,
        calendar: { ics: null } // Will be populated if needed
      };
      
      return new CanvasCourseStaging(courseData);
      
    } catch (error) {
      console.error(`   ❌ Failed to get course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get students enrollment data with grades using CanvasCalls
   * Configuration-driven field filtering applied
   */
  private async getStudentsData(courseId: number): Promise<any[]> {
    try {
      // Skip if student data collection is disabled
      if (!this.config.students) {
        console.log(`   ⏭️ Skipping student data collection (disabled in config)`);
        return [];
      }
      
      // Get basic student info from CanvasCalls
      const courseData = await this.canvasCalls.getActiveStudentsAndAssignments(courseId);
      console.log(`   ✅ Found ${courseData.students.length} active students via CanvasCalls`);
      
      // For staging, we need enrollment data with grades, so we'll still need direct API call
      // But we can validate against the CanvasCalls student list
      const validStudentIds = courseData.students.map(s => s.id);
      
      // Build include parameters based on configuration
      const includeParams = [];
      if (this.config.studentFields.scores || this.config.grades) {
        includeParams.push('grades');
      }
      if (this.config.studentFields.basicInfo) {
        includeParams.push('user', 'email');
      }
      
      // Get detailed enrollment data with conditional includes
      const gateway = (this.canvasCalls as any).gateway; // Access gateway through CanvasCalls
      const response = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/enrollments`,
        {
          params: {
            type: ['StudentEnrollment'],
            state: ['active'],
            include: includeParams,
            per_page: 100
          }
        }
      );
      
      const enrollmentData = (response.data as any[]) || [];
      
      // Filter to only students that CanvasCalls identified as active
      const validEnrollments = enrollmentData.filter(enrollment => 
        validStudentIds.includes(enrollment.user_id)
      );
      
      // Apply field-level filtering based on configuration
      const filteredEnrollments = validEnrollments.map(enrollment => {
        const filtered: any = {
          // Always include core enrollment data
          id: enrollment.id,
          user_id: enrollment.user_id,
          course_id: enrollment.course_id,
          type: enrollment.type,
          enrollment_state: enrollment.enrollment_state
        };
        
        // Conditional field inclusion based on configuration
        if (this.config.studentFields.basicInfo && enrollment.user) {
          filtered.user = {
            id: enrollment.user.id,
            name: enrollment.user.name,
            login_id: enrollment.user.login_id,
            email: enrollment.user.email
          };
        }
        
        if (this.config.studentFields.scores && enrollment.grades) {
          filtered.grades = {
            current_score: enrollment.grades.current_score,
            final_score: enrollment.grades.final_score,
            current_grade: enrollment.grades.current_grade,
            final_grade: enrollment.grades.final_grade
          };
        }
        
        if (this.config.studentFields.analytics) {
          filtered.last_activity_at = enrollment.last_activity_at;
          filtered.last_attended_at = enrollment.last_attended_at;
        }
        
        if (this.config.studentFields.enrollmentDetails) {
          filtered.created_at = enrollment.created_at;
          filtered.updated_at = enrollment.updated_at;
          filtered.course_section_id = enrollment.course_section_id;
          filtered.limit_privileges_to_course_section = enrollment.limit_privileges_to_course_section;
        }
        
        return filtered;
      });
      
      console.log(`   ✅ Validated ${filteredEnrollments.length} student enrollments with grades`);
      
      // Show sample student data
      if (filteredEnrollments.length > 0) {
        const sampleStudent = filteredEnrollments[0];
        const sampleName = sampleStudent.user?.name || 'Unknown';
        const sampleScore = sampleStudent.grades?.current_score || 'Not set';
        console.log(`   📈 Sample: ${sampleName} (Score: ${sampleScore})`);
      }
      
      return filteredEnrollments;
      
    } catch (error) {
      console.error(`   ❌ Failed to get students for course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get modules data with assignments using CanvasCalls gateway
   * Configuration-driven collection and processing
   */
  private async getModulesData(courseId: number): Promise<any[]> {
    try {
      // Skip if both assignments and modules are disabled
      if (!this.config.assignments && !this.config.modules) {
        console.log(`   ⏭️ Skipping modules/assignments data collection (disabled in config)`);
        return [];
      }
      
      // Access the gateway through CanvasCalls for consistency
      const gateway = (this.canvasCalls as any).gateway;
      const response = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/modules`,
        {
          params: {
            'include[]': ['items', 'content_details'],
            per_page: 100
          }
        }
      );
      
      const modulesData = (response.data as any[]) || [];
      console.log(`   ✅ Found ${modulesData.length} modules`);
      
      // Get assignment data from CanvasCalls (we already have this from getActiveStudentsAndAssignments)
      const courseData = await this.canvasCalls.getActiveStudentsAndAssignments(courseId);
      const allAssignments = courseData.assignments;
      
      // Create lookup maps for efficient assignment matching
      const assignmentDataMap: { [id: number]: any } = {};
      allAssignments.forEach(assignment => {
        assignmentDataMap[assignment.id] = assignment;
      });
      
      // Also get the full assignment data with more details if needed
      let fullAssignmentData: any[] = [];
      if (this.config.processing.enhanceWithTimestamps || this.config.assignmentFields.timestamps) {
        console.log(`   🔄 Fetching detailed assignment data with timestamps...`);
        const gateway = (this.canvasCalls as any).gateway;
        const assignmentsResponse = await gateway.getClient().requestWithFullResponse(
          `courses/${courseId}/assignments`,
          {
            params: {
              per_page: 100
            }
          }
        );
        fullAssignmentData = (assignmentsResponse.data as any[]) || [];
        
        // Update the lookup map with full data
        fullAssignmentData.forEach(assignment => {
          assignmentDataMap[assignment.id] = assignment;
          // Also map quiz assignments by quiz_id
          if (assignment.quiz_id) {
            assignmentDataMap[`quiz_${assignment.quiz_id}`] = assignment;
          }
        });
      }
      
      // Process and enhance module items
      let totalAssignments = 0;
      let enhancedCount = 0;
      let filteredCount = 0;
      
      modulesData.forEach(module => {
        if (module.items) {
          // Filter and enhance items
          const originalItems = [...module.items];
          module.items = module.items.filter((item: any) => {
            if (item.type !== 'Assignment' && item.type !== 'Quiz') {
              return false; // Remove non-assignment items
            }
            
            totalAssignments++;
            
            // Extract ID for lookup
            let lookupKey: string | number | null = null;
            if (item.type === 'Assignment') {
              lookupKey = this.extractAssignmentIdFromUrl(item.url);
            } else if (item.type === 'Quiz') {
              const quizId = this.extractQuizIdFromUrl(item.url);
              lookupKey = quizId ? `quiz_${quizId}` : null;
            }
            
            // Check if we have assignment data
            const assignmentData = lookupKey ? assignmentDataMap[lookupKey] : null;
            
            // Filter ungraded quizzes if configured
            if (item.type === 'Quiz' && this.config.processing.filterUngradedQuizzes) {
              if (!assignmentData) {
                console.log(`     🗑️ Filtered out ungraded quiz: ${item.title || 'Unknown'}`);
                filteredCount++;
                return false;
              }
            }
            
            // Enhance item with assignment data if available
            if (assignmentData) {
              // Apply field filtering based on configuration
              if (this.config.assignmentFields.basicInfo) {
                item.points_possible = assignmentData.points_possible;
                item.due_at = assignmentData.due_at;
                item.name = assignmentData.name;
              }
              
              if (this.config.assignmentFields.timestamps) {
                item.created_at = assignmentData.created_at;
                item.updated_at = assignmentData.updated_at;
                item.workflow_state = assignmentData.workflow_state;
              }
              
              if (this.config.assignmentFields.submissions) {
                item.submission_types = assignmentData.submission_types;
                item.grading_type = assignmentData.grading_type;
              }
              
              if (this.config.assignmentFields.urls) {
                item.html_url = assignmentData.html_url;
              }
              
              item.assignment_id = typeof lookupKey === 'number' ? lookupKey : assignmentData.id;
              enhancedCount++;
            }
            
            return true; // Keep this item
          });
        }
      });
      
      console.log(`   📏 Total assignments/quizzes found: ${totalAssignments}`);
      console.log(`   🎆 Enhanced ${enhancedCount} items with assignment data`);
      if (filteredCount > 0) {
        console.log(`   🗑️ Filtered out ${filteredCount} ungraded quizzes`);
      }
      
      // Show sample module data
      if (modulesData.length > 0) {
        const sampleModule = modulesData[0];
        const moduleAssignments = sampleModule.items?.filter((item: any) => 
          item.type === 'Assignment' || item.type === 'Quiz'
        ).length || 0;
        console.log(`   📚 Sample: Module "${sampleModule.name}" with ${moduleAssignments} assignments`);
      }
      
      return modulesData;
      
    } catch (error) {
      console.error(`   ❌ Failed to get modules for course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get student assignment analytics data
   * Simple function that makes single API call to Canvas analytics endpoint
   * 
   * INPUT: courseId (number), studentId (number)
   * OUTPUT: Array of assignment objects with status and scores
   * 
   * @param courseId - Canvas course ID
   * @param studentId - Canvas user ID (student)
   * @returns Array of assignment analytics objects
   */
  async getStudentAssignmentAnalytics(courseId: number, studentId: number): Promise<any[]> {
    try {
      // Use CanvasCalls gateway for consistency
      const gateway = (this.canvasCalls as any).gateway;
      const response = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/analytics/users/${studentId}/assignments`,
        {
          params: {
            // Remove fields parameter to get full response
          }
        }
      );
      
      const analyticsData = (response.data as any[]) || [];
      
      // Transform the data to match the expected output structure
      const transformedData = analyticsData.map(item => ({
        assignment_id: item.assignment_id,
        title: item.title, // Include title from actual response
        status: item.status, // "on_time" | "floating" | "late" | "missing" etc.
        submission: {
          score: item.submission?.score || null, // Get score from submission object
          submitted_at: item.submission?.submitted_at || null,
          posted_at: item.submission?.posted_at || null
        },
        points_possible: item.points_possible,
        excused: item.excused
      }));
      
      return transformedData;
      
    } catch (error) {
      console.error(`❌ Failed to get assignment analytics for student ${studentId} in course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get all active courses and build course staging objects
   * Calls the courses endpoint to get all courses connected to the API key
   * Then builds a CanvasCourseStaging object for each course
   * 
   * @returns Array of CanvasCourseStaging objects for all active courses
   */
  async getAllActiveCoursesStaging(): Promise<CanvasCourseStaging[]> {
    console.log('🏫 Getting all active courses from Canvas API...');
    
    try {
      const startTime = Date.now();
      
      // Use CanvasCalls gateway for consistency
      const gateway = (this.canvasCalls as any).gateway;
      const response = await gateway.getClient().requestWithFullResponse(
        'courses',
        {
          params: {
            per_page: 100
          }
        }
      );
      
      const coursesData = (response.data as any[]) || [];
      const responseTime = Date.now() - startTime;
      
      console.log(`✅ Retrieved ${coursesData.length} courses in ${responseTime}ms`);
      
      // Filter for available courses only and build staging objects
      console.log('🔨 Building course staging objects (available courses only)...');
      const courseStaging: CanvasCourseStaging[] = [];
      
      let availableCount = 0;
      let unpublishedCount = 0;
      let otherCount = 0;
      
      coursesData.forEach(courseData => {
        // Count workflow states
        if (courseData.workflow_state === 'available') {
          availableCount++;
          // Build staging object only for available courses
          const courseStagingObj = new CanvasCourseStaging(courseData);
          courseStaging.push(courseStagingObj);
        } else if (courseData.workflow_state === 'unpublished') {
          unpublishedCount++;
        } else {
          otherCount++;
        }
      });
      
      console.log(`📊 Course Summary:`);
      console.log(`   Total Retrieved: ${coursesData.length}`);
      console.log(`   Available: ${availableCount}`);
      console.log(`   Unpublished (filtered out): ${unpublishedCount}`);
      if (otherCount > 0) {
        console.log(`   Other states: ${otherCount}`);
      }
      console.log(`   Active Course Objects Created: ${availableCount}`);
      
      if (availableCount > 0) {
        console.log('\n📋 Sample Courses:');
        courseStaging.slice(0, 3).forEach((course, index) => {
          console.log(`   ${index + 1}. ID: ${course.id} - "${course.name}" (${course.course_code})`);
        });
      }
      
      return courseStaging;
      
    } catch (error) {
      console.error('💥 Failed to get active courses:', error);
      throw error;
    }
  }

  /**
   * Extract assignment ID from Canvas assignment URL
   * URL format: https://canvas.instructure.com/api/v1/courses/{courseId}/assignments/{assignmentId}
   */
  private extractAssignmentIdFromUrl(url: string): number | null {
    try {
      const match = url.match(/\/assignments\/(\d+)/);
      return match ? parseInt(match[1], 10) : null;
    } catch (error) {
      return null;
    }
  }
  
  /**
   * Extract quiz ID from Canvas quiz URL
   * URL format: https://canvas.instructure.com/api/v1/courses/{courseId}/quizzes/{quizId}
   */
  private extractQuizIdFromUrl(url: string): number | null {
    try {
      const match = url.match(/\/quizzes\/(\d+)/);
      return match ? parseInt(match[1], 10) : null;
    } catch (error) {
      return null;
    }
  }
  
  
  /**
   * Get API status for debugging - via CanvasCalls
   */
  getApiStatus() {
    return this.canvasCalls.getApiStatus();
  }

  /**
   * Validate course access before construction - via CanvasCalls
   */
  async validateCourseAccess(courseId: number): Promise<boolean> {
    try {
      const courseInfo = await this.canvasCalls.getCourseInfo(courseId);
      return courseInfo !== null;
    } catch (error) {
      return false;
    }
  }
  
  /**
   * Mock API implementation for testing
   */
  private async constructCourseDataWithMockApi(courseId: number): Promise<CanvasCourseStaging> {
    try {
      // Use mocked dependencies
      const courseData = await this.mockCanvasApi.getCourse(courseId);
      const studentsData = await this.mockCanvasApi.getCourseStudents(courseId);
      const modulesData = await this.mockCanvasApi.getCourseModules(courseId);
      const assignmentsData = await this.mockCanvasApi.getCourseAssignments(courseId);
      const enrollmentsData = await this.mockCanvasApi.getCourseEnrollments(courseId);
      
      // Create course staging object
      const course = new CanvasCourseStaging(courseData);
      
      // Add students (convert to Canvas API enrollment format)
      if (studentsData && studentsData.length > 0) {
        // Convert flat student data to Canvas API enrollment format
        const enrollmentFormat = studentsData.map((student: any) => ({
          id: student.id,
          user_id: student.id,
          created_at: student.enrollment_date || new Date().toISOString(),
          last_activity_at: student.last_activity_at || null,
          grades: {
            current_score: student.current_score,
            final_score: student.final_score
          },
          user: {
            id: student.id,
            name: student.name || 'Unknown Student',
            sortable_name: student.name || 'Unknown Student',
            login_id: student.login_id || `student${student.id}@example.com`
          },
          enrollment_state: student.enrollment_state || 'active'
        }));
        course.students = enrollmentFormat.map((student: any) => new CanvasStudentStaging(student));
      } else if (enrollmentsData && enrollmentsData.length > 0) {
        // Convert enrollment data to student format
        const studentData = enrollmentsData.map((enrollment: any) => ({
          id: enrollment.user_id || enrollment.student_id,
          name: enrollment.name || `Student ${enrollment.user_id}`,
          current_score: enrollment.current_score || 0,
          final_score: enrollment.final_score || 0,
          enrollment_state: enrollment.enrollment_state || 'active'
        }));
        course.students = studentData.map((student: any) => new CanvasStudentStaging(student));
      }
      
      // Add modules
      if (modulesData && modulesData.length > 0) {
        course.modules = modulesData.map((module: any) => {
          const moduleStaging = new CanvasModuleStaging(module);
          
          // Add assignments to this module
          if (assignmentsData && assignmentsData.length > 0) {
            const moduleAssignments = assignmentsData
              .filter((assignment: any) => assignment.module_id === module.id)
              .map((assignment: any) => new CanvasAssignmentStaging(assignment));
            moduleStaging.assignments = moduleAssignments;
          }
          
          return moduleStaging;
        });
      }
      
      return course;
      
    } catch (error) {
      throw error;
    }
  }
}
