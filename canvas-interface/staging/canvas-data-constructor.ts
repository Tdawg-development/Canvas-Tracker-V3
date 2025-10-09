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
      course.addStudents(studentsData);
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