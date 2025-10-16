/**
 * API Field Inspection Test
 * 
 * This test inspects the raw Canvas API responses to identify what fields
 * are available vs. what fields are being lost in our data pipeline.
 */

import dotenv from 'dotenv';
dotenv.config({ path: '../.env' });

import { CanvasCalls } from '../core/canvas-calls';

async function inspectCanvasApiFields() {
  try {
    console.log('🔍 Canvas API Field Inspection Test');
    console.log('=====================================\n');
    
    const canvasCalls = new CanvasCalls();
    const gateway = (canvasCalls as any).gateway;
    
    // 1. Inspect course data
    console.log('1. COURSE DATA INSPECTION');
    console.log('-------------------------');
    const courseResponse = await gateway.getClient().requestWithFullResponse('courses/7982015', {});
    const course = courseResponse.data;
    
    console.log('Available course fields:');
    console.log(Object.keys(course).sort().join(', '));
    
    console.log('\nCourse field values for missing data:');
    console.log('- calendar:', course.calendar);
    console.log('- total_students:', course.total_students);
    console.log('- syllabus_body:', course.syllabus_body ? 'Present' : 'Null/Missing');
    console.log('- public_syllabus:', course.public_syllabus);
    console.log('- public_syllabus_to_auth:', course.public_syllabus_to_auth);
    console.log('- enrollments:', course.enrollments);
    
    // 2. Inspect enrollment data for student last_activity
    console.log('\n2. ENROLLMENT DATA INSPECTION');
    console.log('-----------------------------');
    const enrollmentResponse = await gateway.getClient().requestWithFullResponse(
      'courses/7982015/enrollments',
      {
        params: {
          type: ['StudentEnrollment'],
          state: ['active'],
          include: ['user'],
          per_page: 3  // Get a few samples
        }
      }
    );
    
    const enrollments = enrollmentResponse.data;
    if (enrollments && enrollments.length > 0) {
      console.log('Available enrollment fields (sample):');
      console.log(Object.keys(enrollments[0]).sort().join(', '));
      
      console.log('\nEnrollment field values for missing data:');
      console.log('- last_activity_at:', enrollments[0].last_activity_at);
      console.log('- last_attended_at:', enrollments[0].last_attended_at);
      console.log('- current_score:', enrollments[0].current_score);
      console.log('- final_score:', enrollments[0].final_score);
      
      if (enrollments[0].user) {
        console.log('\nUser object fields:');
        console.log(Object.keys(enrollments[0].user).sort().join(', '));
        console.log('- email:', enrollments[0].user.email);
        console.log('- last_login:', enrollments[0].user.last_login);
      }
    }
    
    // 3. Check if we need different API calls to get missing data
    console.log('\n3. ALTERNATIVE API ENDPOINTS CHECK');
    console.log('----------------------------------');
    
    // Try course with includes
    console.log('Testing course endpoint with includes...');
    const courseWithIncludes = await gateway.getClient().requestWithFullResponse(
      'courses/7982015',
      {
        params: {
          include: ['total_students', 'teachers', 'syllabus_body', 'public_description']
        }
      }
    );
    
    console.log('Fields with includes:', Object.keys(courseWithIncludes.data).sort().join(', '));
    console.log('- total_students (with include):', courseWithIncludes.data.total_students);
    console.log('- syllabus_body (with include):', courseWithIncludes.data.syllabus_body ? 'Present' : 'Null/Missing');
    
    // Try enrollments with more includes
    console.log('\nTesting enrollments endpoint with more includes...');
    const enrollmentWithIncludes = await gateway.getClient().requestWithFullResponse(
      'courses/7982015/enrollments',
      {
        params: {
          type: ['StudentEnrollment'],
          state: ['active'],
          include: ['user', 'grades', 'last_activity_at'],
          per_page: 2
        }
      }
    );
    
    if (enrollmentWithIncludes.data && enrollmentWithIncludes.data.length > 0) {
      console.log('Enrollment fields with more includes:');
      console.log(Object.keys(enrollmentWithIncludes.data[0]).sort().join(', '));
      console.log('- last_activity_at (with include):', enrollmentWithIncludes.data[0].last_activity_at);
    }
    
    console.log('\n✅ API Field Inspection Complete');
    
  } catch (error) {
    console.error('❌ API Field Inspection Failed:', error.message);
    if (error.response) {
      console.error('Response status:', error.response.status);
      console.error('Response data:', error.response.data);
    }
  }
}

// Run the inspection
if (require.main === module) {
  inspectCanvasApiFields().catch(console.error);
}

export { inspectCanvasApiFields };