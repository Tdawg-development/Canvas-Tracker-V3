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

export class CanvasDataConstructor {
  private canvasCalls: CanvasCalls;
  private mockCanvasApi?: any;

  constructor(options?: { canvasApi?: any }) {
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
      // Step 1: Get course information
      console.log('📋 Step 1: Getting course information...');
      const course = await this.getCourseData(courseId);
      
      // Step 2: Get students with enrollment data
      console.log('👥 Step 2: Getting student enrollment data...');
      const studentsData = await this.getStudentsData(courseId);
      
      // Step 3: Get modules with assignments
      console.log('📚 Step 3: Getting modules and assignments data...');
      const modulesData = await this.getModulesData(courseId);
      
      // Step 4: Construct the complete staging object
      console.log('🔨 Step 4: Constructing staging data objects...');
      course.addStudents(studentsData, this);
      course.addModules(modulesData);
      
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
   */
  private async getStudentsData(courseId: number): Promise<any[]> {
    try {
      // Get basic student info from CanvasCalls
      const courseData = await this.canvasCalls.getActiveStudentsAndAssignments(courseId);
      console.log(`   ✅ Found ${courseData.students.length} active students via CanvasCalls`);
      
      // For staging, we need enrollment data with grades, so we'll still need direct API call
      // But we can validate against the CanvasCalls student list
      const validStudentIds = courseData.students.map(s => s.id);
      
      // Get detailed enrollment data with grades (still needed for staging)
      const gateway = (this.canvasCalls as any).gateway; // Access gateway through CanvasCalls
      const response = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/enrollments`,
        {
          params: {
            type: ['StudentEnrollment'],
            state: ['active'],
            include: ['grades', 'user', 'email'],
            per_page: 100
          }
        }
      );
      
      const enrollmentData = (response.data as any[]) || [];
      
      // Filter to only students that CanvasCalls identified as active
      const validEnrollments = enrollmentData.filter(enrollment => 
        validStudentIds.includes(enrollment.user_id)
      );
      
      console.log(`   ✅ Validated ${validEnrollments.length} student enrollments with grades`);
      
      // Show sample student data
      if (validEnrollments.length > 0) {
        const sampleStudent = validEnrollments[0];
        console.log(`   📊 Sample: ${sampleStudent.user?.name} (Score: ${sampleStudent.grades?.current_score || 'Not set'})`);
      }
      
      return validEnrollments;
      
    } catch (error) {
      console.error(`   ❌ Failed to get students for course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get modules data with assignments using CanvasCalls gateway
   */
  private async getModulesData(courseId: number): Promise<any[]> {
    try {
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
      
      // Count assignments across all modules and collect assignment IDs
      let totalAssignments = 0;
      const allAssignmentIds: number[] = [];
      
      modulesData.forEach(module => {
        if (module.items) {
          const assignments = module.items.filter((item: any) => 
            item.type === 'Assignment' || item.type === 'Quiz'
          );
          totalAssignments += assignments.length;
          
          // Extract assignment IDs for full data fetch
          assignments.forEach((assignment: any) => {
            // console.log(`     🔗 Assignment URL: ${assignment.url}`);
            let assignmentId: number | null = null;
            
            if (assignment.type === 'Assignment') {
              assignmentId = this.extractAssignmentIdFromUrl(assignment.url);
            } else if (assignment.type === 'Quiz') {
              // For quizzes, we need to check if they have corresponding assignments
              // Ungraded quizzes without assignments should be excluded
              // console.log(`     🧩 Quiz item detected - will check if it's a graded assignment`);
              assignmentId = null; // Will be resolved later in enhancement phase
            }
            
            // console.log(`     🏷️ Extracted ID: ${assignmentId}`);
            if (assignmentId) {
              allAssignmentIds.push(assignmentId);
            } else if (assignment.type === 'Assignment') {
              console.log(`     ⚠️ Failed to extract assignment ID from URL: ${assignment.url}`);
            }
          });
        }
      });
      
      console.log(`   📝 Total assignments/quizzes found: ${totalAssignments}`);
      
      // DEBUGGING: Show assignment IDs extraction
      console.log(`   📈 Total assignment IDs collected: ${allAssignmentIds.length}`);
      if (allAssignmentIds.length > 0) {
        console.log(`   🏷️ First 5 assignment IDs: ${allAssignmentIds.slice(0, 5).join(', ')}`);
      }
      
      // Enhance assignment data with full API details including timestamps
      console.log(`   🔄 Enhancing assignment data with timestamps (including quiz resolution)...`);
      
      try {
        await this.enhanceAssignmentDataWithTimestamps(modulesData, courseId, allAssignmentIds);
        console.log(`   ✅ Assignment data enhanced with Canvas API timestamps`);
        
        // DEBUGGING: Check if first assignment now has timestamps
        const firstModule = modulesData[0];
        if (firstModule && firstModule.items) {
          const firstAssignment = firstModule.items.find((item: any) => 
            item.type === 'Assignment' || item.type === 'Quiz'
          );
          if (firstAssignment) {
            console.log(`   📍 DEBUG: First assignment after enhancement:`);
            console.log(`     Title: ${firstAssignment.title}`);
            console.log(`     created_at: ${firstAssignment.created_at}`);
            console.log(`     updated_at: ${firstAssignment.updated_at}`);
            console.log(`     workflow_state: ${firstAssignment.workflow_state}`);
          }
        }
        
      } catch (error) {
        console.error(`   ⚠️ Enhancement failed:`, error);
        console.error(`   🔥 Error details:`, error.message);
        console.error(`   📄 Stack trace:`, error.stack);
        
        // Continue without enhancement rather than failing completely
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
   * Enhance assignment data in modules with full Canvas API data including timestamps
   * This method fetches ALL assignments for the course and matches them properly with module items
   */
  private async enhanceAssignmentDataWithTimestamps(
    modulesData: any[], 
    courseId: number, 
    assignmentIds: number[]
  ): Promise<void> {
    try {
      console.log(`     🔍 Starting comprehensive assignment enhancement...`);
      
      const gateway = (this.canvasCalls as any).gateway;
      
      // Fetch ALL assignments for the course (this includes quiz assignments with their assignment IDs)
      console.log(`     📦 Fetching ALL assignments from Canvas API...`);
      const assignmentsResponse = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments`,
        {
          params: {
            per_page: 100
          }
        }
      );
      
      const allAssignments = (assignmentsResponse.data as any[]) || [];
      console.log(`     📁 Received ${allAssignments.length} total assignments from API`);
      
      // Index assignments by both assignment ID and quiz ID for easy lookup
      const assignmentData: { [key: number]: any } = {};
      const quizAssignmentMap: { [quizId: number]: any } = {};
      
      allAssignments.forEach((assignment, index) => {
        // Index by assignment ID
        assignmentData[assignment.id] = assignment;
        
        // If this assignment is a quiz, also index by quiz_id
        if (assignment.quiz_id) {
          quizAssignmentMap[assignment.quiz_id] = assignment;
          // console.log(`     🧩 Found quiz assignment: ${assignment.name} (Assignment ID: ${assignment.id}, Quiz ID: ${assignment.quiz_id})`);
        }
        
        // Show sample timestamp data
        if (index === 0) {
          console.log(`     📅 Sample assignment timestamps:`);
          console.log(`       ID: ${assignment.id}, Title: ${assignment.name}`);
          console.log(`       created_at: ${assignment.created_at}`);
          console.log(`       updated_at: ${assignment.updated_at}`);
        }
      });
      
      console.log(`     🔗 Found ${Object.keys(quizAssignmentMap).length} quiz assignments in total`);
      
      // Enhance module assignment data and filter out ungraded quizzes
      let filteredItemsCount = 0;
      let enhancedItemsCount = 0;
      
      modulesData.forEach(module => {
        if (module.items) {
          // Filter items to only include assignments and graded quizzes
          const originalItems = [...module.items];
          module.items = module.items.filter((item: any) => {
            if (item.type === 'Assignment') {
              return true; // Keep all regular assignments
            } else if (item.type === 'Quiz') {
              const quizId = this.extractQuizIdFromUrl(item.url);
              const hasAssignment = quizId && quizAssignmentMap[quizId];
              if (!hasAssignment) {
                console.log(`     🗑️ Filtered out ungraded quiz: ${item.title || 'Unknown'} (Quiz ID: ${quizId})`);
                filteredItemsCount++;
                return false; // Remove ungraded quizzes
              }
              return true; // Keep graded quizzes
            }
            return false; // Remove other types
          });
          
          // Enhance remaining items
          module.items.forEach((item: any) => {
            if (item.type === 'Assignment' || item.type === 'Quiz') {
              let fullData: any = null;
              
              if (item.type === 'Assignment') {
                const assignmentId = this.extractAssignmentIdFromUrl(item.url);
                if (assignmentId && assignmentData[assignmentId]) {
                  fullData = assignmentData[assignmentId];
                  // console.log(`     ✅ Enhanced assignment: ${fullData.name} (ID: ${assignmentId})`);
                }
              } else if (item.type === 'Quiz') {
                const quizId = this.extractQuizIdFromUrl(item.url);
                if (quizId && quizAssignmentMap[quizId]) {
                  fullData = quizAssignmentMap[quizId];
                  // console.log(`     ✅ Enhanced quiz assignment: ${fullData.name} (Quiz ID: ${quizId}, Assignment ID: ${fullData.id})`);
                }
              }
              
              // Apply enhancement if we found matching data
              if (fullData) {
                item.created_at = fullData.created_at;
                item.updated_at = fullData.updated_at;
                item.due_at = fullData.due_at;
                item.lock_at = fullData.lock_at;
                item.unlock_at = fullData.unlock_at;
                item.workflow_state = fullData.workflow_state;
                item.assignment_id = fullData.id; // Always store the assignment ID
                item.is_graded = true; // Mark as graded
                
                // Update points_possible if available
                if (fullData.points_possible !== undefined) {
                  if (!item.content_details) {
                    item.content_details = {};
                  }
                  item.content_details.points_possible = fullData.points_possible;
                }
                enhancedItemsCount++;
              }
            }
          });
        }
      });
      
      console.log(`     🎨 Enhancement complete: ${enhancedItemsCount} items enhanced, ${filteredItemsCount} ungraded quizzes filtered out`);
      
    } catch (error) {
      console.error('   ❌ Failed to enhance assignment data with timestamps:', error);
      // Don't throw error - continue with basic assignment data
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
