/**
 * Integration Tests for API-Call-Centric Staging Architecture
 * 
 * These tests make REAL Canvas API calls to validate the staging classes
 * work correctly with your actual Canvas environment.
 */

import dotenv from 'dotenv';
dotenv.config();

import { CanvasCourseApiDataSet } from '../staging/api-call-staging';
import { CanvasBulkApiDataManager } from '../staging/bulk-api-call-staging';
import { CanvasDataConstructor } from '../staging/canvas-data-constructor';

// Test configuration
const TEST_COURSE_ID = 7982015; // Your JDU course
const TEST_TIMEOUT = 30000; // 30 second timeout for API calls

describe('API Staging Integration Tests (Real Canvas API)', () => {
  let dataConstructor: CanvasDataConstructor;

  beforeAll(() => {
    // Ensure Canvas credentials are available
    if (!process.env.CANVAS_URL || !process.env.CANVAS_TOKEN) {
      throw new Error('Missing Canvas credentials. Set CANVAS_URL and CANVAS_TOKEN in .env file');
    }
    
    dataConstructor = new CanvasDataConstructor();
  });

  describe('Single Course API Data Set', () => {
    let courseDataSet: CanvasCourseApiDataSet;

    beforeEach(() => {
      courseDataSet = new CanvasCourseApiDataSet(TEST_COURSE_ID);
    });

    test('Should rebuild course info from real Canvas API', async () => {
      console.log(`🧪 Testing course info rebuild for course ${TEST_COURSE_ID}`);
      
      await courseDataSet.rebuildCourseInfo(dataConstructor);
      
      // Validate course info was populated
      expect(courseDataSet.courseInfo).toBeDefined();
      expect(courseDataSet.courseInfo!.data).toHaveLength(1);
      expect(courseDataSet.courseInfo!.data[0].id).toBe(TEST_COURSE_ID);
      expect(courseDataSet.courseInfo!.metadata.success).toBe(true);
      expect(courseDataSet.courseInfo!.metadata.apiCallsUsed).toBeGreaterThan(0);
      
      console.log(`✅ Course info: "${courseDataSet.courseInfo!.data[0].name}" (${courseDataSet.courseInfo!.data[0].course_code})`);
      
      // Test course reconstruction
      const courseRecords = courseDataSet.reconstructCourses();
      expect(courseRecords).toHaveLength(1);
      expect(courseRecords[0]).toMatchObject({
        id: TEST_COURSE_ID,
        name: expect.any(String),
        course_code: expect.any(String),
        last_synced: expect.any(String)
      });
      
      console.log(`✅ Course record reconstructed: ${courseRecords[0].name}`);
    }, TEST_TIMEOUT);

    test('Should rebuild enrollments from real Canvas API', async () => {
      console.log(`🧪 Testing enrollments rebuild for course ${TEST_COURSE_ID}`);
      
      await courseDataSet.rebuildEnrollments(dataConstructor);
      
      // Validate enrollments were populated
      expect(courseDataSet.enrollments).toBeDefined();
      expect(courseDataSet.enrollments!.data.length).toBeGreaterThan(0);
      expect(courseDataSet.enrollments!.metadata.success).toBe(true);
      
      const enrollmentCount = courseDataSet.enrollments!.data.length;
      console.log(`✅ Found ${enrollmentCount} enrollments`);
      
      // Test students reconstruction
      const studentRecords = courseDataSet.reconstructStudents();
      expect(studentRecords).toHaveLength(enrollmentCount);
      
      // Validate first student record structure
      const firstStudent = studentRecords[0];
      expect(firstStudent).toMatchObject({
        student_id: expect.any(Number),
        user_id: expect.any(Number),
        name: expect.any(String),
        login_id: expect.any(String),
        email: expect.any(String),
        current_score: expect.any(Number),
        final_score: expect.any(Number),
        last_synced: expect.any(String)
      });
      
      console.log(`✅ First student: ${firstStudent.name} (Score: ${firstStudent.current_score})`);
      
      // Test enrollments reconstruction
      const enrollmentRecords = courseDataSet.reconstructEnrollments();
      expect(enrollmentRecords).toHaveLength(enrollmentCount);
      
      console.log(`✅ ${enrollmentRecords.length} enrollment records reconstructed`);
    }, TEST_TIMEOUT);

    test('Should rebuild assignments from real Canvas API', async () => {
      console.log(`🧪 Testing assignments rebuild for course ${TEST_COURSE_ID}`);
      
      await courseDataSet.rebuildAssignments(dataConstructor);
      
      // Validate modules were populated
      expect(courseDataSet.modules).toBeDefined();
      expect(courseDataSet.modules!.metadata.success).toBe(true);
      
      const moduleCount = courseDataSet.modules!.data.length;
      console.log(`✅ Found ${moduleCount} modules`);
      
      // Test assignments reconstruction
      const assignmentRecords = courseDataSet.reconstructAssignments();
      expect(assignmentRecords.length).toBeGreaterThan(0);
      
      // Validate assignment record structure
      const firstAssignment = assignmentRecords[0];
      expect(firstAssignment).toMatchObject({
        id: expect.any(Number),
        course_id: TEST_COURSE_ID,
        module_id: expect.any(Number),
        name: expect.any(String),
        points_possible: expect.any(Number),
        assignment_type: expect.any(String),
        published: expect.any(Boolean),
        last_synced: expect.any(String)
      });
      
      console.log(`✅ First assignment: "${firstAssignment.name}" (${firstAssignment.points_possible} pts)`);
      console.log(`✅ Total assignments reconstructed: ${assignmentRecords.length}`);
    }, TEST_TIMEOUT);

    test('Should complete full course data collection workflow', async () => {
      console.log(`🧪 Testing complete workflow for course ${TEST_COURSE_ID}`);
      
      const startTime = Date.now();
      
      // Execute complete workflow
      await courseDataSet.rebuildCourseInfo(dataConstructor);
      await courseDataSet.rebuildEnrollments(dataConstructor);
      await courseDataSet.rebuildAssignments(dataConstructor);
      
      courseDataSet.completeConstruction();
      
      const endTime = Date.now();
      const totalTime = endTime - startTime;
      
      // Validate all data is present
      const summary = courseDataSet.getCollectionSummary();
      
      expect(summary.hasCompleteCourseInfo).toBe(true);
      expect(summary.enrollmentCount).toBeGreaterThan(0);
      expect(summary.moduleCount).toBeGreaterThan(0);
      expect(summary.totalApiCalls).toBeGreaterThan(0);
      expect(summary.constructionTime).toBeGreaterThan(0);
      
      console.log(`✅ Complete workflow summary:`);
      console.log(`   Course: ${summary.hasCompleteCourseInfo ? '✓' : '✗'}`);
      console.log(`   Students: ${summary.enrollmentCount}`);
      console.log(`   Modules: ${summary.moduleCount}`);
      console.log(`   API calls: ${summary.totalApiCalls}`);
      console.log(`   Total time: ${totalTime}ms`);
      console.log(`   Construction time: ${summary.constructionTime}ms`);
      
      // Test complete reconstruction
      const courseRecords = courseDataSet.reconstructCourses();
      const studentRecords = courseDataSet.reconstructStudents();
      const assignmentRecords = courseDataSet.reconstructAssignments();
      const enrollmentRecords = courseDataSet.reconstructEnrollments();
      
      expect(courseRecords).toHaveLength(1);
      expect(studentRecords.length).toBeGreaterThan(0);
      expect(assignmentRecords.length).toBeGreaterThan(0);
      expect(enrollmentRecords.length).toBeGreaterThan(0);
      
      console.log(`✅ Reconstruction complete:`);
      console.log(`   Courses: ${courseRecords.length}`);
      console.log(`   Students: ${studentRecords.length}`);
      console.log(`   Assignments: ${assignmentRecords.length}`);
      console.log(`   Enrollments: ${enrollmentRecords.length}`);
    }, TEST_TIMEOUT);
  });

  describe('Bulk Canvas Data Manager', () => {
    let bulkManager: CanvasBulkApiDataManager;

    beforeEach(() => {
      bulkManager = new CanvasBulkApiDataManager();
    });

    test('Should discover all available courses', async () => {
      console.log('🧪 Testing bulk course discovery');
      
      await bulkManager.rebuildAllCoursesList(dataConstructor);
      
      expect(bulkManager.allCoursesList).toBeDefined();
      expect(bulkManager.allCoursesList!.data.length).toBeGreaterThan(0);
      expect(bulkManager.allCoursesList!.metadata.success).toBe(true);
      
      const courseCount = bulkManager.allCoursesList!.data.length;
      console.log(`✅ Discovered ${courseCount} available courses`);
      
      // Test course reconstruction from bulk list
      const allCourseRecords = bulkManager.reconstructAllCourses();
      expect(allCourseRecords).toHaveLength(courseCount);
      
      // Show sample courses
      const sampleCourses = allCourseRecords.slice(0, 3);
      console.log(`✅ Sample courses:`);
      sampleCourses.forEach((course, index) => {
        console.log(`   ${index + 1}. ${course.name} (${course.course_code})`);
      });
    }, TEST_TIMEOUT);

    test('Should execute limited bulk workflow', async () => {
      console.log('🧪 Testing limited bulk workflow (max 2 courses)');
      
      const workflowResult = await bulkManager.executeBulkWorkflow(dataConstructor, {
        workflowStates: ['available'],
        maxCourses: 2  // Limit to 2 courses to avoid overwhelming Canvas API
      });
      
      expect(workflowResult.success).toBe(true);
      expect(workflowResult.coursesDiscovered).toBeGreaterThan(0);
      expect(workflowResult.coursesProcessed).toBeLessThanOrEqual(2);
      expect(workflowResult.totalApiCalls).toBeGreaterThan(0);
      expect(workflowResult.errors).toHaveLength(0);
      
      console.log(`✅ Bulk workflow results:`);
      console.log(`   Success: ${workflowResult.success}`);
      console.log(`   Courses discovered: ${workflowResult.coursesDiscovered}`);
      console.log(`   Courses processed: ${workflowResult.coursesProcessed}`);
      console.log(`   Total students: ${workflowResult.totalStudents}`);
      console.log(`   Total assignments: ${workflowResult.totalAssignments}`);
      console.log(`   Total API calls: ${workflowResult.totalApiCalls}`);
      console.log(`   Processing time: ${workflowResult.totalProcessingTime}ms`);
      console.log(`   Avg time per course: ${workflowResult.averageTimePerCourse.toFixed(1)}ms`);
      
      // Test bulk reconstruction
      const allStudents = bulkManager.reconstructAllStudents();
      const allAssignments = bulkManager.reconstructAllAssignments();
      const allEnrollments = bulkManager.reconstructAllEnrollments();
      
      expect(allStudents.length).toBeGreaterThan(0);
      expect(allAssignments.length).toBeGreaterThan(0);
      expect(allEnrollments.length).toBeGreaterThan(0);
      
      console.log(`✅ Bulk reconstruction:`);
      console.log(`   All students: ${allStudents.length}`);
      console.log(`   All assignments: ${allAssignments.length}`);
      console.log(`   All enrollments: ${allEnrollments.length}`);
      
      // Validate bulk summary
      const bulkSummary = bulkManager.getBulkSummary();
      expect(bulkSummary.coursesDiscovered).toBeGreaterThan(0);
      expect(bulkSummary.courseDataSetsInitialized).toBe(workflowResult.coursesProcessed);
      expect(bulkSummary.totalApiCalls).toBeGreaterThan(0);
      
      console.log(`✅ Bulk summary validated`);
    }, TEST_TIMEOUT * 2); // Double timeout for bulk operations
  });

  describe('Integration with Existing Canvas Data Constructor', () => {
    test('Should work with existing CanvasDataConstructor methods', async () => {
      console.log('🧪 Testing integration with existing CanvasDataConstructor');
      
      // Test that our new staging classes can use existing constructor methods
      const courseDataSet = new CanvasCourseApiDataSet(TEST_COURSE_ID);
      
      // These methods should exist and work with our staging classes
      expect(dataConstructor.getCourseInfo).toBeDefined();
      expect(dataConstructor.getAllActiveCoursesStaging).toBeDefined();
      
      // Test course info method
      const courseInfo = await dataConstructor.getCourseInfo(TEST_COURSE_ID);
      expect(courseInfo).toMatchObject({
        id: TEST_COURSE_ID,
        name: expect.any(String),
        course_code: expect.any(String)
      });
      
      console.log(`✅ getCourseInfo works: ${courseInfo.name}`);
      
      // Test all courses method
      const allCourses = await dataConstructor.getAllActiveCoursesStaging();
      expect(Array.isArray(allCourses)).toBe(true);
      expect(allCourses.length).toBeGreaterThan(0);
      
      console.log(`✅ getAllActiveCoursesStaging works: ${allCourses.length} courses`);
      
      console.log(`✅ Integration with existing CanvasDataConstructor confirmed`);
    }, TEST_TIMEOUT);
  });

  describe('Error Handling and Edge Cases', () => {
    test('Should handle invalid course ID gracefully', async () => {
      console.log('🧪 Testing error handling with invalid course ID');
      
      const invalidCourseId = 999999999;
      
      // Test that CanvasDataConstructor.getCourseInfo returns null for invalid course
      const courseInfo = await dataConstructor.getCourseInfo(invalidCourseId);
      expect(courseInfo).toBeNull();
      
      // Test that staging class handles null course info gracefully
      const courseDataSet = new CanvasCourseApiDataSet(invalidCourseId);
      
      // This should complete without throwing, but result in no course data
      await courseDataSet.rebuildCourseInfo(dataConstructor);
      
      // Verify that no course was reconstructed (graceful handling)
      const courses = courseDataSet.reconstructCourses();
      expect(courses).toHaveLength(0);
      
      console.log('✅ Invalid course ID handled gracefully');
    });

    test('Should handle empty reconstruction gracefully', () => {
      console.log('🧪 Testing reconstruction with no data');
      
      const courseDataSet = new CanvasCourseApiDataSet(TEST_COURSE_ID);
      
      // Should return empty arrays when no data is present
      expect(courseDataSet.reconstructCourses()).toHaveLength(0);
      expect(courseDataSet.reconstructStudents()).toHaveLength(0);
      expect(courseDataSet.reconstructAssignments()).toHaveLength(0);
      expect(courseDataSet.reconstructEnrollments()).toHaveLength(0);
      
      console.log('✅ Empty reconstruction handled gracefully');
    });
  });
});