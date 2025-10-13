// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

async function demoGradesSolution() {
  console.log('🎯 Canvas Grades Page Solution Demo');
  console.log('=====================================\n');

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
  
  // Target: https://canvas.instructure.com/courses/7982015/grades/111980264
  const targetCourseId = 7982015;  // JDU 1st Section
  const targetStudentId = 111980264; // From the URL you provided
  
  console.log(`📋 Target: Course ${targetCourseId}, Student ${targetStudentId}`);
  console.log(`    Canvas Page: https://canvas.instructure.com/courses/${targetCourseId}/grades/${targetStudentId}\n`);

  try {
    // STEP 1: Get all assignments in the course
    console.log('🔍 STEP 1: Getting all assignments in the course...');
    const assignmentsResponse = await gateway.getClient().requestWithFullResponse(`courses/${targetCourseId}/assignments`, {
      params: { per_page: 100 }
    });

    if (!assignmentsResponse.data) {
      console.log('❌ Failed to get assignments');
      return;
    }

    const assignments = assignmentsResponse.data as any[];
    console.log(`✅ Found ${assignments.length} assignments`);
    console.log(`   API: ${assignmentsResponse.url}`);
    
    // Show first few assignments
    console.log('\n📚 Sample assignments:');
    assignments.slice(0, 5).forEach((assignment, index) => {
      console.log(`   ${index + 1}. ${assignment.name} (${assignment.points_possible || 0} pts)`);
    });

    // STEP 2: Get submissions for each assignment for this student
    console.log(`\n🎯 STEP 2: Getting individual assignment submissions for student ${targetStudentId}...`);
    
    const submissionResults: any[] = [];
    let totalPoints = 0;
    let earnedPoints = 0;
    
    // Test with first 10 assignments for demo purposes
    const assignmentsToTest = assignments.slice(0, 10);
    console.log(`   Testing with first ${assignmentsToTest.length} assignments...\n`);

    for (let i = 0; i < assignmentsToTest.length; i++) {
      const assignment = assignmentsToTest[i];
      
      try {
        const submissionResponse = await gateway.getClient().requestWithFullResponse(
          `courses/${targetCourseId}/assignments/${assignment.id}/submissions/${targetStudentId}`,
          {
            params: {
              include: ['submission_comments', 'rubric_assessment', 'grade', 'score']
            }
          }
        );

        if (submissionResponse.data) {
          const submission = submissionResponse.data as any;
          
          // Calculate points
          const assignmentPoints = assignment.points_possible || 0;
          const studentScore = submission.score || 0;
          
          totalPoints += assignmentPoints;
          earnedPoints += studentScore;
          
          const result = {
            assignment_name: assignment.name,
            assignment_id: assignment.id,
            points_possible: assignmentPoints,
            grade: submission.grade,
            score: studentScore,
            status: submission.workflow_state,
            submitted_at: submission.submitted_at,
            graded_at: submission.graded_at,
            late: submission.late,
            missing: submission.missing,
            comments_count: submission.submission_comments ? submission.submission_comments.length : 0
          };
          
          submissionResults.push(result);
          
          // Show progress
          const statusIcon = submission.workflow_state === 'graded' ? '✅' : 
                           submission.workflow_state === 'submitted' ? '📝' : 
                           submission.missing ? '❌' : '⏸️';
          
          console.log(`   ${statusIcon} ${assignment.name}`);
          console.log(`      Grade: ${submission.grade || 'No grade'} | Score: ${studentScore}/${assignmentPoints}`);
          console.log(`      Status: ${submission.workflow_state} | Submitted: ${submission.submitted_at || 'Not submitted'}`);
          
          if (submission.late) console.log('      ⚠️ LATE');
          if (submission.missing) console.log('      ❌ MISSING');
          if (submission.submission_comments && submission.submission_comments.length > 0) {
            console.log(`      💬 ${submission.submission_comments.length} comments`);
          }
          console.log('');
          
        } else {
          console.log(`   ❌ Could not get submission for: ${assignment.name}`);
        }
        
        // Small delay to be respectful to the API
        await new Promise(resolve => setTimeout(resolve, 100));
        
      } catch (error) {
        console.log(`   ❌ Error getting submission for ${assignment.name}: ${error}`);
      }
    }

    // STEP 3: Get overall course grade from enrollment
    console.log('📊 STEP 3: Getting overall course grade from enrollment...');
    const enrollmentResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${targetCourseId}/enrollments`,
      {
        params: {
          user_id: targetStudentId,
          include: ['grades'],
          state: ['active', 'completed']
        }
      }
    );

    let overallGrade = null;
    if (enrollmentResponse.data && (enrollmentResponse.data as any[]).length > 0) {
      const enrollment = (enrollmentResponse.data as any[])[0];
      overallGrade = enrollment.grades;
      
      console.log(`✅ Overall course grade retrieved`);
      console.log(`   API: ${enrollmentResponse.url}`);
      console.log(`   Current Grade: ${overallGrade.current_grade || 'Not available'}`);
      console.log(`   Current Score: ${overallGrade.current_score || 'Not available'}%`);
      console.log(`   Final Grade: ${overallGrade.final_grade || 'Not available'}`);
      console.log(`   Final Score: ${overallGrade.final_score || 'Not available'}%`);
    } else {
      console.log('❌ Could not retrieve overall course grade');
    }

    // SUMMARY: Recreated Grades Page Data
    console.log('\n🎉 GRADES PAGE DATA SUMMARY');
    console.log('============================');
    
    console.log(`\n📋 Course: JDU 1st Section (${targetCourseId})`);
    console.log(`👤 Student: ${targetStudentId}`);
    console.log(`📚 Total Assignments: ${assignments.length}`);
    console.log(`🧪 Tested Assignments: ${assignmentsToTest.length}`);
    
    if (overallGrade) {
      console.log(`\n📊 Overall Grade:`);
      console.log(`   Current: ${overallGrade.current_grade || 'N/A'} (${overallGrade.current_score || 'N/A'}%)`);
      console.log(`   Final: ${overallGrade.final_grade || 'N/A'} (${overallGrade.final_score || 'N/A'}%)`);
    }
    
    console.log(`\n🔢 Calculated from tested assignments:`);
    console.log(`   Total Points Possible: ${totalPoints}`);
    console.log(`   Points Earned: ${earnedPoints}`);
    console.log(`   Calculated Percentage: ${totalPoints > 0 ? ((earnedPoints / totalPoints) * 100).toFixed(1) : 0}%`);
    
    // Submission breakdown
    const graded = submissionResults.filter(s => s.status === 'graded').length;
    const submitted = submissionResults.filter(s => s.status === 'submitted').length;
    const unsubmitted = submissionResults.filter(s => s.status === 'unsubmitted').length;
    const missing = submissionResults.filter(s => s.missing).length;
    const late = submissionResults.filter(s => s.late).length;
    
    console.log(`\n📈 Submission Status Breakdown:`);
    console.log(`   ✅ Graded: ${graded}`);
    console.log(`   📝 Submitted: ${submitted}`);
    console.log(`   ⏸️ Unsubmitted: ${unsubmitted}`);
    console.log(`   ❌ Missing: ${missing}`);
    console.log(`   ⚠️ Late: ${late}`);

    console.log(`\n💡 This data recreates the Canvas grades page with:`);
    console.log(`   • Individual assignment grades and scores`);
    console.log(`   • Assignment submission status`);
    console.log(`   • Late and missing assignment flags`);
    console.log(`   • Overall course grade`);
    console.log(`   • Submission comments count`);
    console.log(`   • Complete grade history`);

    // API Performance Summary
    console.log('\n⚡ API Performance:');
    const finalStatus = gateway.getApiStatus();
    console.log(`   Total API calls: ${finalStatus.schedulerMetrics.totalRequests}`);
    console.log(`   Rate limit usage: ${((finalStatus.rateLimitStatus.requestsInWindow / finalStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
    console.log(`   Success rate: ${finalStatus.schedulerMetrics.successRate.toFixed(1)}%`);

  } catch (error) {
    console.error('💥 Demo failed with error:', error);
  }
}

// Run the demo
demoGradesSolution().catch(console.error);