/**
 * Optimized Student Staging Demo
 * 
 * Tests the complete course construction with optimized assignment analytics:
 * 1. Builds full course staging structure
 * 2. Uses current_score vs final_score optimization to only call API for students with missing assignments
 * 3. Shows all students with missing assignments (most useful information for tracking)
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

async function testOptimizedStudentStaging() {
  console.log('🎯 Optimized Student Staging with Missing Assignment Analytics');
  console.log('=============================================================\n');

  try {
    const constructor = new CanvasDataConstructor();

    // Get course ID
    const courseIdInput = await askQuestion('Enter Canvas Course ID (or press Enter for default 7982015): ');
    const courseId = parseInt(courseIdInput.trim() || '7982015');
    console.log(`\n🎯 Building complete course staging structure for course ID: ${courseId}\n`);

    // Step 1: Build complete course staging structure
    console.log('🏗️ STEP 1: Building complete course staging structure...');
    console.log('=======================================================');
    const courseData = await constructor.constructCourseData(courseId);
    
    // Step 2: Load assignment analytics (optimized)
    console.log('\n📊 STEP 2: Loading assignment analytics (optimized for missing assignments)...');
    console.log('==============================================================================');
    await courseData.loadAllStudentAnalytics();
    
    // Display completion summary
    console.log('\n🎉 COURSE STAGING STRUCTURE COMPLETED!');
    console.log('=====================================');
    console.log(`📋 Course: ${courseData.name} (${courseData.course_code})`);
    console.log(`👥 Total Students: ${courseData.students.length}`);
    console.log(`📚 Modules: ${courseData.modules.length}`);
    console.log(`📝 Total Assignments: ${courseData.getAllAssignments().length}`);
    
    // Analyze students with missing assignments
    const studentsWithMissingAssignments = courseData.students.filter((student: any) => student.missing_assignments.length > 0);
    const studentsWithNoMissingAssignments = courseData.students.filter((student: any) => !student.hasMissingAssignments());
    
    console.log(`\n📊 MISSING ASSIGNMENT ANALYSIS:`);
    console.log(`===============================`);
    console.log(`✅ Students with no missing assignments: ${studentsWithNoMissingAssignments.length}`);
    console.log(`❌ Students with missing assignments: ${studentsWithMissingAssignments.length}`);
    
    if (studentsWithMissingAssignments.length === 0) {
      console.log('\n🎉 EXCELLENT! All students are up to date with their assignments!');
    } else {
      console.log(`\n⚠️ ATTENTION NEEDED: ${studentsWithMissingAssignments.length} students have missing assignments`);
    }

    // User menu
    while (true) {
      console.log('\n🤔 What would you like to view?');
      console.log('1. 🚨 Students with Missing Assignments (PRIORITY VIEW)');
      console.log('2. 📊 All Student Status Summary');
      console.log('3. 📋 Complete Course Data');
      console.log('4. Exit');
      
      const choice = await askQuestion('\nEnter your choice (1-4): ');
      
      if (choice === '1') {
        showStudentsWithMissingAssignments(courseData);
      } else if (choice === '2') {
        showAllStudentSummary(courseData);
      } else if (choice === '3') {
        await showCompleteCourseData(courseData);
      } else if (choice === '4') {
        break;
      } else {
        console.log('❌ Invalid choice. Please enter 1, 2, 3, or 4.');
      }
    }

    console.log('\n🎯 Demo Complete!');
    
  } catch (error) {
    console.error('💥 Demo failed:', error);
  } finally {
    rl.close();
  }
}

function showStudentsWithMissingAssignments(courseData: any) {
  const studentsWithMissingAssignments = courseData.students.filter((student: any) => student.missing_assignments.length > 0);
  
  if (studentsWithMissingAssignments.length === 0) {
    console.log('\n🎉 NO STUDENTS WITH MISSING ASSIGNMENTS!');
    console.log('=======================================');
    console.log('All students are up to date with their coursework.');
    return;
  }
  
  console.log(`\n🚨 STUDENTS WITH MISSING ASSIGNMENTS (${studentsWithMissingAssignments.length} students)`);
  console.log('================================================');
  
  // Sort by number of missing assignments (most concerning first)
  studentsWithMissingAssignments.sort((a: any, b: any) => b.missing_assignments.length - a.missing_assignments.length);
  
  studentsWithMissingAssignments.forEach((student: any, index: number) => {
    const summary = student.getAssignmentSummary();
    console.log(`\n${index + 1}. ${student.user.name} (ID: ${student.user_id})`);
    console.log(`   📊 Current Score: ${student.current_score || 'N/A'} | Final Score: ${student.final_score || 'N/A'}`);
    console.log(`   📋 Total: ${summary.total_assignments} | Submitted: ${summary.submitted_count} | Missing: ${summary.missing_count}`);
    console.log(`   📈 Submission Rate: ${summary.submission_rate}`);
    console.log(`   📅 Last Activity: ${student.last_activity_at || 'No activity recorded'}`);
    
    console.log(`   ❌ MISSING ASSIGNMENTS (${student.missing_assignments.length}):`);
    student.missing_assignments.forEach((assignment: any, assignIndex: number) => {
      console.log(`      ${assignIndex + 1}. "${assignment.title}" - ${assignment.points_possible || 'N/A'} points (${assignment.status})`);
    });
    
    if (student.submitted_assignments.length > 0) {
      console.log(`   ✅ Recent submissions: ${student.submitted_assignments.slice(-3).map((a: any) => a.title).join(', ')}`);
    }
  });
  
  // Summary statistics for missing assignments
  const totalMissingAssignments = studentsWithMissingAssignments.reduce((sum: number, student: any) => sum + student.missing_assignments.length, 0);
  const avgMissingPerStudent = (totalMissingAssignments / studentsWithMissingAssignments.length).toFixed(1);
  
  console.log(`\n📊 MISSING ASSIGNMENT STATISTICS:`);
  console.log(`================================`);
  console.log(`Total missing assignments across all students: ${totalMissingAssignments}`);
  console.log(`Average missing assignments per student: ${avgMissingPerStudent}`);
  
  // Find most commonly missing assignments
  const missingAssignmentCounts: {[key: string]: number} = {};
  studentsWithMissingAssignments.forEach((student: any) => {
    student.missing_assignments.forEach((assignment: any) => {
      missingAssignmentCounts[assignment.title] = (missingAssignmentCounts[assignment.title] || 0) + 1;
    });
  });
  
  const sortedMissingAssignments = Object.entries(missingAssignmentCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);
    
  if (sortedMissingAssignments.length > 0) {
    console.log(`\n🔍 MOST COMMONLY MISSING ASSIGNMENTS:`);
    console.log(`====================================`);
    sortedMissingAssignments.forEach(([title, count], index) => {
      console.log(`${index + 1}. "${title}" - ${count} students missing`);
    });
  }
}

function showAllStudentSummary(courseData: any) {
  console.log('\n📊 ALL STUDENT STATUS SUMMARY');
  console.log('=============================');
  
  // Group students by status
  const studentsWithMissingAssignments = courseData.students.filter((student: any) => student.missing_assignments.length > 0);
  const studentsUpToDate = courseData.students.filter((student: any) => !student.hasMissingAssignments());
  
  console.log(`\n✅ STUDENTS UP TO DATE (${studentsUpToDate.length}):`);
  studentsUpToDate.forEach((student: any, index: number) => {
    console.log(`   ${index + 1}. ${student.user.name} - Score: ${student.current_score || 'N/A'}`);
  });
  
  console.log(`\n❌ STUDENTS WITH MISSING ASSIGNMENTS (${studentsWithMissingAssignments.length}):`);
  studentsWithMissingAssignments.forEach((student: any, index: number) => {
    const summary = student.getAssignmentSummary();
    console.log(`   ${index + 1}. ${student.user.name} - Missing: ${summary.missing_count} assignments (${summary.submission_rate} submitted)`);
  });
  
  // Course-wide statistics
  if (courseData.students.length > 0) {
    const studentsWithScores = courseData.students.filter((s: any) => s.current_score !== null);
    if (studentsWithScores.length > 0) {
      const avgCurrentScore = studentsWithScores.reduce((sum: number, s: any) => sum + (s.current_score || 0), 0) / studentsWithScores.length;
      const avgFinalScore = studentsWithScores.reduce((sum: number, s: any) => sum + (s.final_score || 0), 0) / studentsWithScores.length;
      
      console.log('\n📈 COURSE-WIDE STATISTICS:');
      console.log(`Average Current Score: ${avgCurrentScore.toFixed(2)}`);
      console.log(`Average Final Score: ${avgFinalScore.toFixed(2)}`);
      console.log(`Students on track: ${((studentsUpToDate.length / courseData.students.length) * 100).toFixed(1)}%`);
      console.log(`Students needing attention: ${((studentsWithMissingAssignments.length / courseData.students.length) * 100).toFixed(1)}%`);
    }
  }
}

async function showCompleteCourseData(courseData: any) {
  const confirm = await askQuestion('\n⚠️ This will display ALL course data (very large output). Continue? (y/n): ');
  
  if (confirm.toLowerCase() === 'y') {
    console.log('\n📋 COMPLETE COURSE DATA STRUCTURE');
    console.log('==================================');
    
    console.log(`\n🎓 COURSE: ${courseData.name} (${courseData.course_code})`);
    console.log(`ID: ${courseData.id}`);
    
    console.log('\n👥 ALL STUDENTS WITH FULL ANALYTICS:');
    console.log('===================================');
    
    courseData.students.forEach((student: any, index: number) => {
      console.log(`\n${index + 1}. ${student.user.name} (ID: ${student.user_id})`);
      console.log(`   Current Score: ${student.current_score || 'N/A'} | Final Score: ${student.final_score || 'N/A'}`);
      console.log(`   Has Missing Assignments: ${student.hasMissingAssignments() ? 'YES' : 'NO'}`);
      console.log(`   Last Activity: ${student.last_activity_at || 'No activity'}`);
      
      const summary = student.getAssignmentSummary();
      console.log(`   📊 Assignments - Total: ${summary.total_assignments} | Submitted: ${summary.submitted_count} | Missing: ${summary.missing_count} | Rate: ${summary.submission_rate}`);
      
      if (student.missing_assignments.length > 0) {
        console.log(`   ❌ Missing Assignments:`);
        student.missing_assignments.forEach((assignment: any) => {
          console.log(`      - ${assignment.title}: ${assignment.points_possible || 'N/A'} points`);
        });
      }
    });
  }
}

// Run the test
testOptimizedStudentStaging().catch(console.error);