/**
 * Unit Tests for Bulk API-Call-Centric Staging Manager
 * 
 * Tests the bulk staging manager functionality without making Canvas API calls
 */

import { CanvasBulkApiDataManager, CourseListRecord } from '../staging/bulk-api-call-staging';
import { ApiCallMetadata } from '../staging/api-call-staging';

describe('Bulk API Staging Manager (Unit Tests)', () => {
  let bulkManager: CanvasBulkApiDataManager;

  beforeEach(() => {
    bulkManager = new CanvasBulkApiDataManager();
  });

  // Helper function to create mock metadata
  function createMockMetadata(endpoint: string, recordCount: number): ApiCallMetadata {
    return {
      endpoint,
      timestamp: new Date(),
      responseTime: 100,
      recordCount,
      apiCallsUsed: 1,
      success: true,
    };
  }

  test('Should initialize with empty state', () => {
    expect(bulkManager.allCoursesList).toBeUndefined();
    expect(bulkManager.courseDataSets.size).toBe(0);
    expect(bulkManager.totalApiCalls).toBe(0);
    expect(bulkManager.totalProcessingTime).toBe(0);
    expect(bulkManager.constructionStartTime).toBeDefined();
  });

  test('Should add course list and initialize data sets', () => {
    const mockCourseList: CourseListRecord[] = [
      {
        id: 12345,
        name: 'Algebra I',
        course_code: 'ALG-101',
        workflow_state: 'available',
        start_at: '2025-01-01T00:00:00Z',
        end_at: '2025-06-01T00:00:00Z',
        calendar: { ics: 'http://example.com/calendar.ics' },
        created_at: '2024-12-01T00:00:00Z',
        updated_at: '2024-12-15T00:00:00Z',
      },
      {
        id: 12346,
        name: 'Geometry',
        course_code: 'GEO-101',
        workflow_state: 'available',
        start_at: '2025-01-01T00:00:00Z',
        end_at: '2025-06-01T00:00:00Z',
        calendar: { ics: 'http://example.com/calendar2.ics' },
        created_at: '2024-12-01T00:00:00Z',
        updated_at: '2024-12-15T00:00:00Z',
      },
    ];

    bulkManager.addAllCoursesList(mockCourseList, createMockMetadata('/courses', 2));

    // Validate course list was stored
    expect(bulkManager.allCoursesList).toBeDefined();
    expect(bulkManager.allCoursesList!.data).toHaveLength(2);
    expect(bulkManager.totalApiCalls).toBe(1);

    // Test course reconstruction
    const courseRecords = bulkManager.reconstructAllCourses();
    expect(courseRecords).toHaveLength(2);
    
    // DEBUG: Show bulk course reconstruction
    console.log('\n🏫 DEBUG: Bulk Course Records:');
    courseRecords.forEach((course, index) => {
      console.log(`Course ${index + 1}:`, JSON.stringify(course, null, 2));
    });
    
    expect(courseRecords[0]).toMatchObject({
      id: 12345,
      name: 'Algebra I',
      course_code: 'ALG-101',
      calendar_ics: 'http://example.com/calendar.ics',
      workflow_state: 'available',
    });

    expect(courseRecords[1]).toMatchObject({
      id: 12346,
      name: 'Geometry',
      course_code: 'GEO-101',
    });
  });

  test('Should initialize and manage course data sets', () => {
    const courseIds = [12345, 12346, 12347];
    
    bulkManager.initializeCourseDataSets(courseIds);
    
    expect(bulkManager.courseDataSets.size).toBe(3);
    
    // Test getting individual course data sets
    const course1DataSet = bulkManager.getCourseDataSet(12345);
    const course2DataSet = bulkManager.getCourseDataSet(12346);
    
    expect(course1DataSet.courseId).toBe(12345);
    expect(course2DataSet.courseId).toBe(12346);
    
    // Test getting new course data set
    const course4DataSet = bulkManager.getCourseDataSet(12348);
    expect(bulkManager.courseDataSets.size).toBe(4);
    expect(course4DataSet.courseId).toBe(12348);
  });

  test('Should provide correct bulk summary', async () => {
    const mockCourseList: CourseListRecord[] = [
      {
        id: 12345,
        name: 'Test Course',
        course_code: 'TEST-101',
        workflow_state: 'available',
        start_at: '',
        end_at: '',
        created_at: '',
        updated_at: '',
      },
    ];

    bulkManager.addAllCoursesList(mockCourseList, createMockMetadata('/courses', 1));
    bulkManager.initializeCourseDataSets([12345]);
    
    // Add some data to the course data set
    const courseDataSet = bulkManager.getCourseDataSet(12345);
    courseDataSet.addCourseInfo({
      id: 12345,
      name: 'Test Course',
      course_code: 'TEST-101',
      workflow_state: 'available',
      start_at: '',
      end_at: '',
      created_at: '',
      updated_at: '',
    }, createMockMetadata('/courses/12345', 1));
    
    await new Promise(resolve => setTimeout(resolve, 1));
    bulkManager.completeConstruction();

    const summary = bulkManager.getBulkSummary();
    
    // DEBUG: Show bulk summary
    console.log('\n📈 DEBUG: Bulk Manager Summary:');
    console.log(JSON.stringify(summary, null, 2));
    
    expect(summary).toMatchObject({
      coursesDiscovered: 1,
      courseDataSetsInitialized: 1,
      totalApiCalls: 1,
      totalProcessingTime: 100,
    });

    expect(summary.constructionTime).toBeGreaterThanOrEqual(0);
    expect(summary.individualCourseSummaries).toHaveLength(1);
    expect(summary.individualCourseSummaries[0].courseId).toBe(12345);
  });

  test('Should identify ready courses correctly', () => {
    bulkManager.initializeCourseDataSets([12345, 12346]);
    
    // Course 12345 has complete data
    const course1DataSet = bulkManager.getCourseDataSet(12345);
    course1DataSet.addCourseInfo({
      id: 12345,
      name: 'Complete Course',
      course_code: 'COMPLETE-101',
      workflow_state: 'available',
      start_at: '',
      end_at: '',
      created_at: '',
      updated_at: '',
    }, createMockMetadata('/courses/12345', 1));
    
    course1DataSet.addEnrollments([{
      id: 1,
      user_id: 2001,
      course_id: 12345,
      created_at: '2025-01-01T00:00:00Z',
      last_activity_at: '2025-01-01T00:00:00Z',
      grades: { current_score: 85, final_score: 85 },
      user: { id: 2001, name: 'Test Student', login_id: 'test', email: 'test@example.com', sortable_name: 'Student, Test' },
      enrollment_state: 'active',
    }], createMockMetadata('/courses/12345/enrollments', 1));

    // Course 12346 has no enrollments (incomplete)
    const course2DataSet = bulkManager.getCourseDataSet(12346);
    course2DataSet.addCourseInfo({
      id: 12346,
      name: 'Incomplete Course',
      course_code: 'INCOMPLETE-101',
      workflow_state: 'available',
      start_at: '',
      end_at: '',
      created_at: '',
      updated_at: '',
    }, createMockMetadata('/courses/12346', 1));

    const readyCourses = bulkManager.getReadyCourses();
    expect(readyCourses).toEqual([12345]);
  });

  test('Should reconstruct all data from course data sets', () => {
    // Initialize with multiple courses
    bulkManager.initializeCourseDataSets([12345, 12346]);
    
    // Add data to first course
    const course1DataSet = bulkManager.getCourseDataSet(12345);
    course1DataSet.addEnrollments([{
      id: 1,
      user_id: 2001,
      course_id: 12345,
      created_at: '2025-01-01T00:00:00Z',
      last_activity_at: '2025-01-01T00:00:00Z',
      grades: { current_score: 85, final_score: 85 },
      user: { id: 2001, name: 'Student One', login_id: 'student1', email: 'student1@example.com', sortable_name: 'One, Student' },
      enrollment_state: 'active',
    }], createMockMetadata('/courses/12345/enrollments', 1));

    // Add data to second course
    const course2DataSet = bulkManager.getCourseDataSet(12346);
    course2DataSet.addEnrollments([{
      id: 2,
      user_id: 2002,
      course_id: 12346,
      created_at: '2025-01-01T00:00:00Z',
      last_activity_at: '2025-01-01T00:00:00Z',
      grades: { current_score: 92, final_score: 92 },
      user: { id: 2002, name: 'Student Two', login_id: 'student2', email: 'student2@example.com', sortable_name: 'Two, Student' },
      enrollment_state: 'active',
    }], createMockMetadata('/courses/12346/enrollments', 1));

    // Test bulk reconstruction
    const allStudents = bulkManager.reconstructAllStudents();
    const allEnrollments = bulkManager.reconstructAllEnrollments();
    
    // DEBUG: Show bulk reconstruction results
    console.log('\n🔄 DEBUG: Bulk Reconstruction Results:');
    console.log('All Students:');
    allStudents.forEach((student, index) => {
      console.log(`  Student ${index + 1}:`, JSON.stringify(student, null, 2));
    });
    console.log('All Enrollments:');
    allEnrollments.forEach((enrollment, index) => {
      console.log(`  Enrollment ${index + 1}:`, JSON.stringify(enrollment, null, 2));
    });
    
    expect(allStudents).toHaveLength(2);
    expect(allEnrollments).toHaveLength(2);
    
    expect(allStudents[0].name).toBe('Student One');
    expect(allStudents[1].name).toBe('Student Two');
    
    expect(allEnrollments[0].course_id).toBe(12345);
    expect(allEnrollments[1].course_id).toBe(12346);
  });
});