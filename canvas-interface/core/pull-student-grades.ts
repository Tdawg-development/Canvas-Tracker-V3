// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from '../../src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from '../../src/infrastructure/http/canvas/CanvasTypes';

// Input types
interface GradesPullInputs {
  courseId: number;
  studentIds: number[];
  validAssignmentIds: number[];
}

// Output types
interface StudentGradeResult {
  student_id: number;
  student_name: string;
  total_points_earned: number;
  missing_assignment_ids: number[];
}

interface GradesPullResult {
  course_id: number;
  students: StudentGradeResult[];
  summary: {
    total_students: number;
    total_api_calls: number;
    processing_time_ms: number;
  };
}

class CanvasGradesPuller {
  private gateway: CanvasGatewayHttp;

  constructor(gateway: CanvasGatewayHttp) {
    this.gateway = gateway;
  }

  /**
   * Pull student grades with minimal API calls
   * Uses the most efficient approach: 1 API call per assignment to get all students' submissions
   */
  async pullStudentGrades(inputs: GradesPullInputs): Promise<GradesPullResult> {
    const { courseId, studentIds, validAssignmentIds } = inputs;
    const startTime = Date.now();
    
    console.log(`🎯 Pulling grades for ${studentIds.length} students in course ${courseId}`);
    console.log(`📚 Checking ${validAssignmentIds.length} valid assignments`);
    console.log(`📊 Expected API calls: ${validAssignmentIds.length} (1 per assignment)`);

    // Get all submissions for all valid assignments
    // This is the most efficient approach: 1 call per assignment gets ALL students
    const allSubmissions = await this.getAllSubmissionsForAssignments(courseId, validAssignmentIds);
    
    console.log(`✅ Retrieved submissions from ${validAssignmentIds.length} assignments`);

    // Process student grades efficiently in memory
    const studentResults = await this.processStudentGrades(studentIds, validAssignmentIds, allSubmissions, courseId);

    const processingTime = Date.now() - startTime;
    const apiCalls = this.gateway.getApiStatus().schedulerMetrics.totalRequests;

    return {
      course_id: courseId,
      students: studentResults,
      summary: {
        total_students: studentIds.length,
        total_api_calls: apiCalls,
        processing_time_ms: processingTime
      }
    };
  }

  /**
   * Get submissions for all assignments with minimal API calls
   * 1 call per assignment gets submissions from ALL students
   */
  private async getAllSubmissionsForAssignments(
    courseId: number,
    assignmentIds: number[]
  ): Promise<Map<number, any[]>> {
    const submissionsByAssignment = new Map<number, any[]>();
    
    // Process assignments in batches to be respectful to the API
    const batchSize = 10; // Larger batch size since we're being more efficient
    const batches: number[][] = [];
    
    for (let i = 0; i < assignmentIds.length; i += batchSize) {
      batches.push(assignmentIds.slice(i, i + batchSize));
    }

    console.log(`   Processing ${assignmentIds.length} assignments in ${batches.length} batches...`);

    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      // Process each batch in parallel for maximum efficiency
      const batchPromises = batch.map(assignmentId => 
        this.getAssignmentSubmissions(courseId, assignmentId)
      );
      
      const batchResults = await Promise.all(batchPromises);
      
      // Store results
      batch.forEach((assignmentId, index) => {
        submissionsByAssignment.set(assignmentId, batchResults[index]);
      });
      
      // Progress indicator
      const progress = ((batchIndex + 1) / batches.length * 100).toFixed(0);
      const assignmentsProcessed = (batchIndex + 1) * batchSize;
      console.log(`   ⚡ Batch ${batchIndex + 1}/${batches.length}: ${Math.min(assignmentsProcessed, assignmentIds.length)}/${assignmentIds.length} assignments [${progress}%]`);
      
      // Small delay between batches to be respectful
      if (batchIndex < batches.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 50));
      }
    }

    return submissionsByAssignment;
  }

  /**
   * Get submissions for a single assignment (all students)
   * Only fetches the minimal data needed: user_id, score, workflow_state
   */
  private async getAssignmentSubmissions(courseId: number, assignmentId: number): Promise<any[]> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments/${assignmentId}/submissions`,
        {
          params: {
            per_page: 100, // Get all submissions for this assignment
            // Only include the minimal data we need - no extra fluff
            include: ['score'] // Just score, we'll get user_id and workflow_state by default
          }
        }
      );

      if (response.data && Array.isArray(response.data)) {
        return (response.data as any[]).map(submission => ({
          user_id: submission.user_id,
          score: submission.score,
          workflow_state: submission.workflow_state
        }));
      }
      
      return [];
    } catch (error) {
      console.log(`   ⚠️ Error getting submissions for assignment ${assignmentId}:`, error);
      return [];
    }
  }

  /**
   * Process student grades using efficient in-memory operations
   * No API calls - all data processing
   * Now gets student names for easier verification
   */
  private async processStudentGrades(
    studentIds: number[],
    validAssignmentIds: number[],
    allSubmissions: Map<number, any[]>,
    courseId: number
  ): Promise<StudentGradeResult[]> {
    
    // Get student names for verification
    console.log('👥 Getting student names for verification...');
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
    
    const allStudents = (studentsResponse.data as any[]) || [];
    const studentNameMap = new Map<number, string>();
    allStudents.forEach(student => {
      studentNameMap.set(student.id, student.name);
    });
    
    // Group all submissions by student ID for efficient lookup
    const submissionsByStudent = new Map<number, any[]>();
    
    allSubmissions.forEach((assignmentSubmissions, assignmentId) => {
      assignmentSubmissions.forEach(submission => {
        if (!submissionsByStudent.has(submission.user_id)) {
          submissionsByStudent.set(submission.user_id, []);
        }
        
        // Add assignment ID to the submission for easier processing
        submissionsByStudent.get(submission.user_id)!.push({
          ...submission,
          assignment_id: assignmentId
        });
      });
    });

    console.log(`⚡ Processing grades for ${studentIds.length} students...`);

    // Process each student
    const results: StudentGradeResult[] = studentIds.map((studentId, index) => {
      const studentSubmissions = submissionsByStudent.get(studentId) || [];
      
      // Create lookup map for this student's submissions
      const submissionMap = new Map<number, any>();
      studentSubmissions.forEach(submission => {
        submissionMap.set(submission.assignment_id, submission);
      });
      
      let totalPointsEarned = 0;
      const missingAssignmentIds: number[] = [];
      
      // Check each valid assignment for this student
      validAssignmentIds.forEach(assignmentId => {
        const submission = submissionMap.get(assignmentId);
        
        if (submission && 
            submission.score !== null && 
            submission.score !== undefined && 
            submission.workflow_state === 'graded') {
          // Student has a grade - add the points (rounded for precision)
          totalPointsEarned += Math.round(submission.score * 100) / 100;
        } else {
          // Student is missing this assignment
          missingAssignmentIds.push(assignmentId);
        }
      });

      // Progress indicator every 10 students
      if ((index + 1) % 10 === 0 || index === studentIds.length - 1) {
        const progress = ((index + 1) / studentIds.length * 100).toFixed(0);
        console.log(`   📊 Processed ${index + 1}/${studentIds.length} students [${progress}%]`);
      }

      return {
        student_id: studentId,
        student_name: studentNameMap.get(studentId) || `Unknown Student ${studentId}`,
        total_points_earned: Math.round(totalPointsEarned * 100) / 100, // Round final total
        missing_assignment_ids: missingAssignmentIds
      };
    });

    return results;
  }
}

// Example usage function (for demonstration)
async function exampleUsage() {
  console.log('🚀 Canvas Student Grades Puller');
  console.log('================================\n');

  // Get environment variables
  const canvasUrl = process.env.CANVAS_URL;
  const canvasToken = process.env.CANVAS_TOKEN;

  if (!canvasUrl || !canvasToken) {
    console.error('❌ Error: Missing Canvas configuration');
    console.log('Please set CANVAS_URL and CANVAS_TOKEN environment variables');
    return;
  }

  // Initialize Canvas Gateway
  const config: CanvasApiConfig = {
    baseUrl: canvasUrl,
    token: canvasToken,
    rateLimitRequestsPerHour: 600,
    accountType: 'free',
  };

  const gateway = new CanvasGatewayHttp(config);
  const puller = new CanvasGradesPuller(gateway);

  try {
    console.log('🔍 Getting complete dataset from Canvas...');
    
    // Get ALL students from the course
    const studentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/7982015/users`,
      {
        params: {
          enrollment_type: 'student',
          enrollment_state: 'active',
          per_page: 100
        }
      }
    );
    
    const allStudents = (studentsResponse.data as any[]) || [];
    const allStudentIds = allStudents.map(student => student.id);
    
    // Get ALL assignments and filter to active ones
    const assignmentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/7982015/assignments`,
      {
        params: {
          per_page: 100
        }
      }
    );
    
    const allAssignments = (assignmentsResponse.data as any[]) || [];
    
    // Filter to active assignments (same logic as our tracker)
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
    
    const activeAssignmentIds = activeAssignments.map(a => a.id);
    
    console.log(`✅ Found ${allStudents.length} total students`);
    console.log(`✅ Found ${allAssignments.length} total assignments, ${activeAssignments.length} active`);
    
    // Complete dataset for comprehensive testing
    const inputs: GradesPullInputs = {
      courseId: 7982015,
      studentIds: allStudentIds, // ALL students
      validAssignmentIds: activeAssignmentIds // ALL active assignments
    };

    console.log('📋 Example Inputs:');
    console.log(`   Course ID: ${inputs.courseId}`);
    console.log(`   Student IDs: [${inputs.studentIds.join(', ')}]`);
    console.log(`   Valid Assignment IDs: [${inputs.validAssignmentIds.slice(0, 3).join(', ')}...] (${inputs.validAssignmentIds.length} total)`);
    console.log('');

    const result = await puller.pullStudentGrades(inputs);

    console.log('\n🎉 GRADES PULL COMPLETED!');
    console.log('==========================');
    
    console.log('\n📊 Results:');
    result.students.forEach((student, index) => {
      console.log(`   ${index + 1}. ${student.student_name} (ID: ${student.student_id}):`);
      console.log(`      Total Points Earned: ${student.total_points_earned}`);
      console.log(`      Missing Assignments: [${student.missing_assignment_ids.join(', ')}]`);
      console.log(`      Missing Count: ${student.missing_assignment_ids.length}/${inputs.validAssignmentIds.length}`);
    });

    console.log('\n⚡ Performance Summary:');
    console.log(`   Students processed: ${result.summary.total_students}`);
    console.log(`   API calls made: ${result.summary.total_api_calls}`);
    console.log(`   Processing time: ${result.summary.processing_time_ms}ms`);
    console.log(`   Average time per student: ${(result.summary.processing_time_ms / result.summary.total_students).toFixed(1)}ms`);
    
    // Calculate API efficiency
    const naiveApproach = inputs.studentIds.length * inputs.validAssignmentIds.length;
    const savings = naiveApproach - result.summary.total_api_calls;
    const percentSavings = ((savings / naiveApproach) * 100).toFixed(1);
    
    console.log(`\n💰 API Efficiency:`);
    console.log(`   Naive approach: ${naiveApproach} calls (1 per student per assignment)`);
    console.log(`   Our approach: ${result.summary.total_api_calls} calls (1 per assignment)`);
    console.log(`   Savings: ${savings} calls (${percentSavings}% reduction)`);

    return result;

  } catch (error) {
    console.error('💥 Grades pull failed:', error);
  }
}

// Export the class for use in other modules
export { CanvasGradesPuller, GradesPullInputs, StudentGradeResult, GradesPullResult };

// Run example if this file is executed directly
if (require.main === module) {
  exampleUsage().catch(console.error);
}