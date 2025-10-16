/**
 * Bulk Canvas API Test Script
 * 
 * Uses the existing bulk API infrastructure to process multiple courses
 * with configuration-driven selective data collection.
 */

import { CanvasDataConstructor } from './canvas-interface/staging/canvas-data-constructor';
import { CanvasBulkApiDataManager } from './canvas-interface/staging/bulk-api-call-staging';
import { SyncConfiguration } from './canvas-interface/types/sync-configuration';

interface BulkTestOptions {
  maxCourses?: number;
  includeUnpublished?: boolean;
  workflowStates?: string[];
  configuration?: SyncConfiguration;
}

/**
 * Print detailed raw data for verification purposes
 */
function printDetailedRawData(courses: any[], students: any[], assignments: any[], enrollments: any[]) {
  console.log('\n' + '='.repeat(80));
  console.log('🔍 DETAILED RAW DATA VERIFICATION');
  console.log('='.repeat(80));
  
  // Print Courses
  console.log(`\n📚 COURSES (${courses.length} total):`);
  console.log('-'.repeat(60));
  courses.forEach((course, index) => {
    console.log(`\n[Course ${index + 1}/${courses.length}]`);
    console.log(`   ID: ${course.id}`);
    console.log(`   Name: "${course.name}"`);
    console.log(`   Code: "${course.course_code || 'N/A'}"`);
    console.log(`   State: ${course.workflow_state}`);
    console.log(`   Created At: ${course.created_at || 'N/A'}`);
    console.log(`   Calendar: ${course.calendar || 'N/A'}`);
  });
  
  // Print Students
  console.log(`\n\n👥 STUDENTS (${students.length} total):`);
  console.log('-'.repeat(60));
  students.forEach((student, index) => {
    console.log(`\n[Student ${index + 1}/${students.length}]`);
    console.log(`   Student ID: ${student.student_id || student.id}`);
    console.log(`   User ID: ${student.user_id}`);
    console.log(`   Course ID: ${student.course_id}`);
    console.log(`   Name: "${student.name}"`);
    console.log(`   Email: "${student.email}"`);
    console.log(`   Current Score: ${student.current_score}`);
    console.log(`   Final Score: ${student.final_score}`);
    console.log(`   Current Grade: "${student.current_grade || 'N/A'}"`);
    console.log(`   Final Grade: "${student.final_grade || 'N/A'}"`);
    console.log(`   Enrollment Status: "${student.enrollment_status || 'N/A'}"`);
    console.log(`   Enrollment Date: ${student.enrollment_date || 'N/A'}`);
    console.log(`   Last Synced: ${student.last_synced || 'N/A'}`);
    console.log(`   Created At: ${student.created_at || 'N/A'}`);
    console.log(`   Updated At: ${student.updated_at || 'N/A'}`);
  });
  
  // Print Assignments
  console.log(`\n\n📝 ASSIGNMENTS (${assignments.length} total):`);
  console.log('-'.repeat(60));
  assignments.forEach((assignment, index) => {
    console.log(`\n[Assignment ${index + 1}/${assignments.length}]`);
    console.log(`   Assignment ID: ${assignment.assignment_id || assignment.id}`);
    console.log(`   Course ID: ${assignment.course_id}`);
    console.log(`   Name: "${assignment.name}"`);
    console.log(`   Description: "${(assignment.description || '').substring(0, 100)}${assignment.description && assignment.description.length > 100 ? '...' : ''}"`);
    console.log(`   Points: ${assignment.points_possible}`);
    console.log(`   Due Date: ${assignment.due_at || 'N/A'}`);
    console.log(`   Type: ${assignment.submission_types || assignment.type || 'N/A'}`);
    console.log(`   Published: ${assignment.published}`);
    console.log(`   Position: ${assignment.position || 'N/A'}`);
    console.log(`   Module ID: ${assignment.module_id || 'N/A'}`);
    console.log(`   Workflow State: ${assignment.workflow_state || 'N/A'}`);
    console.log(`   Created At: ${assignment.created_at || 'N/A'}`);
    console.log(`   Updated At: ${assignment.updated_at || 'N/A'}`);
  });
  
  // Print Enrollments
  console.log(`\n\n📋 ENROLLMENTS (${enrollments.length} total):`);
  console.log('-'.repeat(60));
  enrollments.forEach((enrollment, index) => {
    console.log(`\n[Enrollment ${index + 1}/${enrollments.length}]`);
    console.log(`   Enrollment ID: ${enrollment.enrollment_id || enrollment.id}`);
    console.log(`   Course ID: ${enrollment.course_id}`);
    console.log(`   User ID: ${enrollment.user_id}`);
    console.log(`   Student ID: ${enrollment.student_id}`);
    console.log(`   Type: ${enrollment.type || 'N/A'}`);
    console.log(`   Role: ${enrollment.role || 'N/A'}`);
    console.log(`   State: ${enrollment.enrollment_state || enrollment.workflow_state || 'N/A'}`);
    console.log(`   Current Score: ${enrollment.current_score || 'N/A'}`);
    console.log(`   Final Score: ${enrollment.final_score || 'N/A'}`);
    console.log(`   Current Grade: "${enrollment.current_grade || 'N/A'}"`);
    console.log(`   Final Grade: "${enrollment.final_grade || 'N/A'}"`);
    console.log(`   Created At: ${enrollment.created_at || 'N/A'}`);
    console.log(`   Updated At: ${enrollment.updated_at || 'N/A'}`);
    console.log(`   Last Activity: ${enrollment.last_activity_at || 'N/A'}`);
  });
  
  console.log('\n' + '='.repeat(80));
  console.log('✅ RAW DATA VERIFICATION COMPLETE');
  console.log('='.repeat(80));
}

async function executeBulkCanvasTest(options: BulkTestOptions = {}) {
  console.log('🏢 Bulk Canvas API Test - Multi-Course Processing');
  console.log('=================================================');
  
  try {
    // Create data constructor
    const dataConstructor = new CanvasDataConstructor({
      config: options.configuration
    });
    
    // Create bulk API manager
    const bulkManager = new CanvasBulkApiDataManager(options.configuration);
    
    // Set up course filters
    const courseFilters = {
      includeUnpublished: options.includeUnpublished || false,
      workflowStates: options.workflowStates || ['available'],
      maxCourses: options.maxCourses
    };
    
    console.log('\n🚀 Starting bulk workflow...');
    console.log(`   📋 Course filters: ${JSON.stringify(courseFilters)}`);
    console.log(`   ⚙️  Configuration: ${options.configuration ? 'Custom' : 'Full sync'}`);
    
    const startTime = Date.now();
    
    // Execute the complete bulk workflow
    const workflowResult = await bulkManager.executeBulkWorkflow(dataConstructor, courseFilters);
    
    const totalTime = Date.now() - startTime;
    
    console.log('\n🎉 Bulk workflow completed!');
    console.log('============================');
    
    if (workflowResult.success) {
      console.log(`✅ Success: ${workflowResult.coursesProcessed}/${workflowResult.coursesDiscovered} courses processed`);
      console.log(`👥 Students: ${workflowResult.totalStudents}`);
      console.log(`📝 Assignments: ${workflowResult.totalAssignments}`);
      console.log(`📋 Enrollments: ${workflowResult.totalEnrollments}`);
      console.log(`📞 API Calls: ${workflowResult.totalApiCalls}`);
      console.log(`⏱️  Total Time: ${totalTime}ms`);
      console.log(`⚡ Avg Time/Course: ${workflowResult.averageTimePerCourse.toFixed(1)}ms`);
      
      // Get reconstructed data for output
      const courses = bulkManager.reconstructAllCourses();
      const students = bulkManager.reconstructAllStudents();
      const assignments = bulkManager.reconstructAllAssignments();
      const enrollments = bulkManager.reconstructAllEnrollments();
      
      // Print detailed raw data for verification
      printDetailedRawData(courses, students, assignments, enrollments);
      
      // Output structured data for Python consumption
      console.log('\n===BULK_CANVAS_API_RESULT_START===');
      console.log(JSON.stringify({
        success: true,
        workflow_result: workflowResult,
        data: {
          courses: courses,
          students: students,
          assignments: assignments,
          enrollments: enrollments
        },
        metadata: {
          api_execution_time: totalTime,
          courses_discovered: workflowResult.coursesDiscovered,
          courses_processed: workflowResult.coursesProcessed,
          total_api_calls: workflowResult.totalApiCalls,
          bulk_summary: bulkManager.getBulkSummary()
        }
      }));
      console.log('===BULK_CANVAS_API_RESULT_END===');
      
    } else {
      console.log(`❌ Workflow failed:`);
      workflowResult.errors.forEach(error => console.log(`   - ${error}`));
      
      // Output error result
      console.log('\n===BULK_CANVAS_API_RESULT_START===');
      console.log(JSON.stringify({
        success: false,
        error: {
          message: 'Bulk workflow failed',
          errors: workflowResult.errors
        },
        workflow_result: workflowResult
      }));
      console.log('===BULK_CANVAS_API_RESULT_END===');
    }
    
  } catch (error) {
    console.error('💥 Bulk test failed:', error);
    
    // Output error result for Python
    console.log('\n===BULK_CANVAS_API_RESULT_START===');
    console.log(JSON.stringify({
      success: false,
      error: {
        message: error instanceof Error ? error.message : 'Unknown error',
        type: 'BulkProcessingError'
      }
    }));
    console.log('===BULK_CANVAS_API_RESULT_END===');
    
    throw error;
  }
}

// Parse command line arguments for configuration
const args = process.argv.slice(2);
const options: BulkTestOptions = {};

// Simple argument parsing
args.forEach(arg => {
  if (arg.startsWith('--max-courses=')) {
    options.maxCourses = parseInt(arg.split('=')[1]);
  } else if (arg === '--include-unpublished') {
    options.includeUnpublished = true;
  } else if (arg.startsWith('--workflow-states=')) {
    options.workflowStates = arg.split('=')[1].split(',');
  }
});

console.log(`🎯 Bulk test options: ${JSON.stringify(options)}`);

// Run the bulk test
executeBulkCanvasTest(options).catch(console.error);