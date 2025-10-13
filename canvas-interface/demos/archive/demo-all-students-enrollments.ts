// Demo: Get all students in course and call enrollments endpoint
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

async function demoAllStudentsEnrollments() {
  console.log('🎯 Demo: All Students Enrollments Call');
  console.log('=====================================\n');

  const canvasUrl = process.env.CANVAS_URL;
  const canvasToken = process.env.CANVAS_TOKEN;

  if (!canvasUrl || !canvasToken) {
    console.error('❌ Missing Canvas configuration');
    return;
  }

  const config: CanvasApiConfig = {
    baseUrl: canvasUrl,
    token: canvasToken,
    rateLimitRequestsPerHour: 600,
    accountType: 'free',
  };

  const gateway = new CanvasGatewayHttp(config);
  const courseId = 7982015; // JDU 1st Section

  try {
    console.log('📋 Step 1: Getting all students in the course...');
    
    // Get ALL students from the course
    const studentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${courseId}/users`,
      {
        params: {
          enrollment_type: 'student',
          enrollment_state: 'active',
          per_page: 100
        }
      }
    );

    const allStudents = (studentsResponse.data as any[]) || [];
    console.log(`✅ Found ${allStudents.length} students in course ${courseId}`);

    // Show first few students
    console.log('\n👥 First 5 students:');
    allStudents.slice(0, 5).forEach((student, index) => {
      console.log(`   ${index + 1}. ${student.name} (ID: ${student.id})`);
    });

    if (allStudents.length > 5) {
      console.log(`   ... and ${allStudents.length - 5} more students`);
    }

    console.log('\n📊 Step 2: Calling enrollments endpoint with ALL student IDs...');
    
    // Build the user_id array parameters
    const allStudentIds = allStudents.map(student => student.id);
    console.log(`🎯 Building URL with ${allStudentIds.length} user IDs...`);

    // Create the enrollments call with all student IDs
    const enrollmentsParams = {
      include: ['grades'],
      per_page: 100
    };

    // Add all user IDs as array parameters
    allStudentIds.forEach((studentId, index) => {
      (enrollmentsParams as any)[`user_id[${index}]`] = studentId;
    });

    console.log(`📞 Making API call to /enrollments with ${allStudentIds.length} student IDs...`);
    const startTime = Date.now();

    const enrollmentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${courseId}/enrollments`,
      {
        params: enrollmentsParams
      }
    );

    const responseTime = Date.now() - startTime;
    console.log(`⚡ Response received in ${responseTime}ms`);
    console.log(`🔗 Full URL: ${enrollmentsResponse.url}`);

    const enrollments = (enrollmentsResponse.data as any[]) || [];
    console.log(`✅ Retrieved ${enrollments.length} enrollment records`);

    console.log('\n🎯 Step 3: Processing enrollment data...');

    if (enrollments.length > 0) {
      console.log('\n📊 Student Grade Summary:');
      
      // Process each enrollment
      enrollments.forEach((enrollment, index) => {
        if (enrollment.type === 'StudentEnrollment' && enrollment.grades) {
          const studentName = allStudents.find(s => s.id === enrollment.user_id)?.name || 'Unknown';
          const grades = enrollment.grades;
          
          console.log(`   ${index + 1}. ${studentName} (ID: ${enrollment.user_id}):`);
          console.log(`      Current Grade: ${grades.current_grade || 'Not set'}`);
          console.log(`      Current Score: ${grades.current_score || 'Not set'}%`);
          console.log(`      Final Grade: ${grades.final_grade || 'Not set'}`);
          console.log(`      Final Score: ${grades.final_score || 'Not set'}%`);
          
          if (index >= 4) { // Show first 5 students only
            if (enrollments.length > 5) {
              console.log(`   ... and ${enrollments.length - 5} more students`);
            }
            return;
          }
        }
      });
    }

    console.log('\n🎉 SUCCESS! Key Findings:');
    console.log('=========================');
    console.log(`✅ Single API call retrieved ${enrollments.length} enrollment records`);
    console.log(`⚡ Response time: ${responseTime}ms`);
    console.log(`📊 Students with grades: ${enrollments.filter(e => e.grades).length}`);
    console.log(`🎯 Average time per student: ${(responseTime / allStudents.length).toFixed(1)}ms`);

    // Compare to alternative approaches
    console.log('\n💰 Efficiency Comparison:');
    console.log(`🔴 Individual calls: ${allStudents.length} API calls (1 per student)`);
    console.log(`🟢 Bulk call: 1 API call (all students at once)`);
    console.log(`💰 API calls saved: ${allStudents.length - 1}`);
    console.log(`🚀 Efficiency gain: ${((allStudents.length - 1) / allStudents.length * 100).toFixed(1)}% fewer calls`);

  } catch (error) {
    console.error('💥 Demo failed:', error);
    
    console.log('\n🔧 Possible Issues:');
    console.log('===================');
    console.log('1. Too many user IDs in one call (Canvas may have limits)');
    console.log('2. URL too long (browser/server limits)');
    console.log('3. Canvas API rate limiting');
    console.log('4. Permission issues with bulk enrollment access');
    
    console.log('\n💡 Solutions:');
    console.log('1. Try with fewer students (batch processing)');
    console.log('2. Use POST instead of GET for large parameter lists');
    console.log('3. Implement retry logic with exponential backoff');
  }
}

// Run the demo
demoAllStudentsEnrollments().catch(console.error);