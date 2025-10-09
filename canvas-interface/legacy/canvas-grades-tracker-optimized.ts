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

interface Student {
  id: number;
  name: string;
}

interface BulkSubmission {
  id: number;
  assignment_id: number;
  user_id: number;
  score: number | null;
  grade: string | null;
  workflow_state: string;
  submitted_at: string | null;
  late: boolean;
  missing: boolean;
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
  is_course_completed: boolean;
}

interface CourseGradeReport {
  course_id: number;
  course_name: string;
  total_assignments: number;
  total_course_points: number;
  assignments: Assignment[];
  students: Student[];
  student_reports: StudentGradeReport[];
  summary: {
    total_students: number;
    students_completed: number;
    students_in_progress: number;
    average_grade: number;
    total_missing_assignments: number;
  };
}

class OptimizedCanvasGradesTracker {
  private gateway: CanvasGatewayHttp;

  constructor(gateway: CanvasGatewayHttp) {
    this.gateway = gateway;
  }

  /**
   * Generate a complete grade report for a course using bulk API calls
   */
  async generateCourseGradeReport(courseId: number): Promise<CourseGradeReport> {
    console.log(`🎯 Generating optimized grade report for course ${courseId}...`);

    // Step 1: Get course info
    console.log('📋 Getting course information...');
    const courseResponse = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
    const course = courseResponse.data as any;
    
    if (!course) {
      throw new Error(`Could not retrieve course ${courseId}`);
    }

    console.log(`✅ Course: ${course.name}`);

    // Step 2: Get ALL assignments and students in parallel (bulk approach)
    console.log('🚀 Getting assignments and students in parallel...');
    const [assignments, students] = await Promise.all([
      this.getAllAssignments(courseId),
      this.getAllStudents(courseId)
    ]);

    const totalCoursePoints = assignments.reduce((sum, assignment) => sum + assignment.points_possible, 0);

    console.log(`✅ Found ${assignments.length} assignments (${totalCoursePoints} total points)`);
    console.log(`✅ Found ${students.length} students`);

    // Step 3: Get ALL submissions for ALL students in bulk using Canvas's bulk submission endpoint
    console.log('📊 Getting ALL student submissions in bulk...');
    const allSubmissions = await this.getAllSubmissionsBulk(courseId);
    
    console.log(`✅ Retrieved ${allSubmissions.length} total submissions from bulk API`);

    // Step 4: Process data efficiently using in-memory operations
    console.log('⚡ Processing grade data (in-memory operations)...');
    const studentReports = this.processStudentGrades(students, assignments, allSubmissions, totalCoursePoints);

    // Step 5: Generate course summary
    const summary = this.generateCourseSummary(studentReports);

    const courseReport: CourseGradeReport = {
      course_id: courseId,
      course_name: course.name,
      total_assignments: assignments.length,
      total_course_points: totalCoursePoints,
      assignments: assignments,
      students: students,
      student_reports: studentReports,
      summary: summary
    };

    return courseReport;
  }

  /**
   * Get ALL submissions for ALL students using Canvas bulk submission API
   * This replaces 1000+ individual API calls with just a few bulk calls
   */
  private async getAllSubmissionsBulk(courseId: number): Promise<BulkSubmission[]> {
    const allSubmissions: BulkSubmission[] = [];
    let page = 1;
    let hasMore = true;

    while (hasMore) {
      try {
        // Use Canvas's bulk submissions endpoint - gets submissions for ALL students
        const response = await this.gateway.getClient().requestWithFullResponse(
          `courses/${courseId}/students/submissions`,
          {
            params: {
              per_page: 100,
              page: page,
              include: ['assignment', 'grade', 'score'],
              student_ids: 'all' // This gets ALL students' submissions
            }
          }
        );

        if (response.data && Array.isArray(response.data)) {
          const pageSubmissions = (response.data as any[]).map(submission => ({
            id: submission.id,
            assignment_id: submission.assignment_id,
            user_id: submission.user_id,
            score: submission.score,
            grade: submission.grade,
            workflow_state: submission.workflow_state,
            submitted_at: submission.submitted_at,
            late: submission.late || false,
            missing: submission.missing || false
          }));

          allSubmissions.push(...pageSubmissions);

          console.log(`   📄 Page ${page}: Retrieved ${pageSubmissions.length} submissions (${allSubmissions.length} total)`);

          // Check if there are more pages
          const linkHeader = response.headers.link;
          hasMore = linkHeader && linkHeader.includes('rel="next"');
          page++;
        } else {
          hasMore = false;
        }
      } catch (error) {
        console.log(`   ⚠️ Error on page ${page}, trying alternative approach:`, error);
        
        // Fallback: Try without student_ids=all parameter
        try {
          const response = await this.gateway.getClient().requestWithFullResponse(
            `courses/${courseId}/students/submissions`,
            {
              params: {
                per_page: 100,
                page: page,
                include: ['assignment', 'grade', 'score']
              }
            }
          );

          if (response.data && Array.isArray(response.data)) {
            const pageSubmissions = (response.data as any[]).map(submission => ({
              id: submission.id,
              assignment_id: submission.assignment_id,
              user_id: submission.user_id,
              score: submission.score,
              grade: submission.grade,
              workflow_state: submission.workflow_state,
              submitted_at: submission.submitted_at,
              late: submission.late || false,
              missing: submission.missing || false
            }));

            allSubmissions.push(...pageSubmissions);
            console.log(`   📄 Page ${page} (fallback): Retrieved ${pageSubmissions.length} submissions`);

            const linkHeader = response.headers.link;
            hasMore = linkHeader && linkHeader.includes('rel="next"');
            page++;
          } else {
            hasMore = false;
          }
        } catch (fallbackError) {
          console.log(`   ❌ Fallback also failed on page ${page}:`, fallbackError);
          hasMore = false;
        }
      }
    }

    return allSubmissions;
  }

  /**
   * Process all grade data using efficient in-memory operations
   * This replaces hundreds of individual API calls with fast data processing
   */
  private processStudentGrades(
    students: Student[],
    assignments: Assignment[],
    allSubmissions: BulkSubmission[],
    totalCoursePoints: number
  ): StudentGradeReport[] {
    // Create lookup maps for efficiency
    const assignmentMap = new Map<number, Assignment>();
    assignments.forEach(assignment => {
      assignmentMap.set(assignment.id, assignment);
    });

    // Group submissions by student ID for efficient processing
    const submissionsByStudent = new Map<number, BulkSubmission[]>();
    allSubmissions.forEach(submission => {
      if (!submissionsByStudent.has(submission.user_id)) {
        submissionsByStudent.set(submission.user_id, []);
      }
      submissionsByStudent.get(submission.user_id)!.push(submission);
    });

    const studentReports: StudentGradeReport[] = [];

    // Process each student efficiently
    students.forEach((student, index) => {
      const studentSubmissions = submissionsByStudent.get(student.id) || [];
      
      // Create set of assignment IDs this student has submissions for
      const submittedAssignmentIds = new Set(studentSubmissions.map(s => s.assignment_id));
      
      const submissions: StudentSubmission[] = [];
      const missingAssignments: MissingAssignment[] = [];
      let totalPointsEarned = 0;

      // Check each assignment for this student
      assignments.forEach(assignment => {
        const studentSubmission = studentSubmissions.find(s => s.assignment_id === assignment.id);
        
        if (studentSubmission && 
            studentSubmission.score !== null && 
            studentSubmission.score !== undefined && 
            studentSubmission.workflow_state === 'graded') {
          
          // Student has a grade - add the points
          totalPointsEarned += studentSubmission.score;
          
          submissions.push({
            assignment_id: assignment.id,
            assignment_name: assignment.name,
            points_possible: assignment.points_possible,
            score: studentSubmission.score,
            grade: studentSubmission.grade,
            workflow_state: studentSubmission.workflow_state,
            submitted_at: studentSubmission.submitted_at,
            late: studentSubmission.late,
            missing: studentSubmission.missing
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
      });

      // Calculate student's grade percentage
      const gradePercentage = totalCoursePoints > 0 ? (totalPointsEarned / totalCoursePoints) * 100 : 0;
      
      // Check if course is completed (no missing assignments)
      const isCourseCompleted = missingAssignments.length === 0;

      const studentReport: StudentGradeReport = {
        student_id: student.id,
        student_name: student.name,
        submissions: submissions,
        missing_assignments: missingAssignments,
        total_points_possible: totalCoursePoints,
        total_points_earned: totalPointsEarned,
        grade_percentage: gradePercentage,
        missing_assignments_count: missingAssignments.length,
        completed_assignments_count: submissions.length,
        is_course_completed: isCourseCompleted
      };

      studentReports.push(studentReport);

      // Progress indicator
      if ((index + 1) % 10 === 0 || index === students.length - 1) {
        const progress = ((index + 1) / students.length * 100).toFixed(1);
        console.log(`   ⚡ Processed ${index + 1}/${students.length} students [${progress}%]`);
      }
    });

    return studentReports;
  }

  /**
   * Get all assignments in a course (with pagination)
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
   * Get all students in a course (with pagination)
   */
  private async getAllStudents(courseId: number): Promise<Student[]> {
    const students: Student[] = [];
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

    console.log('\n📊 Grade Distribution:');
    const gradeBuckets = [
      { range: '90-100%', count: 0, color: '🟢' },
      { range: '80-89%', count: 0, color: '🟡' },
      { range: '70-79%', count: 0, color: '🟠' },
      { range: '60-69%', count: 0, color: '🔴' },
      { range: 'Below 60%', count: 0, color: '⚫' }
    ];

    report.student_reports.forEach(student => {
      if (student.grade_percentage >= 90) gradeBuckets[0].count++;
      else if (student.grade_percentage >= 80) gradeBuckets[1].count++;
      else if (student.grade_percentage >= 70) gradeBuckets[2].count++;
      else if (student.grade_percentage >= 60) gradeBuckets[3].count++;
      else gradeBuckets[4].count++;
    });

    gradeBuckets.forEach(bucket => {
      if (bucket.count > 0) {
        console.log(`   ${bucket.color} ${bucket.range}: ${bucket.count} students`);
      }
    });
  }
}

// Main execution function
async function runOptimizedGradesTracker() {
  console.log('🚀 OPTIMIZED Canvas Course Grades Tracker');
  console.log('==========================================\n');

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
  const tracker = new OptimizedCanvasGradesTracker(gateway);

  try {
    // Target course: JDU 1st Section
    const courseId = 7982015;
    
    const startTime = Date.now();
    const report = await tracker.generateCourseGradeReport(courseId);
    const elapsed = Date.now() - startTime;

    console.log(`\n🎉 OPTIMIZATION SUCCESS!`);
    console.log(`✅ Complete grade report generated in ${elapsed}ms`);
    
    // Print reports
    tracker.printSummaryReport(report);
    
    console.log('\n💡 Want to see detailed student reports? Uncomment the line below:');
    // tracker.printDetailedReport(report);

    // API Performance Summary
    console.log('\n⚡ API PERFORMANCE COMPARISON:');
    const finalStatus = gateway.getApiStatus();
    const oldApproachCalls = 33 * 37 + 3; // Students × Assignments + overhead
    const actualCalls = finalStatus.schedulerMetrics.totalRequests;
    const savings = oldApproachCalls - actualCalls;
    const percentSavings = ((savings / oldApproachCalls) * 100).toFixed(1);
    
    console.log(`   🔴 Old approach: ~${oldApproachCalls} API calls`);
    console.log(`   🟢 Optimized approach: ${actualCalls} API calls`);
    console.log(`   💰 Savings: ${savings} calls (${percentSavings}% reduction)`);
    console.log(`   📈 Speed improvement: ~${Math.round(oldApproachCalls / actualCalls)}x faster`);
    console.log(`   🎯 Rate limit usage: ${((finalStatus.rateLimitStatus.requestsInWindow / finalStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
    console.log(`   ✅ Success rate: ${finalStatus.schedulerMetrics.successRate.toFixed(1)}%`);

    return report;

  } catch (error) {
    console.error('💥 Optimized grades tracking failed:', error);
  }
}

// Run the optimized tracker
runOptimizedGradesTracker().catch(console.error);