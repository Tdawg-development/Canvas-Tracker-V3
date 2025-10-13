/**
 * Simple Student Assignment Analytics Test
 * 
 * Tests the single API call function for student assignment analytics:
 * INPUT: courseId, studentId
 * OUTPUT: Array of assignment objects with status and scores
 */

import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
import * as readline from 'readline';

const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, resolve);
  });
}

async function testStudentAssignmentAnalytics() {
  console.log('🎯 Student Assignment Analytics API Test');
  console.log('=========================================\n');

  try {
    const constructor = new CanvasDataConstructor();

    // Get course ID
    const courseIdInput = await askQuestion('Enter Canvas Course ID (or press Enter for default 7982015): ');
    const courseId = parseInt(courseIdInput.trim() || '7982015');
    
    // Get student ID
    const studentIdInput = await askQuestion('Enter Canvas Student/User ID: ');
    const studentId = parseInt(studentIdInput.trim());
    
    if (!studentId) {
      console.log('❌ Student ID is required!');
      rl.close();
      return;
    }

    console.log(`\n🎯 Testing student assignment analytics:`);
    console.log(`   Course ID: ${courseId}`);
    console.log(`   Student ID: ${studentId}\n`);

    // Make the API call
    console.log('📊 Calling Canvas analytics API...');
    const startTime = Date.now();
    
    const analytics = await constructor.getStudentAssignmentAnalytics(courseId, studentId);
    
    const responseTime = Date.now() - startTime;
    
    console.log(`✅ API call completed in ${responseTime}ms`);
    console.log(`📈 Found ${analytics.length} assignment records\n`);
    
    if (analytics.length > 0) {
      console.log('📋 Assignment Analytics Data:');
      console.log('============================');
      
      analytics.forEach((assignment, index) => {
        console.log(`\n${index + 1}. Assignment ID: ${assignment.assignment_id}`);
        console.log(`   Title: ${assignment.title || 'Untitled'}`);
        console.log(`   Status: ${assignment.status}`);
        console.log(`   Score: ${assignment.submission.score !== null ? assignment.submission.score : 'Not submitted'}`);
        console.log(`   Points Possible: ${assignment.points_possible || 'N/A'}`);
        console.log(`   Submitted: ${assignment.submission.submitted_at || 'Not submitted'}`);
      });

      // Show status summary
      const statusCounts = analytics.reduce((counts, assignment) => {
        counts[assignment.status] = (counts[assignment.status] || 0) + 1;
        return counts;
      }, {} as Record<string, number>);
      
      console.log('\n📊 Status Summary:');
      console.log('==================');
      Object.entries(statusCounts).forEach(([status, count]) => {
        console.log(`${status}: ${count} assignments`);
      });
      
      // Calculate scores
      const submittedAssignments = analytics.filter(a => a.submission.score !== null);
      if (submittedAssignments.length > 0) {
        const totalScore = submittedAssignments.reduce((sum, a) => sum + (a.submission.score || 0), 0);
        const totalPossible = submittedAssignments.reduce((sum, a) => sum + (a.points_possible || 0), 0);
        const percentage = totalPossible > 0 ? (totalScore / totalPossible * 100).toFixed(2) : 'N/A';
        
        console.log('\n🎯 Score Summary:');
        console.log('=================');
        console.log(`Total Score: ${totalScore}/${totalPossible} (${percentage}%)`);
        console.log(`Submitted: ${submittedAssignments.length}/${analytics.length} assignments`);
      }
      
    } else {
      console.log('ℹ️ No assignment analytics found for this student.');
      console.log('   This could mean:');
      console.log('   - Student has no assignments in this course');
      console.log('   - Student ID or Course ID is incorrect');
      console.log('   - Analytics are not available for this course');
    }

    console.log('\n🎉 Test Complete!');
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  } finally {
    rl.close();
  }
}

// Run the test
testStudentAssignmentAnalytics().catch(console.error);