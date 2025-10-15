/**
 * Unit Tests for API-Call-Centric Staging Classes
 * 
 * Tests the staging classes functionality without making actual Canvas API calls
 */

import { CanvasCourseApiDataSet, ApiCallMetadata } from '../staging/api-call-staging';

describe('API Staging Classes (Unit Tests)', () => {
  const courseId = 12345;
  let dataSet: CanvasCourseApiDataSet;

  beforeEach(() => {
    dataSet = new CanvasCourseApiDataSet(courseId);
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

  test('Should initialize with correct course ID', () => {
    expect(dataSet.courseId).toBe(courseId);
    expect(dataSet.totalApiCalls).toBe(0);
    expect(dataSet.totalProcessingTime).toBe(0);
    expect(dataSet.constructionStartTime).toBeDefined();
  });

  test('Should add course info and reconstruct correctly', () => {
    const mockCourseData = {
      id: courseId,
      name: 'Test Course',
      course_code: 'TEST-101',
      workflow_state: 'available',
      start_at: '2025-01-01T00:00:00Z',
      end_at: '2025-06-01T00:00:00Z',
      calendar: { ics: 'http://example.com/calendar.ics' },
      created_at: '2024-12-01T00:00:00Z',
      updated_at: '2024-12-15T00:00:00Z',
    };

    dataSet.addCourseInfo(mockCourseData, createMockMetadata('/courses/12345', 1));

    // Validate course info was stored
    expect(dataSet.courseInfo).toBeDefined();
    expect(dataSet.courseInfo!.data).toHaveLength(1);
    expect(dataSet.courseInfo!.data[0]).toEqual(mockCourseData);
    expect(dataSet.totalApiCalls).toBe(1);

    // Test reconstruction
    const courseRecords = dataSet.reconstructCourses();
    expect(courseRecords).toHaveLength(1);
    
    // DEBUG: Show generated course record
    console.log('\n📋 DEBUG: Generated Course Record:');
    console.log(JSON.stringify(courseRecords[0], null, 2));
    
    expect(courseRecords[0]).toMatchObject({
      id: courseId,
      name: 'Test Course',
      course_code: 'TEST-101',
      calendar_ics: 'http://example.com/calendar.ics',
      workflow_state: 'available',
    });
  });

  test('Should add enrollments and reconstruct students correctly', () => {
    const mockEnrollmentData = [
      {
        id: 1,
        user_id: 2001,
        course_id: courseId,
        created_at: '2025-01-02T00:00:00Z',
        last_activity_at: '2025-01-10T00:00:00Z',
        grades: { current_score: 88.5, final_score: 90.0 },
        user: { 
          id: 2001, 
          name: 'Ada Lovelace', 
          login_id: 'ada', 
          email: 'ada@example.com', 
          sortable_name: 'Lovelace, Ada' 
        },
        enrollment_state: 'active',
      },
      {
        id: 2,
        user_id: 2002,
        course_id: courseId,
        created_at: '2025-01-02T00:00:00Z',
        last_activity_at: '2025-01-08T00:00:00Z',
        grades: { current_score: 92.0, final_score: 92.0 },
        user: { 
          id: 2002, 
          name: 'Grace Hopper', 
          login_id: 'grace', 
          email: 'grace@example.com', 
          sortable_name: 'Hopper, Grace' 
        },
        enrollment_state: 'active',
      },
    ];

    dataSet.addEnrollments(mockEnrollmentData, createMockMetadata('/courses/12345/enrollments', 2));

    // Validate enrollments were stored
    expect(dataSet.enrollments).toBeDefined();
    expect(dataSet.enrollments!.data).toHaveLength(2);
    expect(dataSet.totalApiCalls).toBe(1);

    // Test student reconstruction
    const studentRecords = dataSet.reconstructStudents();
    expect(studentRecords).toHaveLength(2);
    
    // DEBUG: Show generated student records
    console.log('\n👥 DEBUG: Generated Student Records:');
    studentRecords.forEach((student, index) => {
      console.log(`Student ${index + 1}:`, JSON.stringify(student, null, 2));
    });
    
    expect(studentRecords[0]).toMatchObject({
      student_id: 2001,
      user_id: 2001,
      name: 'Ada Lovelace',
      login_id: 'ada',
      email: 'ada@example.com',
      current_score: 88.5,
      final_score: 90.0,
    });

    // Test enrollment reconstruction
    const enrollmentRecords = dataSet.reconstructEnrollments();
    expect(enrollmentRecords).toHaveLength(2);
    
    // DEBUG: Show generated enrollment records
    console.log('\n📝 DEBUG: Generated Enrollment Records:');
    enrollmentRecords.forEach((enrollment, index) => {
      console.log(`Enrollment ${index + 1}:`, JSON.stringify(enrollment, null, 2));
    });
    
    expect(enrollmentRecords[0]).toMatchObject({
      student_id: 2001,
      course_id: courseId,
      enrollment_status: 'active',
    });
  });

  test('Should handle modules and assignments correctly', () => {
    const mockModulesData = [
      {
        id: 3001,
        course_id: courseId,
        name: 'Module A',
        position: 1,
        workflow_state: 'active',
        items: [
          {
            id: 777,
            module_id: 3001,
            type: 'Assignment',
            title: 'Homework 1',
            position: 1,
            url: `https://canvas.instructure.com/api/v1/courses/${courseId}/assignments/9001`,
            published: true,
            content_details: { points_possible: 10 },
          },
          {
            id: 778,
            module_id: 3001,
            type: 'Quiz',
            title: 'Quiz 1',
            position: 2,
            url: `https://canvas.instructure.com/api/v1/courses/${courseId}/quizzes/9002`,
            published: true,
            content_details: { points_possible: 20 },
          },
        ],
      },
    ];

    dataSet.addModules(mockModulesData, createMockMetadata('/courses/12345/modules', 1));

    // Validate modules were stored
    expect(dataSet.modules).toBeDefined();
    expect(dataSet.modules!.data).toHaveLength(1);
    expect(dataSet.totalApiCalls).toBe(1);

    // Test assignment reconstruction
    const assignmentRecords = dataSet.reconstructAssignments();
    expect(assignmentRecords).toHaveLength(2);
    
    // DEBUG: Show generated assignment records
    console.log('\n📚 DEBUG: Generated Assignment Records:');
    assignmentRecords.forEach((assignment, index) => {
      console.log(`Assignment ${index + 1}:`, JSON.stringify(assignment, null, 2));
    });
    
    expect(assignmentRecords[0]).toMatchObject({
      id: 9001,
      course_id: courseId,
      module_id: 3001,
      name: 'Homework 1',
      points_possible: 10,
      assignment_type: 'Assignment',
      published: true,
      module_position: 1,
    });

    expect(assignmentRecords[1]).toMatchObject({
      id: 9002,
      course_id: courseId,
      module_id: 3001,
      name: 'Quiz 1',
      points_possible: 20,
      assignment_type: 'Quiz',
      published: true,
      module_position: 2,
    });
  });

  test('Should handle empty data gracefully', () => {
    // Test reconstruction with no data
    expect(dataSet.reconstructCourses()).toHaveLength(0);
    expect(dataSet.reconstructStudents()).toHaveLength(0);
    expect(dataSet.reconstructAssignments()).toHaveLength(0);
    expect(dataSet.reconstructEnrollments()).toHaveLength(0);
  });

  test('Should track API calls and timing correctly', () => {
    const metadata1 = createMockMetadata('/courses/12345', 1);
    metadata1.responseTime = 150;
    metadata1.apiCallsUsed = 2;

    const metadata2 = createMockMetadata('/courses/12345/enrollments', 3);
    metadata2.responseTime = 250;
    metadata2.apiCallsUsed = 1;

    dataSet.addCourseInfo({
      id: courseId,
      name: 'Test',
      course_code: 'TEST',
      workflow_state: 'available',
      start_at: '',
      end_at: '',
      created_at: '',
      updated_at: '',
    }, metadata1);

    dataSet.addEnrollments([], metadata2);

    expect(dataSet.totalApiCalls).toBe(3); // 2 + 1
    expect(dataSet.totalProcessingTime).toBe(400); // 150 + 250
  });

  test('Should provide correct collection summary', async () => {
    // Add some data
    dataSet.addCourseInfo({
      id: courseId,
      name: 'Test Course',
      course_code: 'TEST',
      workflow_state: 'available',
      start_at: '',
      end_at: '',
      created_at: '',
      updated_at: '',
    }, createMockMetadata('/courses/12345', 1));

    dataSet.addEnrollments([
      {
        id: 1, user_id: 2001, course_id: courseId,
        created_at: '', last_activity_at: '',
        grades: { current_score: 85, final_score: 85 },
        user: { id: 2001, name: 'Test Student', login_id: 'test', email: 'test@example.com', sortable_name: 'Student, Test' },
        enrollment_state: 'active',
      }
    ], createMockMetadata('/courses/12345/enrollments', 1));

    // Wait a tiny bit to ensure construction time is measurable
    await new Promise(resolve => setTimeout(resolve, 1));
    dataSet.completeConstruction();

    const summary = dataSet.getCollectionSummary();
    
    // DEBUG: Show collection summary
    console.log('\n📈 DEBUG: Collection Summary:');
    console.log(JSON.stringify(summary, null, 2));
    
    expect(summary).toMatchObject({
      courseId: courseId,
      hasCompleteCourseInfo: true,
      enrollmentCount: 1,
      moduleCount: 0,
      studentAnalyticsCount: 0,
      totalApiCalls: 2,
      totalProcessingTime: 200, // 100 + 100 from mock metadata
    });

    expect(summary.constructionTime).toBeGreaterThanOrEqual(0);
  });
});