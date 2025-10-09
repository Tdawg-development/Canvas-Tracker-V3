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
  unlock_at: string | null;
  lock_at: string | null;
  workflow_state: string;
  published: boolean;
  only_visible_to_overrides: boolean;
  locked_for_user: boolean;
}

interface Student {
  id: number;
  name: string;
}

interface AssignmentSubmission {
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

interface StudentMissingAssignments {
  student_id: number;
  missing_assignment_ids: number[];
}

interface StudentGradeReport {
  student_id: number;
  student_name: string;
  submissions: StudentSubmission[];
  missing_assignments: MissingAssignment[];
  missing_assignment_ids: number[]; // List of missing assignment IDs
  total_points_possible: number;
  total_points_earned: number;
  grade_percentage: number; // Keep for calculations but focus on points
  missing_assignments_count: number;
  completed_assignments_count: number;
  is_course_completed: boolean;
}

interface CourseGradeReport {
  course_id: number;
  course_name: string;
  total_assignments: number;
  total_course_points: number;
  active_assignments: number; // Count of non-locked/closed assignments
  active_course_points: number; // Points from non-locked/closed assignments only
  assignments: Assignment[];
  active_assignments_list: Assignment[]; // Only the active assignments
  students: Student[];
  student_reports: StudentGradeReport[];
  summary: {
    total_students: number;
    students_completed: number;
    students_in_progress: number;
    average_points: number; // Average points earned (not percentage)
    total_missing_assignments: number;
  };
}

class FixedCanvasGradesTracker {
  private gateway: CanvasGatewayHttp;

  constructor(gateway: CanvasGatewayHttp) {
    this.gateway = gateway;
  }

  /**
   * Generate a complete grade report for a course using optimized per-assignment API calls
   */
  async generateCourseGradeReport(courseId: number): Promise<CourseGradeReport> {
    console.log(`🎯 Generating FIXED optimized grade report for course ${courseId}...`);

    // Step 1: Get course info
    console.log('📋 Getting course information...');
    const courseResponse = await this.gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
    const course = courseResponse.data as any;
    
    if (!course) {
      throw new Error(`Could not retrieve course ${courseId}`);
    }

    console.log(`✅ Course: ${course.name}`);

    // Step 2: Get ALL assignments and students in parallel
    console.log('🚀 Getting assignments and students in parallel...');
    const [assignments, students] = await Promise.all([
      this.getAllAssignments(courseId),
      this.getAllStudents(courseId)
    ]);

    // Filter out locked or closed assignments
    // Canvas assignment workflow states: 'published', 'unpublished', 'deleted'
    // But we also need to check for locked assignments via other means
    console.log('\n🔍 Analyzing assignment properties for programmatic filtering...');
    
    // Analyze all available assignment properties
    console.log('   Assignment property analysis:');
    
    const now = new Date();
    let lockedCount = 0;
    let unlockedCount = 0;
    let futureUnlockCount = 0;
    let pastLockCount = 0;
    let restrictedCount = 0;
    let zeroPointCount = 0;
    
    assignments.forEach(assignment => {
      // Check various locking conditions
      if (assignment.locked_for_user) {
        lockedCount++;
      } else if (assignment.unlock_at && new Date(assignment.unlock_at) > now) {
        futureUnlockCount++;
      } else if (assignment.lock_at && new Date(assignment.lock_at) < now) {
        pastLockCount++;
      } else if (assignment.only_visible_to_overrides) {
        restrictedCount++;
      } else if (assignment.points_possible <= 0) {
        zeroPointCount++;
      } else if (assignment.workflow_state === 'published') {
        unlockedCount++;
      }
    });
    
    console.log(`\n   📊 Locking Summary:`);
    console.log(`     ✅ Available assignments: ${unlockedCount}`);
    console.log(`     🔒 Locked for user: ${lockedCount}`);
    console.log(`     ⏰ Future unlock date: ${futureUnlockCount}`);
    console.log(`     ⏱ Past lock date: ${pastLockCount}`);
    console.log(`     🔐 Restricted visibility: ${restrictedCount}`);
    console.log(`     📝 0-point assignments: ${zeroPointCount}`);
    
    // Filter assignments programmatically based on Canvas properties
    const activeAssignments = assignments.filter(assignment => {
      // Must be published
      if (assignment.workflow_state !== 'published') return false;
      
      // Must not be locked for user
      if (assignment.locked_for_user) return false;
      
      // Must not have a future unlock date
      if (assignment.unlock_at && new Date(assignment.unlock_at) > now) return false;
      
      // Must not be past a lock date
      if (assignment.lock_at && new Date(assignment.lock_at) < now) return false;
      
      // Must not be restricted to overrides only
      if (assignment.only_visible_to_overrides) return false;
      
      // Must have points (filter out 0-point assignments)
      if (assignment.points_possible <= 0) return false;
      
      return true;
    });
    
    const activeTotal = activeAssignments.reduce((sum, a) => sum + a.points_possible, 0);
    console.log(`\n   ✅ Programmatically filtered assignments: ${activeAssignments.length} active, ${activeTotal} points`);
    
    // Show which assignments were filtered out
    const filteredOut = assignments.filter(a => !activeAssignments.includes(a));
    if (filteredOut.length > 0) {
      console.log(`   📝 Filtered out assignments:`);
      filteredOut.forEach(assignment => {
        let reason = '';
        if (assignment.workflow_state !== 'published') reason = `not published (${assignment.workflow_state})`;
        else if (assignment.locked_for_user) reason = 'locked for user';
        else if (assignment.unlock_at && new Date(assignment.unlock_at) > now) reason = 'future unlock date';
        else if (assignment.lock_at && new Date(assignment.lock_at) < now) reason = 'past lock date';
        else if (assignment.only_visible_to_overrides) reason = 'restricted visibility';
        else if (assignment.points_possible <= 0) reason = '0 points (informational only)';
        
        console.log(`     • ${assignment.name} (${assignment.points_possible} pts) - ${reason}`);
      });
    }
    
    const totalCoursePoints = assignments.reduce((sum, assignment) => sum + assignment.points_possible, 0);
    const activeCoursePoints = activeAssignments.reduce((sum, assignment) => sum + assignment.points_possible, 0);

    console.log(`✅ Found ${assignments.length} total assignments (${totalCoursePoints} total points)`);
    console.log(`✅ Found ${activeAssignments.length} active assignments (${activeCoursePoints} active points)`);
    if (activeAssignments.length < assignments.length) {
      console.log(`   📝 Filtered out ${assignments.length - activeAssignments.length} locked/closed assignments`);
    }
    console.log(`✅ Found ${students.length} students`);
    console.log(`📊 Expected API calls: ${assignments.length} assignment calls (checking all assignments for completeness)`);

    // Step 3: Get submissions for ALL assignments (but only count active ones for grading)
    console.log('\n📊 Getting submissions for all assignments (optimized parallel approach)...');
    const allSubmissions = await this.getAllSubmissionsOptimized(courseId, assignments);
    
    console.log(`✅ Retrieved submissions for ${assignments.length} assignments`);

    // Step 4: Process data efficiently using in-memory operations
    console.log('⚡ Processing grade data (in-memory operations)...');
    const studentReports = this.processStudentGrades(students, activeAssignments, allSubmissions, activeCoursePoints);

    // Step 5: Generate course summary
    const summary = this.generateCourseSummary(studentReports);

    const courseReport: CourseGradeReport = {
      course_id: courseId,
      course_name: course.name,
      total_assignments: assignments.length,
      total_course_points: totalCoursePoints,
      active_assignments: activeAssignments.length,
      active_course_points: activeCoursePoints,
      assignments: assignments,
      active_assignments_list: activeAssignments,
      students: students,
      student_reports: studentReports,
      summary: summary
    };

    return courseReport;
  }

  /**
   * Get submissions for ALL assignments using optimized parallel calls
   * This makes 1 API call per assignment instead of 1 call per student per assignment
   */
  private async getAllSubmissionsOptimized(
    courseId: number,
    assignments: Assignment[]
  ): Promise<Map<number, AssignmentSubmission[]>> {
    const submissionsByAssignment = new Map<number, AssignmentSubmission[]>();
    
    // Process assignments in batches to avoid overwhelming the API
    const batchSize = 5; // Process 5 assignments at a time
    const batches: Assignment[][] = [];
    
    for (let i = 0; i < assignments.length; i += batchSize) {
      batches.push(assignments.slice(i, i + batchSize));
    }

    console.log(`   Processing ${assignments.length} assignments in ${batches.length} batches of ${batchSize}...`);

    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      const batch = batches[batchIndex];
      
      // Process each batch in parallel
      const batchPromises = batch.map(assignment => 
        this.getAssignmentSubmissions(courseId, assignment.id)
      );
      
      const batchResults = await Promise.all(batchPromises);
      
      // Store results
      batch.forEach((assignment, index) => {
        submissionsByAssignment.set(assignment.id, batchResults[index]);
      });
      
      // Progress indicator
      const progress = ((batchIndex + 1) / batches.length * 100).toFixed(1);
      const assignmentsProcessed = (batchIndex + 1) * batchSize;
      console.log(`   ⚡ Batch ${batchIndex + 1}/${batches.length}: Processed ${Math.min(assignmentsProcessed, assignments.length)}/${assignments.length} assignments [${progress}%]`);
      
      // Small delay between batches to be respectful to the API
      if (batchIndex < batches.length - 1) {
        await new Promise(resolve => setTimeout(resolve, 100));
      }
    }

    return submissionsByAssignment;
  }

  /**
   * Get all submissions for a single assignment
   */
  private async getAssignmentSubmissions(
    courseId: number,
    assignmentId: number
  ): Promise<AssignmentSubmission[]> {
    try {
      const response = await this.gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments/${assignmentId}/submissions`,
        {
          params: {
            per_page: 100, // Get all submissions for this assignment
            include: ['grade', 'score']
          }
        }
      );

      if (response.data && Array.isArray(response.data)) {
        return (response.data as any[]).map(submission => ({
          id: submission.id,
          assignment_id: assignmentId,
          user_id: submission.user_id,
          score: submission.score,
          grade: submission.grade,
          workflow_state: submission.workflow_state,
          submitted_at: submission.submitted_at,
          late: submission.late || false,
          missing: submission.missing || false
        }));
      }
      
      return [];
    } catch (error) {
      console.log(`   ⚠️ Error getting submissions for assignment ${assignmentId}:`, error);
      return [];
    }
  }

  /**
   * Process all grade data using efficient in-memory operations
   * Now focuses on active assignments only and includes missing assignment IDs
   */
  private processStudentGrades(
    students: Student[],
    activeAssignments: Assignment[], // Only active assignments for grading
    allSubmissions: Map<number, AssignmentSubmission[]>,
    activeCoursePoints: number // Only points from active assignments
  ): StudentGradeReport[] {
    // Create lookup map of all submissions by student ID
    const submissionsByStudent = new Map<number, AssignmentSubmission[]>();
    
    // Group all submissions by student ID
    allSubmissions.forEach((assignmentSubmissions, assignmentId) => {
      assignmentSubmissions.forEach(submission => {
        if (!submissionsByStudent.has(submission.user_id)) {
          submissionsByStudent.set(submission.user_id, []);
        }
        submissionsByStudent.get(submission.user_id)!.push(submission);
      });
    });

    const studentReports: StudentGradeReport[] = [];

    // Process each student efficiently
    students.forEach((student, index) => {
      const studentSubmissions = submissionsByStudent.get(student.id) || [];
      
      // Create lookup of student's submissions by assignment ID
      const studentSubmissionMap = new Map<number, AssignmentSubmission>();
      studentSubmissions.forEach(submission => {
        studentSubmissionMap.set(submission.assignment_id, submission);
      });
      
      const submissions: StudentSubmission[] = [];
      const missingAssignments: MissingAssignment[] = [];
      const missingAssignmentIds: number[] = [];
      let totalPointsEarned = 0;

      // Check each ACTIVE assignment for this student
      // Note: We only count active assignments as potentially missing
      // Filtered assignments (locked, 0-point, etc.) are not counted as missing
      activeAssignments.forEach(assignment => {
        const studentSubmission = studentSubmissionMap.get(assignment.id);
        
        if (studentSubmission && 
            studentSubmission.score !== null && 
            studentSubmission.score !== undefined && 
            studentSubmission.workflow_state === 'graded') {
          
          // Student has a grade - add the points (round to 2 decimal places for precision)
          totalPointsEarned += Math.round(studentSubmission.score * 100) / 100;
          
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
          missingAssignmentIds.push(assignment.id);
        }
      });

      // Calculate student's grade percentage (based on active assignments only)
      const gradePercentage = activeCoursePoints > 0 ? (totalPointsEarned / activeCoursePoints) * 100 : 0;
      
      // Check if course is completed (no missing assignments)
      const isCourseCompleted = missingAssignments.length === 0;

      const studentReport: StudentGradeReport = {
        student_id: student.id,
        student_name: student.name,
        submissions: submissions,
        missing_assignments: missingAssignments,
        missing_assignment_ids: missingAssignmentIds, // New field with missing assignment IDs
        total_points_possible: activeCoursePoints, // Use active course points
        total_points_earned: Math.round(totalPointsEarned * 100) / 100, // Round to 2 decimal places
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
          unlock_at: assignment.unlock_at,
          lock_at: assignment.lock_at,
          workflow_state: assignment.workflow_state,
          published: assignment.published || false,
          only_visible_to_overrides: assignment.only_visible_to_overrides || false,
          locked_for_user: assignment.locked_for_user || false
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
    
    const averagePoints = totalStudents > 0 
      ? Math.round((studentReports.reduce((sum, report) => sum + report.total_points_earned, 0) / totalStudents) * 100) / 100
      : 0;
    
    const totalMissingAssignments = studentReports.reduce((sum, report) => sum + report.missing_assignments_count, 0);

    return {
      total_students: totalStudents,
      students_completed: studentsCompleted,
      students_in_progress: studentsInProgress,
      average_points: averagePoints,
      total_missing_assignments: totalMissingAssignments
    };
  }

  /**
   * Print a compact summary report
   */
  printSummaryReport(report: CourseGradeReport) {
    console.log('\n📋 COURSE GRADE SUMMARY (Points-Based)');
    console.log('=======================================');
    
    console.log(`Course: ${report.course_name}`);
    console.log(`Total Assignments: ${report.total_assignments} (${report.total_course_points} total points)`);
    console.log(`Active Assignments: ${report.active_assignments} (${report.active_course_points} active points)`);
    console.log(`Students: ${report.summary.total_students} total, ${report.summary.students_completed} completed, ${report.summary.students_in_progress} in progress`);
    const formattedAverage = report.summary.average_points % 1 === 0 
      ? report.summary.average_points.toString() 
      : report.summary.average_points.toFixed(1).replace(/\.?0+$/, '');
    const formattedActivePts = report.active_course_points % 1 === 0 
      ? report.active_course_points.toString() 
      : report.active_course_points.toFixed(1).replace(/\.?0+$/, '');
    
    console.log(`Average Points Earned: ${formattedAverage}/${formattedActivePts} points`);
    console.log(`Missing Assignments: ${report.summary.total_missing_assignments} total`);

    console.log('\n🏆 Top 10 Students (by points earned):');
    report.student_reports
      .sort((a, b) => b.total_points_earned - a.total_points_earned) // Sort by points, not percentage
      .slice(0, 10)
      .forEach((student, index) => {
        const status = student.is_course_completed ? '✅' : '📝';
        const formattedPoints = student.total_points_earned % 1 === 0 
          ? student.total_points_earned.toString() 
          : student.total_points_earned.toFixed(2).replace(/\.?0+$/, '');
        const formattedPossible = student.total_points_possible % 1 === 0 
          ? student.total_points_possible.toString() 
          : student.total_points_possible.toFixed(2).replace(/\.?0+$/, '');
        
        console.log(`   ${index + 1}. ${student.student_name}: ${formattedPoints}/${formattedPossible} points (${student.completed_assignments_count}/${report.active_assignments}) ${status}`);
        if (student.missing_assignment_ids.length > 0) {
          console.log(`      Missing Assignment IDs: [${student.missing_assignment_ids.join(', ')}]`);
        }
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
async function runFixedGradesTracker() {
  console.log('🔧 FIXED Canvas Course Grades Tracker');
  console.log('======================================\n');

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
  const tracker = new FixedCanvasGradesTracker(gateway);

  try {
    // Target course: JDU 1st Section (testing rounding fixes)
    const courseId = 7982015;
    
    const startTime = Date.now();
    const report = await tracker.generateCourseGradeReport(courseId);
    const elapsed = Date.now() - startTime;

    console.log(`\n🎉 SUCCESS!`);
    console.log(`✅ Complete grade report generated in ${(elapsed / 1000).toFixed(1)} seconds`);
    
    // Print reports
    tracker.printSummaryReport(report);

    // API Performance Summary
    console.log('\n⚡ API PERFORMANCE COMPARISON:');
    const finalStatus = gateway.getApiStatus();
    const badApproachCalls = 33 * 37; // Students × Assignments = 1,221 calls
    const actualCalls = finalStatus.schedulerMetrics.totalRequests;
    const savings = badApproachCalls - actualCalls;
    const percentSavings = ((savings / badApproachCalls) * 100).toFixed(1);
    
    console.log(`   🔴 Bad approach: ${badApproachCalls} API calls (1 per student per assignment)`);
    console.log(`   🟢 Fixed approach: ${actualCalls} API calls (1 per assignment + overhead)`);
    console.log(`   💰 Savings: ${savings} calls (${percentSavings}% reduction)`);
    console.log(`   📈 Speed improvement: ~${Math.round(badApproachCalls / actualCalls)}x faster`);
    console.log(`   🎯 Rate limit usage: ${((finalStatus.rateLimitStatus.requestsInWindow / finalStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
    console.log(`   ✅ Success rate: ${finalStatus.schedulerMetrics.successRate.toFixed(1)}%`);

    return report;

  } catch (error) {
    console.error('💥 Fixed grades tracking failed:', error);
  }
}

// Run the fixed tracker
runFixedGradesTracker().catch(console.error);