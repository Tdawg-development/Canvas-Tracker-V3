/**
 * Canvas Data Constructor
 * 
 * Orchestrates Canvas API calls to build complete staging data objects.
 * Takes a course ID input and returns fully constructed class structures.
 */

import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from '../../src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from '../../src/infrastructure/http/canvas/CanvasTypes';
import { CanvasCourseStaging, CanvasStudentStaging, CanvasModuleStaging, CanvasAssignmentStaging } from './canvas-staging-data';

export class CanvasDataConstructor {
  private gateway: CanvasGatewayHttp;

  constructor() {
    const canvasUrl = process.env.CANVAS_URL;
    const canvasToken = process.env.CANVAS_TOKEN;

    if (!canvasUrl || !canvasToken) {
      throw new Error('Missing Canvas configuration. Please set CANVAS_URL and CANVAS_TOKEN environment variables.');
    }

    const config: CanvasApiConfig = {
      baseUrl: canvasUrl,
      token: canvasToken,
      rateLimitRequestsPerHour: 600,
      accountType: 'free',
    };

    this.gateway = new CanvasGatewayHttp(config);
  }

  /**
   * Main constructor method - builds complete course staging data
   */
  async constructCourseData(courseId: number): Promise<CanvasCourseStaging> {
    console.log(`🏗️ Canvas Data Constructor: Building data for course ${courseId}`);
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
      const apiCalls = this.gateway.getApiStatus().schedulerMetrics.totalRequests;
      
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
   * Get course basic information
   */
  private async getCourseData(courseId: number): Promise<CanvasCourseStaging> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}`,
        {
          params: {
            include: ['calendar']
          }
        }
      );
      
      if (!response.data) {
        throw new Error(`Course ${courseId} not found or not accessible`);
      }
      
      const courseData = response.data as any;
      console.log(`   ✅ Course: ${courseData.name} (${courseData.course_code})`);
      
      return new CanvasCourseStaging(courseData);
      
    } catch (error) {
      console.error(`   ❌ Failed to get course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get students enrollment data with grades
   */
  private async getStudentsData(courseId: number): Promise<any[]> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/enrollments`,
        {
          params: {
            type: ['StudentEnrollment'],
            state: ['active'],
            include: ['grades', 'user'],
            per_page: 100
          }
        }
      );
      
      const studentsData = (response.data as any[]) || [];
      console.log(`   ✅ Found ${studentsData.length} active students`);
      
      // Show sample student data
      if (studentsData.length > 0) {
        const sampleStudent = studentsData[0];
        console.log(`   📊 Sample: ${sampleStudent.user?.name} (Score: ${sampleStudent.grades?.current_score || 'Not set'})`);
      }
      
      return studentsData;
      
    } catch (error) {
      console.error(`   ❌ Failed to get students for course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get modules data with assignments
   */
  private async getModulesData(courseId: number): Promise<any[]> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(
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
      
      // Count assignments across all modules
      let totalAssignments = 0;
      modulesData.forEach(module => {
        if (module.items) {
          const assignments = module.items.filter((item: any) => 
            item.type === 'Assignment' || item.type === 'Quiz'
          );
          totalAssignments += assignments.length;
        }
      });
      
      console.log(`   📝 Total assignments/quizzes found: ${totalAssignments}`);
      
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
      const response = await this.gateway.getClient().requestWithFullResponse(
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
      
      const response = await this.gateway.getClient().requestWithFullResponse(
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
   * Get API status for debugging
   */
  getApiStatus() {
    return this.gateway.getApiStatus();
  }

  /**
   * Validate course access before construction
   */
  async validateCourseAccess(courseId: number): Promise<boolean> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
      return response.data !== null;
    } catch (error) {
      return false;
    }
  }
}