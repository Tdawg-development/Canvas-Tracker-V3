/**
 * Canvas Staging Demo Program
 * 
 * Interactive demo that lets users input a course ID and see the complete
 * Canvas staging data structure built and displayed.
 * 
 * Recent Updates:
 * - ✅ Email collection via dual Canvas API calls
 * - ✅ Timestamp preservation from Canvas API
 * - ✅ Enhanced sortable name handling
 */

import * as readline from 'readline';
import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
import { CanvasCourseStaging } from '../staging/canvas-staging-data';

// Create readline interface for user input
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout
});

function askQuestion(question: string): Promise<string> {
  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      resolve(answer);
    });
  });
}

async function displayCourseData(course: CanvasCourseStaging) {
  console.log('\n📊 COMPLETE CANVAS STAGING DATA STRUCTURE');
  console.log('==========================================');
  console.log('\n THIS DEMO IS TO TEST "canvas-data-constructor"');
  // Warn user about large datasets
  const totalStudents = course.students.length;
  const totalAssignments = course.getAllAssignments().length;
  const totalModules = course.modules.length;
  
  if (totalStudents > 20 || totalAssignments > 50) {
    console.log(`\n⚠️ LARGE DATASET WARNING:`);
    console.log(`   Students: ${totalStudents}`);
    console.log(`   Assignments: ${totalAssignments}`);
    console.log(`   Modules: ${totalModules}`);
    console.log(`   This will generate a lot of output!`);
    
    const proceed = await askQuestion('\nDo you want to display all data? (y/n): ');
    if (!proceed.toLowerCase().startsWith('y')) {
      console.log('\n📋 Showing summary only...');
      const summary = course.getSummary();
      console.log('\n📈 SUMMARY STATISTICS:');
      console.log(`   Course ID: ${summary.course_id}`);
      console.log(`   Course Name: ${summary.course_name}`);
      console.log(`   Total Students: ${summary.students_count}`);
      console.log(`   Students with Scores: ${summary.students_with_scores}`);
      console.log(`   Total Modules: ${summary.modules_count}`);
      console.log(`   Total Assignments: ${summary.total_assignments}`);
      console.log(`   Published Assignments: ${summary.published_assignments}`);
      console.log(`   Total Possible Points: ${summary.total_possible_points}`);
      return;
    }
    
    console.log('\n📄 Displaying complete dataset...');
  }
  
  // Course Information
  console.log('\n🎓 COURSE OBJECT:');
  console.log(`   ID: ${course.id}`);
  console.log(`   Name: ${course.name}`);
  console.log(`   Course Code: ${course.course_code}`);
  console.log(`   Calendar ICS: ${course.calendar.ics || 'Not available'}`);
  
  // Students Information - SHOW ALL
  console.log(`\n👥 STUDENTS OBJECT (${course.students.length} total):`);
  course.students.forEach((student, index) => {
    console.log(`   ${index + 1}. Student ID: ${student.id}`);
    console.log(`      User ID: ${student.user_id}`);
    console.log(`      Name: ${student.user.name}`);
    console.log(`      Sortable Name: ${student.user.sortable_name}`);
    console.log(`      Login ID: ${student.user.login_id}`);
    console.log(`      Created At: ${student.created_at}`);
    console.log(`      Last Activity: ${student.last_activity_at || 'Never'}`);
    console.log(`      Current Score: ${student.current_score || 'Not set'}`);
    console.log(`      Final Score: ${student.final_score || 'Not set'}`);
    console.log('');
  });
  
  // Modules Information - SHOW ALL
  console.log(`\n📚 MODULES OBJECT (${course.modules.length} total):`);
  course.modules.forEach((module, index) => {
    console.log(`   ${index + 1}. Module ID: ${module.id}`);
    console.log(`      Position: ${module.position}`);
    console.log(`      Published: ${module.published}`);
    console.log(`      Assignments: ${module.assignments.length}`);
    
    // Show ALL assignments in this module
    if (module.assignments.length > 0) {
      console.log(`      📝 ASSIGNMENT OBJECTS in this module:`);
      module.assignments.forEach((assignment, assIndex) => {
        console.log(`         ${assIndex + 1}. Assignment ID: ${assignment.id}`);
        console.log(`            Title: ${assignment.title}`);
        console.log(`            Type: ${assignment.type}`);
        console.log(`            Position: ${assignment.position}`);
        console.log(`            Published: ${assignment.published}`);
        console.log(`            Points Possible: ${assignment.content_details.points_possible}`);
        console.log(`            URL: ${assignment.url}`);
      });
    } else {
      console.log(`      📝 No assignments found in this module`);
    }
    console.log('');
  });
  
  // All Assignments Comprehensive List
  const allAssignments = course.getAllAssignments();
  if (allAssignments.length > 0) {
    console.log(`\n📝 COMPREHENSIVE ASSIGNMENTS LIST (${allAssignments.length} total):`);
    console.log('===============================================================');
    allAssignments.forEach((assignment, index) => {
      console.log(`   ${index + 1}. Assignment ID: ${assignment.id}`);
      console.log(`      Title: ${assignment.title}`);
      console.log(`      Type: ${assignment.type}`);
      console.log(`      Position: ${assignment.position}`);
      console.log(`      Published: ${assignment.published}`);
      console.log(`      Points Possible: ${assignment.content_details.points_possible}`);
      console.log(`      URL: ${assignment.url}`);
      console.log('');
    });
  } else {
    console.log(`\n📝 COMPREHENSIVE ASSIGNMENTS LIST:`);
    console.log('===============================================================');
    console.log('   No assignments found in any modules.');
  }
  
  // Summary Statistics
  const summary = course.getSummary();
  console.log('\n📈 SUMMARY STATISTICS:');
  console.log(`   Course ID: ${summary.course_id}`);
  console.log(`   Course Name: ${summary.course_name}`);
  console.log(`   Total Students: ${summary.students_count}`);
  console.log(`   Students with Scores: ${summary.students_with_scores}`);
  console.log(`   Total Modules: ${summary.modules_count}`);
  console.log(`   Total Assignments: ${summary.total_assignments}`);
  console.log(`   Published Assignments: ${summary.published_assignments}`);
  console.log(`   Total Possible Points: ${summary.total_possible_points}`);
}

async function runDemo() {
  console.log('🎯 Canvas Staging Data Demo Program');
  console.log('===================================\n');
  
  try {
    // Get course ID from user
    const courseIdInput = await askQuestion('Enter a Canvas Course ID (or press Enter for default 7982015): ');
    const courseId = courseIdInput.trim() === '' ? 7982015 : parseInt(courseIdInput.trim());
    
    if (isNaN(courseId) || courseId <= 0) {
      console.log('❌ Invalid course ID. Please enter a positive number.');
      rl.close();
      return;
    }
    
    console.log(`\n🎯 Processing course ID: ${courseId}`);
    console.log('Building complete Canvas staging data structure...\n');
    
    // Initialize the constructor
    const constructor = new CanvasDataConstructor();
    
    // Validate course access first
    console.log('🔐 Validating course access...');
    const hasAccess = await constructor.validateCourseAccess(courseId);
    
    if (!hasAccess) {
      console.log('❌ Error: Cannot access course or course does not exist.');
      console.log('   Check that:');
      console.log('   • Course ID is correct');
      console.log('   • You have permission to access this course');
      console.log('   • Canvas API credentials are valid');
      rl.close();
      return;
    }
    
    console.log('✅ Course access validated!\n');
    
    // Build the complete staging data structure
    const courseData = await constructor.constructCourseData(courseId);
    
    // Display the results
    await displayCourseData(courseData);
    
    // Show API performance
    const apiStatus = constructor.getApiStatus();
    console.log('\n⚡ API PERFORMANCE:');
    console.log(`   Total API Calls: ${apiStatus.schedulerMetrics.totalRequests}`);
    console.log(`   Success Rate: ${apiStatus.schedulerMetrics.successRate.toFixed(1)}%`);
    console.log(`   Rate Limit Usage: ${((apiStatus.rateLimitStatus.requestsInWindow / apiStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
    
    // Ask if user wants to try another course
    console.log('\n🎯 DEMO COMPLETE!');
    const tryAnother = await askQuestion('\nWould you like to try another course? (y/n): ');
    
    if (tryAnother.toLowerCase().startsWith('y')) {
      console.log('\n' + '='.repeat(60) + '\n');
      await runDemo(); // Recursive call for another course
    } else {
      console.log('\n👋 Thanks for using the Canvas Staging Demo!');
      rl.close();
    }
    
  } catch (error) {
    console.error('\n💥 Demo failed with error:', error);
    console.log('\n🔧 Troubleshooting:');
    console.log('   • Check your Canvas API credentials (.env file)');
    console.log('   • Verify the course ID is correct');
    console.log('   • Ensure you have access to the course');
    console.log('   • Check your network connection');
    
    const tryAgain = await askQuestion('\nWould you like to try again? (y/n): ');
    
    if (tryAgain.toLowerCase().startsWith('y')) {
      console.log('\n' + '='.repeat(60) + '\n');
      await runDemo();
    } else {
      rl.close();
    }
  }
}

// Handle process termination
process.on('SIGINT', () => {
  console.log('\n\n👋 Demo terminated by user. Goodbye!');
  rl.close();
  process.exit(0);
});

// Start the demo
runDemo().catch((error) => {
  console.error('💥 Fatal error:', error);
  rl.close();
  process.exit(1);
});