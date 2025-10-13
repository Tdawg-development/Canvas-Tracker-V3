// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from '../../src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from '../../src/infrastructure/http/canvas/CanvasTypes';
import { CanvasGradesPuller, GradesPullInputs, StudentGradeResult, GradesPullResult } from './pull-student-grades';

// Database interface types (for future database integration)
interface DatabaseStudentGradeRequest {
  request_id: string;
  course_id: number;
  student_ids: number[];
  assignment_ids: number[];
  requested_at: Date;
  status: 'pending' | 'processing' | 'completed' | 'error';
}

interface DatabaseStudentGradeResponse {
  request_id: string;
  course_id: number;
  results: StudentGradeResult[];
  total_students: number;
  total_assignments: number;
  total_api_calls: number;
  processing_time_ms: number;
  completed_at: Date;
  status: 'completed' | 'error';
  error_message?: string;
}

/**
 * Canvas Calls Module
 * 
 * This module serves as the interface layer between the database and Canvas API.
 * In the future, this will:
 * 1. Receive requests from the database
 * 2. Process them via Canvas API
 * 3. Push results back to the database
 * 
 * Current implementation processes direct inputs for testing and development.
 */
class CanvasCalls {
  private gateway: CanvasGatewayHttp;
  private puller: CanvasGradesPuller;

  constructor() {
    // Initialize Canvas Gateway with environment configuration
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
    this.puller = new CanvasGradesPuller(this.gateway);
  }

  /**
   * Process Student Grades Request
   * 
   * Main function that will eventually be called by database requests.
   * Takes input parameters, processes via Canvas API, and returns structured results.
   */
  async processStudentGradesRequest( /**TAKES COURSE ID, STUDENTID, ASSIGNMENTID --> RETURNS STUDENT GRADES AND MISSING ASSIGNMENTS */
    requestId: string,
    courseId: number,
    studentIds: number[],
    assignmentIds: number[]
  ): Promise<DatabaseStudentGradeResponse> {
    
    console.log(`🎯 Canvas Calls: Processing request ${requestId}`);
    console.log(`   Course: ${courseId}`);
    console.log(`   Students: ${studentIds.length}`);
    console.log(`   Assignments: ${assignmentIds.length}`);

    const startTime = Date.now();

    try {
      // Prepare inputs for the grades puller
      const inputs: GradesPullInputs = {
        courseId,
        studentIds,
        validAssignmentIds: assignmentIds
      };

      // Execute the grades pull
      const result: GradesPullResult = await this.puller.pullStudentGrades(inputs);
      
      const completedAt = new Date();
      const processingTime = Date.now() - startTime;

      // Structure the response for database storage
      const response: DatabaseStudentGradeResponse = {
        request_id: requestId,
        course_id: courseId,
        results: result.students,
        total_students: result.summary.total_students,
        total_assignments: assignmentIds.length,
        total_api_calls: result.summary.total_api_calls,
        processing_time_ms: processingTime,
        completed_at: completedAt,
        status: 'completed'
      };

      console.log(`✅ Canvas Calls: Request ${requestId} completed successfully`);
      console.log(`   Processing time: ${processingTime}ms`);
      console.log(`   API calls: ${result.summary.total_api_calls}`);
      console.log(`   Students processed: ${result.summary.total_students}`);

      return response;

    } catch (error) {
      console.error(`💥 Canvas Calls: Request ${requestId} failed:`, error);
      
      const completedAt = new Date();
      const processingTime = Date.now() - startTime;

      const errorResponse: DatabaseStudentGradeResponse = {
        request_id: requestId,
        course_id: courseId,
        results: [],
        total_students: 0,
        total_assignments: assignmentIds.length,
        total_api_calls: 0,
        processing_time_ms: processingTime,
        completed_at: completedAt,
        status: 'error',
        error_message: error instanceof Error ? error.message : 'Unknown error occurred'
      };

      return errorResponse;
    }
  }

  /**
   * Get Course Information
   * 
   * Utility function to get basic course details.
   * Useful for validating course IDs before processing grade requests.
   */
  async getCourseInfo(courseId: number) {
    try {
      console.log(`📋 Canvas Calls: Getting course info for ${courseId}`);
      
      const response = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
      const course = response.data as any;
      
      if (course) {
        console.log(`✅ Course found: ${course.name}`);
        return {
          id: course.id,
          name: course.name,
          course_code: course.course_code,
          workflow_state: course.workflow_state,
          start_at: course.start_at,
          end_at: course.end_at
        };
      }
      
      return null;
    } catch (error) {
      console.error(`❌ Failed to get course info for ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get Active Students and Assignments
   * 
   * Utility function to get the complete list of active students and assignments
   * for a course. Useful for populating database tables or validating requests.
   */
  async getActiveStudentsAndAssignments(courseId: number) {
    try {
      console.log(`👥📚 Canvas Calls: Getting active students and assignments for course ${courseId}`);

      // Get students
      const studentsResponse = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/users`,
        {
          params: {
            enrollment_type: 'student',
            enrollment_state: 'active',
            per_page: 100
          }
        }
      );

      const students = (studentsResponse.data as any[]) || [];

      // Get assignments and filter to active ones
      const assignmentsResponse = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments`,
        {
          params: {
            per_page: 100
          }
        }
      );

      const allAssignments = (assignmentsResponse.data as any[]) || [];
      
      // Filter to active assignments (same logic as grades tracker)
      const now = new Date();
      const activeAssignments = allAssignments.filter(assignment => {
        if (assignment.workflow_state !== 'published') return false;
        if (assignment.locked_for_user) return false;
        if (assignment.unlock_at && new Date(assignment.unlock_at) > now) return false;
        if (assignment.lock_at && new Date(assignment.lock_at) < now) return false;
        if (assignment.only_visible_to_overrides) return false;
        if (assignment.points_possible <= 0) return false;
        return true;
      });

      console.log(`✅ Found ${students.length} active students`);
      console.log(`✅ Found ${activeAssignments.length} active assignments (${allAssignments.length} total)`);

      return {
        students: students.map(s => ({
          id: s.id,
          name: s.name,
          sis_user_id: s.sis_user_id
        })),
        assignments: activeAssignments.map(a => ({
          id: a.id,
          name: a.name,
          points_possible: a.points_possible,
          due_at: a.due_at
        })),
        summary: {
          total_students: students.length,
          total_assignments: allAssignments.length,
          active_assignments: activeAssignments.length
        }
      };

    } catch (error) {
      console.error(`❌ Failed to get students and assignments for course ${courseId}:`, error);
      throw error;
    }
  }

  /**
   * Get API Status
   * 
   * Utility function to check Canvas API status and rate limit usage.
   */
  getApiStatus() {
    return this.gateway.getApiStatus();
  }

  /**
   * Simulate Database Request Processing (for development/testing)
   * 
   * This function simulates how the system will work when integrated with a database.
   * It creates a mock request and processes it through the full pipeline.
   */
  async simulateDatabaseRequest(courseId: number, maxStudents: number = 10, maxAssignments: number = 15) {
    console.log('\n🔧 Canvas Calls: Simulating Database Request Processing');
    console.log('========================================================');

    try {
      // Step 1: Get available students and assignments (simulates database lookup)
      console.log('\n📋 Step 1: Getting available students and assignments...');
      const courseData = await this.getActiveStudentsAndAssignments(courseId);
      
      // Step 2: Create a mock database request
      const mockRequest: DatabaseStudentGradeRequest = {
        request_id: `req_${Date.now()}`,
        course_id: courseId,
        student_ids: courseData.students.slice(0, maxStudents).map(s => s.id),
        assignment_ids: courseData.assignments.slice(0, maxAssignments).map(a => a.id),
        requested_at: new Date(),
        status: 'pending'
      };

      console.log('\n📝 Step 2: Mock database request created:');
      console.log(`   Request ID: ${mockRequest.request_id}`);
      console.log(`   Students: ${mockRequest.student_ids.length}`);
      console.log(`   Assignments: ${mockRequest.assignment_ids.length}`);

      // Step 3: Process the request
      console.log('\n⚡ Step 3: Processing request through Canvas API...');
      const response = await this.processStudentGradesRequest(
        mockRequest.request_id,
        mockRequest.course_id,
        mockRequest.student_ids,
        mockRequest.assignment_ids
      );

      // Step 4: Display results (simulates database storage)
      console.log('\n💾 Step 4: Results ready for database storage:');
      console.log(`   Request ID: ${response.request_id}`);
      console.log(`   Status: ${response.status}`);
      console.log(`   Students processed: ${response.total_students}`);
      console.log(`   API calls made: ${response.total_api_calls}`);
      console.log(`   Processing time: ${response.processing_time_ms}ms`);
      
      if (response.status === 'completed') {
        console.log('\n🎯 Sample Results:');
        response.results.slice(0, 5).forEach((student, index) => {
          console.log(`   ${index + 1}. ${student.student_name}: ${student.total_points_earned} points, missing ${student.missing_assignment_ids.length} assignments`);
        });
        
        if (response.results.length > 5) {
          console.log(`   ... and ${response.results.length - 5} more students`);
        }
      }

      console.log('\n✅ Simulation Complete! Ready for database integration.');
      return response;

    } catch (error) {
      console.error('\n💥 Simulation failed:', error);
      throw error;
    }
  }
}

// Export the class and types for use in other modules
export { CanvasCalls, DatabaseStudentGradeRequest, DatabaseStudentGradeResponse };

// Demo function for testing
async function demonstrateCanvasCalls() {
  console.log('🚀 Canvas Calls Module Demonstration');
  console.log('====================================\n');

  try {
    const canvasCalls = new CanvasCalls();

    // Demonstrate the simulated database request processing
    await canvasCalls.simulateDatabaseRequest(7982015, 8, 12); // JDU course, 8 students, 12 assignments

    // Show API status
    const apiStatus = canvasCalls.getApiStatus();
    console.log('\n📊 Final API Status:');
    console.log(`   Total requests: ${apiStatus.schedulerMetrics.totalRequests}`);
    console.log(`   Success rate: ${apiStatus.schedulerMetrics.successRate.toFixed(1)}%`);
    console.log(`   Rate limit usage: ${((apiStatus.rateLimitStatus.requestsInWindow / apiStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);

  } catch (error) {
    console.error('💥 Canvas Calls demonstration failed:', error);
  }
}

// Run demonstration if this file is executed directly
if (require.main === module) {
  demonstrateCanvasCalls().catch(console.error);
}