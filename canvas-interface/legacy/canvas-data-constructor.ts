/**
 * Canvas Data Constructor
 * 
 * Orchestrates Canvas API calls to build complete staging data objects.
 * Takes a course ID input and returns fully constructed class structures.
 */

import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';
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
    console.log(`🏗️ Canvas Data Constructor: Building data for course ${courseId}`);\n    console.log('==============================================================');\n    
    const startTime = Date.now();\n    
    try {\n      // Step 1: Get course information\n      console.log('📋 Step 1: Getting course information...');\n      const course = await this.getCourseData(courseId);\n      \n      // Step 2: Get students with enrollment data\n      console.log('👥 Step 2: Getting student enrollment data...');\n      const studentsData = await this.getStudentsData(courseId);\n      \n      // Step 3: Get modules with assignments\n      console.log('📚 Step 3: Getting modules and assignments data...');\n      const modulesData = await this.getModulesData(courseId);\n      \n      // Step 4: Construct the complete staging object\n      console.log('🔨 Step 4: Constructing staging data objects...');\n      course.addStudents(studentsData);\n      course.addModules(modulesData);\n      \n      const processingTime = Date.now() - startTime;\n      const apiCalls = this.gateway.getApiStatus().schedulerMetrics.totalRequests;\n      \n      console.log('\\n🎉 CONSTRUCTION COMPLETED!');\n      console.log('===========================');\n      console.log(`⚡ Processing time: ${processingTime}ms`);\n      console.log(`📞 API calls made: ${apiCalls}`);\n      console.log(`🎯 Average time per API call: ${(processingTime / apiCalls).toFixed(1)}ms`);\n      \n      return course;\n      \n    } catch (error) {\n      console.error('💥 Canvas data construction failed:', error);\n      throw error;\n    }\n  }\n\n  /**\n   * Get course basic information\n   */\n  private async getCourseData(courseId: number): Promise<CanvasCourseStaging> {\n    try {\n      const response = await this.gateway.getClient().requestWithFullResponse(\n        `courses/${courseId}`,\n        {\n          params: {\n            include: ['calendar']\n          }\n        }\n      );\n      \n      if (!response.data) {\n        throw new Error(`Course ${courseId} not found or not accessible`);\n      }\n      \n      const courseData = response.data as any;\n      console.log(`   ✅ Course: ${courseData.name} (${courseData.course_code})`);\n      \n      return new CanvasCourseStaging(courseData);\n      \n    } catch (error) {\n      console.error(`   ❌ Failed to get course ${courseId}:`, error);\n      throw error;\n    }\n  }\n\n  /**\n   * Get students enrollment data with grades\n   */\n  private async getStudentsData(courseId: number): Promise<any[]> {\n    try {\n      const response = await this.gateway.getClient().requestWithFullResponse(\n        `courses/${courseId}/enrollments`,\n        {\n          params: {\n            type: ['StudentEnrollment'],\n            state: ['active'],\n            include: ['grades', 'user'],\n            per_page: 100\n          }\n        }\n      );\n      \n      const studentsData = (response.data as any[]) || [];\n      console.log(`   ✅ Found ${studentsData.length} active students`);\n      \n      // Show sample student data\n      if (studentsData.length > 0) {\n        const sampleStudent = studentsData[0];\n        console.log(`   📊 Sample: ${sampleStudent.user?.name} (Score: ${sampleStudent.grades?.current_score || 'Not set'})`);\n      }\n      \n      return studentsData;\n      \n    } catch (error) {\n      console.error(`   ❌ Failed to get students for course ${courseId}:`, error);\n      throw error;\n    }\n  }\n\n  /**\n   * Get modules data with assignments\n   */\n  private async getModulesData(courseId: number): Promise<any[]> {\n    try {\n      const response = await this.gateway.getClient().requestWithFullResponse(\n        `courses/${courseId}/modules`,\n        {\n          params: {\n            include: ['items', 'content_details'],\n            per_page: 100\n          }\n        }\n      );\n      \n      const modulesData = (response.data as any[]) || [];\n      console.log(`   ✅ Found ${modulesData.length} modules`);\n      \n      // Count assignments across all modules\n      let totalAssignments = 0;\n      modulesData.forEach(module => {\n        if (module.items) {\n          const assignments = module.items.filter((item: any) => \n            item.type === 'Assignment' || item.type === 'Quiz'\n          );\n          totalAssignments += assignments.length;\n        }\n      });\n      \n      console.log(`   📝 Total assignments/quizzes found: ${totalAssignments}`);\n      \n      // Show sample module data\n      if (modulesData.length > 0) {\n        const sampleModule = modulesData[0];\n        const moduleAssignments = sampleModule.items?.filter((item: any) => \n          item.type === 'Assignment' || item.type === 'Quiz'\n        ).length || 0;\n        console.log(`   📚 Sample: Module \"${sampleModule.name}\" with ${moduleAssignments} assignments`);\n      }\n      \n      return modulesData;\n      \n    } catch (error) {\n      console.error(`   ❌ Failed to get modules for course ${courseId}:`, error);\n      throw error;\n    }\n  }\n\n  /**\n   * Get API status for debugging\n   */\n  getApiStatus() {\n    return this.gateway.getApiStatus();\n  }\n\n  /**\n   * Validate course access before construction\n   */\n  async validateCourseAccess(courseId: number): Promise<boolean> {\n    try {\n      const response = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});\n      return response.data !== null;\n    } catch (error) {\n      return false;\n    }\n  }\n}