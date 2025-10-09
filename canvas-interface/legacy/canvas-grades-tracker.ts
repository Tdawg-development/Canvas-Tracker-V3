// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

// Types for our grading system
interface Assignment {
  id: number;
  name: string;
  points_possible: number;
  due_at: string | null;
  workflow_state: string;
}

interface StudentSubmission {
  assignment_id: number;
  assignment_name: string;
  points_possible: number;
  score: number | null;
  grade: string | null;
  workflow_state: string;
  submitted_at: string | null;
  late: boolean;
  missing: boolean;
}

interface MissingAssignment {
  assignment_id: number;
  assignment_name: string;
  points_possible: number;
  due_at: string | null;
}

interface StudentGradeReport {
  student_id: number;
  student_name: string;
  submissions: StudentSubmission[];
  missing_assignments: MissingAssignment[];
  total_points_possible: number;
  total_points_earned: number;
  grade_percentage: number;
  missing_assignments_count: number;
  completed_assignments_count: number;
  is_course_completed: boolean; // True if no missing assignments
}

interface CourseGradeReport {
  course_id: number;
  course_name: string;
  total_assignments: number;
  total_course_points: number;
  assignments: Assignment[];
  student_reports: StudentGradeReport[];
  summary: {
    total_students: number;
    students_completed: number;
    students_in_progress: number;
    average_grade: number;
    total_missing_assignments: number;
  };
}

class CanvasGradesTracker {
  private gateway: CanvasGatewayHttp;

  constructor(gateway: CanvasGatewayHttp) {
    this.gateway = gateway;
  }

  /**
   * Generate a complete grade report for a course
   */
  async generateCourseGradeReport(courseId: number): Promise<CourseGradeReport> {
    console.log(`🎯 Generating grade report for course ${courseId}...`);

    // Step 1: Get course info
    console.log('📋 Getting course information...');
    const courseResponse = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
    const course = courseResponse.data as any;
    
    if (!course) {
      throw new Error(`Could not retrieve course ${courseId}`);
    }

    console.log(`✅ Course: ${course.name}`);

    // Step 2: Get master list of ALL assignments
    console.log('📚 Getting all assignments (master list)...');
    const assignments = await this.getAllAssignments(courseId);
    const totalCoursePoints = assignments.reduce((sum, assignment) => sum + assignment.points_possible, 0);

    console.log(`✅ Found ${assignments.length} assignments, ${totalCoursePoints} total points`);

    // Step 3: Get all students in the course
    console.log('👥 Getting all students...');
    const students = await this.getAllStudents(courseId);
    console.log(`✅ Found ${students.length} students`);

    // Step 4: For each student, check every assignment
    console.log('🔍 Analyzing grades for each student...');
    const studentReports: StudentGradeReport[] = [];

    for (let i = 0; i < students.length; i++) {
      const student = students[i];
      console.log(`\n   Processing ${i + 1}/${students.length}: ${student.name} (ID: ${student.id})`);
      
      const studentReport = await this.generateStudentGradeReport(
        courseId, 
        student.id, 
        student.name, 
        assignments, 
        totalCoursePoints
      );
      
      studentReports.push(studentReport);
      
      // Progress indicator
      const progress = ((i + 1) / students.length * 100).toFixed(1);
      console.log(`   ✅ ${student.name}: ${studentReport.grade_percentage.toFixed(1)}% (${studentReport.missing_assignments_count} missing) [${progress}%]`);
    }

    // Step 5: Generate course summary
    const summary = this.generateCourseSummary(studentReports);

    const courseReport: CourseGradeReport = {
      course_id: courseId,
      course_name: course.name,
      total_assignments: assignments.length,
      total_course_points: totalCoursePoints,
      assignments: assignments,
      student_reports: studentReports,
      summary: summary
    };

    return courseReport;
  }

  /**
   * Generate grade report for a single student
   */
  private async generateStudentGradeReport(
    courseId: number,
    studentId: number,
    studentName: string,
    assignments: Assignment[],
    totalCoursePoints: number
  ): Promise<StudentGradeReport> {
    const submissions: StudentSubmission[] = [];
    const missingAssignments: MissingAssignment[] = [];
    let totalPointsEarned = 0;

    // Check every assignment for this student
    for (const assignment of assignments) {
      try {
        const submissionResponse = await this.gateway.getClient().requestWithFullResponse(
          `courses/${courseId}/assignments/${assignment.id}/submissions/${studentId}`,
          {
            params: {
              include: ['grade', 'score']
            }
          }
        );

        if (submissionResponse.data) {
          const submission = submissionResponse.data as any;
          
          // Check if student has a grade
          if (submission.score !== null && submission.score !== undefined && submission.workflow_state === 'graded') {
            // Student has a grade - add the points
            totalPointsEarned += submission.score;
            
            submissions.push({
              assignment_id: assignment.id,
              assignment_name: assignment.name,
              points_possible: assignment.points_possible,
              score: submission.score,
              grade: submission.grade,
              workflow_state: submission.workflow_state,
              submitted_at: submission.submitted_at,
              late: submission.late || false,
              missing: submission.missing || false
            });
          } else {
            // Student does not have a grade - add to missing assignments
            missingAssignments.push({
              assignment_id: assignment.id,
              assignment_name: assignment.name,
              points_possible: assignment.points_possible,
              due_at: assignment.due_at
            });
          }
        } else {
          // Could not get submission - consider it missing
          missingAssignments.push({
            assignment_id: assignment.id,
            assignment_name: assignment.name,
            points_possible: assignment.points_possible,
            due_at: assignment.due_at
          });
        }

        // Small delay to be respectful to API
        await new Promise(resolve => setTimeout(resolve, 50));

      } catch (error) {
        // Error getting submission - consider it missing
        missingAssignments.push({
          assignment_id: assignment.id,
          assignment_name: assignment.name,
          points_possible: assignment.points_possible,
          due_at: assignment.due_at
        });
      }
    }

    // Calculate student's grade percentage
    const gradePercentage = totalCoursePoints > 0 ? (totalPointsEarned / totalCoursePoints) * 100 : 0;
    
    // Check if course is completed (no missing assignments)
    const isCourseCompleted = missingAssignments.length === 0;

    return {
      student_id: studentId,
      student_name: studentName,
      submissions: submissions,
      missing_assignments: missingAssignments,
      total_points_possible: totalCoursePoints,
      total_points_earned: totalPointsEarned,
      grade_percentage: gradePercentage,
      missing_assignments_count: missingAssignments.length,
      completed_assignments_count: submissions.length,
      is_course_completed: isCourseCompleted
    };
  }

  /**
   * Get all assignments in a course
   */
  private async getAllAssignments(courseId: number): Promise<Assignment[]> {
    const assignments: Assignment[] = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments`,
        {
          params: {
            per_page: 100,
            page: page
          }
        }
      );

      if (response.data && Array.isArray(response.data)) {
        const pageAssignments = (response.data as any[]).map(assignment => ({
          id: assignment.id,
          name: assignment.name,
          points_possible: assignment.points_possible || 0,
          due_at: assignment.due_at,
          workflow_state: assignment.workflow_state
        }));

        assignments.push(...pageAssignments);

        // Check if there are more pages
        const linkHeader = response.headers.link;
        hasMore = linkHeader && linkHeader.includes('rel="next"');
        page++;
      } else {
        hasMore = false;
      }
    }

    return assignments;
  }

  /**
   * Get all students in a course
   */
  private async getAllStudents(courseId: number): Promise<Array<{id: number, name: string}>> {
    const students: Array<{id: number, name: string}> = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/users`,
        {
          params: {
            enrollment_type: 'student',
            enrollment_state: 'active',
            per_page: 100,
            page: page
          }
        }
      );

      if (response.data && Array.isArray(response.data)) {
        const pageStudents = (response.data as any[]).map(student => ({
          id: student.id,
          name: student.name
        }));

        students.push(...pageStudents);

        // Check if there are more pages
        const linkHeader = response.headers.link;
        hasMore = linkHeader && linkHeader.includes('rel="next"');
        page++;
      } else {
        hasMore = false;
      }
    }

    return students;
  }

  /**
   * Generate course summary statistics
   */
  private generateCourseSummary(studentReports: StudentGradeReport[]) {
    const totalStudents = studentReports.length;
    const studentsCompleted = studentReports.filter(report => report.is_course_completed).length;
    const studentsInProgress = totalStudents - studentsCompleted;
    
    const averageGrade = totalStudents > 0 
      ? studentReports.reduce((sum, report) => sum + report.grade_percentage, 0) / totalStudents
      : 0;
    
    const totalMissingAssignments = studentReports.reduce((sum, report) => sum + report.missing_assignments_count, 0);

    return {
      total_students: totalStudents,
      students_completed: studentsCompleted,
      students_in_progress: studentsInProgress,
      average_grade: averageGrade,
      total_missing_assignments: totalMissingAssignments
    };
  }

  /**
   * Print a detailed report
   */
  printDetailedReport(report: CourseGradeReport) {
    console.log('\n🎓 DETAILED COURSE GRADE REPORT');
    console.log('================================');
    
    console.log(`\n📋 Course: ${report.course_name} (ID: ${report.course_id})`);
    console.log(`📚 Total Assignments: ${report.total_assignments}`);
    console.log(`🎯 Total Course Points: ${report.total_course_points}`);
    
    console.log(`\n📊 Course Summary:`);
    console.log(`   👥 Total Students: ${report.summary.total_students}`);
    console.log(`   ✅ Students Completed: ${report.summary.students_completed}`);
    console.log(`   📝 Students In Progress: ${report.summary.students_in_progress}`);
    console.log(`   📈 Average Grade: ${report.summary.average_grade.toFixed(1)}%`);
    console.log(`   ❌ Total Missing Assignments: ${report.summary.total_missing_assignments}`);

    console.log(`\n👥 INDIVIDUAL STUDENT REPORTS:`);
    console.log('==============================');

    report.student_reports
      .sort((a, b) => b.grade_percentage - a.grade_percentage) // Sort by grade descending
      .forEach((student, index) => {
        const status = student.is_course_completed ? '✅ COMPLETED' : '📝 IN PROGRESS';
        const gradeColor = student.grade_percentage >= 90 ? '🟢' : 
                          student.grade_percentage >= 80 ? '🟡' : 
                          student.grade_percentage >= 70 ? '🟠' : '🔴';
        
        console.log(`\n${index + 1}. ${student.student_name} (ID: ${student.student_id})`);
        console.log(`   ${status} | ${gradeColor} ${student.grade_percentage.toFixed(1)}% (${student.total_points_earned}/${student.total_points_possible} pts)`);
        console.log(`   📝 Completed: ${student.completed_assignments_count} | ❌ Missing: ${student.missing_assignments_count}`);
        
        if (student.missing_assignments.length > 0) {
          console.log(`   Missing Assignments:`);
          student.missing_assignments.slice(0, 5).forEach(assignment => {
            console.log(`     • ${assignment.assignment_name} (${assignment.points_possible} pts)`);
          });
          if (student.missing_assignments.length > 5) {
            console.log(`     ... and ${student.missing_assignments.length - 5} more`);
          }
        }
      });
  }

  /**
   * Print a compact summary report
   */
  printSummaryReport(report: CourseGradeReport) {
    console.log('\n📋 COURSE GRADE SUMMARY');
    console.log('========================');
    
    console.log(`Course: ${report.course_name}`);
    console.log(`Assignments: ${report.total_assignments} (${report.total_course_points} total points)`);
    console.log(`Students: ${report.summary.total_students} total, ${report.summary.students_completed} completed, ${report.summary.students_in_progress} in progress`);
    console.log(`Average Grade: ${report.summary.average_grade.toFixed(1)}%`);
    console.log(`Missing Assignments: ${report.summary.total_missing_assignments} total`);

    console.log('\n🏆 Top Students:');
    report.student_reports
      .sort((a, b) => b.grade_percentage - a.grade_percentage)
      .slice(0, 5)
      .forEach((student, index) => {
        const status = student.is_course_completed ? '✅' : '📝';
        console.log(`   ${index + 1}. ${student.student_name}: ${student.grade_percentage.toFixed(1)}% ${status}`);
      });
  }
}

// Main execution function
async function runGradesTracker() {
  console.log('🎓 Canvas Course Grades Tracker');
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
  const tracker = new CanvasGradesTracker(gateway);

  try {
    // Target course: JDU 1st Section
    const courseId = 7982015;
    
    const startTime = Date.now();
    const report = await tracker.generateCourseGradeReport(courseId);
    const elapsed = Date.now() - startTime;

    console.log(`\n✅ Grade report completed in ${elapsed}ms`);
    
    // Print reports
    tracker.printSummaryReport(report);
    
    console.log('\n Would you like to see the detailed report? [Uncomment the line below]');
    // tracker.printDetailedReport(report);

    // API Performance Summary
    console.log('\n⚡ API Performance:');
    const finalStatus = gateway.getApiStatus();
    console.log(`   Total API calls: ${finalStatus.schedulerMetrics.totalRequests}`);
    console.log(`   Rate limit usage: ${((finalStatus.rateLimitStatus.requestsInWindow / finalStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
    console.log(`   Success rate: ${finalStatus.schedulerMetrics.successRate.toFixed(1)}%`);
    console.log(`   Average response time: ${finalStatus.schedulerMetrics.averageResponseTime.toFixed(0)}ms`);

    return report;

  } catch (error) {
    console.error('💥 Grades tracking failed:', error);
  }
}

// Run the tracker
runGradesTracker().catch(console.error);