/**
 * Test Student Assignment Analytics Demo
 * 
 * Tests the new student assignment analytics function that retrieves:
 * - Individual assignment status and scores for specific students
 * - Assignment completion data that feeds into student grades objects
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

async function testStudentAnalytics() {
  console.log('🎯 Student Assignment Analytics Test');
  console.log('====================================\n');

  try {
    const constructor = new CanvasDataConstructor();

    // Get course ID
    const courseIdInput = await askQuestion('Enter Canvas Course ID (or press Enter for default 7982015): ');
    const courseId = courseIdInput.trim() || '7982015';
    console.log(`\n🎯 Testing student analytics for course ID: ${courseId}\n`);

    // Validate course access first
    console.log('🔐 Validating course access...');
    const hasAccess = await constructor.validateCourseAccess(parseInt(courseId));
    if (!hasAccess) {
      console.log('❌ No access to this course!');
      rl.close();
      return;
    }
    console.log('✅ Course access validated!\n');

    // Get course data to find students
    console.log('📋 Getting course data to find students...');
    const courseData = await constructor.constructCourseData(parseInt(courseId));
    const students = courseData.getStudents();
    
    if (students.length === 0) {
      console.log('❌ No students found in this course!');
      rl.close();
      return;
    }

    console.log(`\n👥 Found ${students.length} students in course`);
    console.log('📝 Sample students:');
    students.slice(0, 5).forEach((student, index) => {
      console.log(`   ${index + 1}. ${student.getUserName()} (ID: ${student.getUserId()})`);
    });

    // Test single student analytics
    console.log('\n🔍 TESTING SINGLE STUDENT ANALYTICS:');
    console.log('=====================================');
    
    const testStudent = students[0];
    const userId = testStudent.getUserId();
    const userName = testStudent.getUserName();
    
    console.log(`📊 Getting assignment analytics for: ${userName} (ID: ${userId})`);
    
    const startTime = Date.now();
    const analytics = await constructor.getStudentAssignmentAnalytics(parseInt(courseId), userId);
    const responseTime = Date.now() - startTime;
    
    console.log(`\n✅ Retrieved analytics in ${responseTime}ms`);
    console.log(`📈 Found ${analytics.length} assignment records\n`);
    
    if (analytics.length > 0) {
      console.log('📋 Sample assignment analytics:');
      analytics.slice(0, 5).forEach((assignment, index) => {
        console.log(`   ${index + 1}. Assignment ID: ${assignment.assignment_id}`);
        console.log(`      Status: ${assignment.status}`);
        console.log(`      Score: ${assignment.submission.score || 'Not submitted'}`);
        console.log(`      Points Possible: ${assignment.points_possible || 'N/A'}`);
        console.log('');
      });

      // Show status breakdown
      const statusCounts = analytics.reduce((counts, assignment) => {
        counts[assignment.status] = (counts[assignment.status] || 0) + 1;
        return counts;
      }, {} as Record<string, number>);
      
      console.log('📊 Assignment Status Summary:');
      Object.entries(statusCounts).forEach(([status, count]) => {
        console.log(`   ${status}: ${count} assignments`);
      });
    }

    // Ask if user wants to test bulk analytics
    const testBulk = await askQuestion('\n🤔 Test bulk analytics for all students? (y/n): ');
    
    if (testBulk.toLowerCase() === 'y') {
      console.log('\n🚀 TESTING BULK STUDENT ANALYTICS:');
      console.log('===================================');
      
      const studentIds = students.slice(0, 5).map(student => student.getUserId()); // Test first 5 students
      console.log(`📊 Testing with ${studentIds.length} students...`);
      
      const bulkStartTime = Date.now();
      const bulkAnalytics = await constructor.getAllStudentsAssignmentAnalytics(parseInt(courseId), studentIds);
      const bulkResponseTime = Date.now() - bulkStartTime;
      
      console.log(`\n✅ Bulk analytics completed in ${bulkResponseTime}ms`);
      console.log(`📈 Retrieved analytics for ${bulkAnalytics.size} students\n`);
      
      // Show summary for each student
      console.log('📋 Bulk Analytics Summary:');
      bulkAnalytics.forEach((studentAnalytics, studentId) => {
        const student = students.find(s => s.getUserId() === studentId);
        const studentName = student?.getUserName() || `User ${studentId}`;
        console.log(`   ${studentName}: ${studentAnalytics.length} assignments`);
      });
    }

    console.log('\n🎉 Student Analytics Test Complete!');
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  } finally {
    rl.close();
  }
}

// Run the test
testStudentAnalytics().catch(console.error);