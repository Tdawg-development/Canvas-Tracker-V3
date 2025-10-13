/**
 * Raw Course Data Output Script
 * 
 * Constructs a complete course staging structure and outputs the verbatim 
 * raw data to a text file for verification of what's being stored.
 */

import { CanvasDataConstructor } from '../staging/canvas-data-constructor';
import * as fs from 'fs';
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

async function outputRawCourseData() {
  console.log('📄 Raw Course Data Output Script');
  console.log('================================\n');

  try {
    const constructor = new CanvasDataConstructor();

    // Get course ID
    const courseIdInput = await askQuestion('Enter Canvas Course ID (or press Enter for default 7982015): ');
    const courseId = parseInt(courseIdInput.trim() || '7982015');
    console.log(`\n🎯 Constructing course staging structure for course ID: ${courseId}\n`);

    // Build complete course staging structure
    console.log('🏗️ Building complete course staging structure...');
    const courseData = await constructor.constructCourseData(courseId);
    
    // Load assignment analytics (optimized)
    console.log('📊 Loading assignment analytics (optimized)...');
    await courseData.loadAllStudentAnalytics();
    
    console.log('\n✅ Course structure completed!');
    console.log('📝 Generating raw data output...\n');

    // Generate raw data structure as string
    const rawDataOutput = generateRawDataOutput(courseData);
    
    // Write to file
    const fileName = `raw-course-data-${courseId}-${Date.now()}.txt`;
    fs.writeFileSync(fileName, rawDataOutput, 'utf8');
    
    console.log(`✅ Raw data output saved to: ${fileName}`);
    console.log(`📊 File size: ${(fs.statSync(fileName).size / 1024).toFixed(2)} KB`);
    console.log('\n🎯 Script Complete!');
    
  } catch (error) {
    console.error('💥 Script failed:', error);
  } finally {
    rl.close();
  }
}

function generateRawDataOutput(courseData: any): string {
  const output: string[] = [];
  
  output.push('========================================');
  output.push('RAW CANVAS COURSE STAGING DATA STRUCTURE');
  output.push('========================================');
  output.push(`Generated: ${new Date().toISOString()}`);
  output.push(`Course ID: ${courseData.id}`);
  output.push('');
  
  // COURSE OBJECT RAW DATA
  output.push('========================================');
  output.push('COURSE OBJECT (CanvasCourseStaging)');
  output.push('========================================');
  output.push(`id: ${courseData.id}`);
  output.push(`name: "${courseData.name}"`);
  output.push(`course_code: "${courseData.course_code}"`);
  output.push(`calendar.ics: "${courseData.calendar.ics}"`);
  output.push(`students.length: ${courseData.students.length}`);
  output.push(`modules.length: ${courseData.modules.length}`);
  output.push('');
  
  // STUDENTS RAW DATA
  output.push('========================================');
  output.push('STUDENTS ARRAY (CanvasStudentStaging[])');
  output.push('========================================');
  output.push(`Total Students: ${courseData.students.length}`);
  output.push('');
  
  courseData.students.forEach((student: any, index: number) => {
    output.push(`--- STUDENT ${index + 1} ---`);
    output.push(`id: ${student.id}`);
    output.push(`user_id: ${student.user_id}`);
    output.push(`created_at: "${student.created_at}"`);
    output.push(`last_activity_at: ${student.last_activity_at ? `"${student.last_activity_at}"` : 'null'}`);
    output.push(`current_score: ${student.current_score}`);
    output.push(`final_score: ${student.final_score}`);
    output.push(`user.id: ${student.user.id}`);
    output.push(`user.name: "${student.user.name}"`);
    output.push(`user.sortable_name: "${student.user.sortable_name}"`);
    output.push(`user.login_id: "${student.user.login_id}"`);
    output.push(`submitted_assignments.length: ${student.submitted_assignments.length}`);
    output.push(`missing_assignments.length: ${student.missing_assignments.length}`);
    output.push(`hasMissingAssignments(): ${student.hasMissingAssignments()}`);
    
    if (student.submitted_assignments.length > 0) {
      output.push(`--- SUBMITTED ASSIGNMENTS ---`);
      student.submitted_assignments.forEach((assignment: any, assignIndex: number) => {
        output.push(`  [${assignIndex}] assignment_id: ${assignment.assignment_id}`);
        output.push(`  [${assignIndex}] title: "${assignment.title}"`);
        output.push(`  [${assignIndex}] status: "${assignment.status}"`);
        output.push(`  [${assignIndex}] submission.score: ${assignment.submission.score}`);
        output.push(`  [${assignIndex}] submission.submitted_at: ${assignment.submission.submitted_at ? `"${assignment.submission.submitted_at}"` : 'null'}`);
        output.push(`  [${assignIndex}] submission.posted_at: ${assignment.submission.posted_at ? `"${assignment.submission.posted_at}"` : 'null'}`);
        output.push(`  [${assignIndex}] points_possible: ${assignment.points_possible}`);
        output.push(`  [${assignIndex}] excused: ${assignment.excused}`);
      });
    }
    
    if (student.missing_assignments.length > 0) {
      output.push(`--- MISSING ASSIGNMENTS ---`);
      student.missing_assignments.forEach((assignment: any, assignIndex: number) => {
        output.push(`  [${assignIndex}] assignment_id: ${assignment.assignment_id}`);
        output.push(`  [${assignIndex}] title: "${assignment.title}"`);
        output.push(`  [${assignIndex}] status: "${assignment.status}"`);
        output.push(`  [${assignIndex}] submission.score: ${assignment.submission.score}`);
        output.push(`  [${assignIndex}] submission.submitted_at: ${assignment.submission.submitted_at ? `"${assignment.submission.submitted_at}"` : 'null'}`);
        output.push(`  [${assignIndex}] submission.posted_at: ${assignment.submission.posted_at ? `"${assignment.submission.posted_at}"` : 'null'}`);
        output.push(`  [${assignIndex}] points_possible: ${assignment.points_possible}`);
        output.push(`  [${assignIndex}] excused: ${assignment.excused}`);
      });
    }
    
    output.push('');
  });
  
  // MODULES RAW DATA
  output.push('========================================');
  output.push('MODULES ARRAY (CanvasModuleStaging[])');
  output.push('========================================');
  output.push(`Total Modules: ${courseData.modules.length}`);
  output.push('');
  
  courseData.modules.forEach((module: any, index: number) => {
    output.push(`--- MODULE ${index + 1} ---`);
    output.push(`id: ${module.id}`);
    output.push(`position: ${module.position}`);
    output.push(`published: ${module.published}`);
    output.push(`assignments.length: ${module.assignments.length}`);
    
    if (module.assignments.length > 0) {
      output.push(`--- MODULE ASSIGNMENTS ---`);
      module.assignments.forEach((assignment: any, assignIndex: number) => {
        output.push(`  [${assignIndex}] id: ${assignment.id}`);
        output.push(`  [${assignIndex}] position: ${assignment.position}`);
        output.push(`  [${assignIndex}] published: ${assignment.published}`);
        output.push(`  [${assignIndex}] title: "${assignment.title}"`);
        output.push(`  [${assignIndex}] type: "${assignment.type}"`);
        output.push(`  [${assignIndex}] url: "${assignment.url}"`);
        output.push(`  [${assignIndex}] content_details.points_possible: ${assignment.content_details.points_possible}`);
      });
    }
    
    output.push('');
  });
  
  // SUMMARY STATISTICS
  output.push('========================================');
  output.push('SUMMARY STATISTICS');
  output.push('========================================');
  const summary = courseData.getSummary();
  Object.entries(summary).forEach(([key, value]) => {
    output.push(`${key}: ${value}`);
  });
  output.push('');
  
  // OPTIMIZATION STATISTICS
  const studentsWithMissingAssignments = courseData.students.filter((s: any) => s.hasMissingAssignments());
  const studentsWithoutMissingAssignments = courseData.students.filter((s: any) => !s.hasMissingAssignments());
  
  output.push('========================================');
  output.push('OPTIMIZATION STATISTICS');
  output.push('========================================');
  output.push(`Total Students: ${courseData.students.length}`);
  output.push(`Students with Missing Assignments (API called): ${studentsWithMissingAssignments.length}`);
  output.push(`Students without Missing Assignments (API skipped): ${studentsWithoutMissingAssignments.length}`);
  output.push(`API Efficiency: ${studentsWithoutMissingAssignments.length > 0 ? ((studentsWithoutMissingAssignments.length / courseData.students.length) * 100).toFixed(1) + '% calls avoided' : 'No optimization possible'}`);
  output.push('');
  
  return output.join('\n');
}

// Run the script
outputRawCourseData().catch(console.error);