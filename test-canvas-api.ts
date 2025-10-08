/**
 * Canvas API Real Test Script
 * Tests our Canvas infrastructure with actual API calls
 */

// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

async function testCanvasApi(): Promise<void> {
  console.log('🧪 Canvas API Test Suite Starting...\n');

  // Get environment variables
  const canvasUrl = process.env.CANVAS_URL;
  const canvasToken = process.env.CANVAS_TOKEN;

  if (!canvasUrl || !canvasToken) {
    console.error('❌ Error: Missing Canvas configuration');
    console.log('Please set CANVAS_URL and CANVAS_TOKEN environment variables');
    console.log('Example: CANVAS_URL=https://your-school.instructure.com');
    console.log('         CANVAS_TOKEN=your_api_token_here');
    return;
  }

  console.log('📋 Configuration:');
  console.log(`   Canvas URL: ${canvasUrl}`);
  console.log(`   Token: ${canvasToken.substring(0, 10)}...`);
  console.log('');

  // Initialize Canvas Gateway
  const config: CanvasApiConfig = {
    baseUrl: canvasUrl,
    token: canvasToken,
    rateLimitRequestsPerHour: 600, // Canvas Free default
    accountType: 'free',
  };

  const gateway = new CanvasGatewayHttp(config);

  try {
    // Test 1: Get all courses
    console.log('🔍 Test 1: Getting all courses...');
    const startTime = Date.now();
    
    const coursesResponse = await gateway.coursesApi.getAllCourses({
      state: 'available',
      perPage: 100,
    });

    const elapsed = Date.now() - startTime;
    
    if (coursesResponse.data) {
      console.log(`✅ Success! Found ${coursesResponse.data.length} courses (${elapsed}ms)`);
      
      // Display course information
      console.log('\n📚 Courses found:');
      coursesResponse.data.forEach((course, index) => {
        console.log(`   ${index + 1}. ${course.name} (ID: ${course.id})`);
        console.log(`      Code: ${course.course_code}`);
        console.log(`      State: ${course.workflow_state}`);
        console.log(`      Students: ${course.total_students || 'Unknown'}`);
        console.log('');
      });

      // Test 2: Get API status
      console.log('📊 Test 2: API Status Check...');
      const apiStatus = gateway.getApiStatus();
      
      console.log('Rate Limit Status:');
      console.log(`   Requests in window: ${apiStatus.rateLimitStatus.requestsInWindow}`);
      console.log(`   Max requests: ${apiStatus.rateLimitStatus.maxRequests}`);
      console.log(`   Window resets: ${apiStatus.rateLimitStatus.windowResetTime.toLocaleString()}`);
      
      console.log('Scheduler Metrics:');
      console.log(`   Success rate: ${apiStatus.schedulerMetrics.successRate.toFixed(1)}%`);
      console.log(`   Average response time: ${apiStatus.schedulerMetrics.averageResponseTime.toFixed(0)}ms`);
      console.log(`   Total requests: ${apiStatus.schedulerMetrics.totalRequests}`);
      
      console.log('Performance Summary:');
      console.log(`   Status: ${apiStatus.performanceSummary.status}`);
      console.log(`   Can handle 8 courses: ${apiStatus.performanceSummary.canHandle8Courses}`);
      console.log(`   Estimated sync time: ${apiStatus.performanceSummary.estimatedSyncTime}s`);

      // Test 3: Curriculum test with available courses
      if (coursesResponse.data.length > 0) {
        console.log('\n🎯 Test 3: Curriculum Sync Test...');
        
        // Take up to 3 courses for testing (safe number)
        const testCourseIds = coursesResponse.data
          .slice(0, Math.min(3, coursesResponse.data.length))
          .map(course => course.id);

        console.log(`Testing with courses: ${testCourseIds.join(', ')}`);

        const curriculumConfig = {
          id: 'test-curriculum',
          name: 'API Test Curriculum',
          courseIds: testCourseIds,
          syncSettings: {
            syncCourses: true,
            syncStudents: true,
            syncAssignments: true,
            syncSubmissions: false,
            syncInterval: 15,
          },
        };

        const curriculumStart = Date.now();
        const curriculumResult = await gateway.getCurriculumData(curriculumConfig);
        const curriculumElapsed = Date.now() - curriculumStart;

        console.log(`✅ Curriculum sync completed in ${curriculumElapsed}ms`);
        console.log(`   Courses synced: ${curriculumResult.courses.length}`);
        console.log(`   Total students: ${curriculumResult.totalStudents}`);
        console.log(`   Estimated assignments: ${curriculumResult.totalAssignments}`);
        console.log(`   Performance status: ${curriculumResult.performance.status}`);
        console.log(`   Success rate: ${curriculumResult.performance.successRate.toFixed(1)}%`);
        console.log(`   Requests made: ${curriculumResult.performance.requestsMade}`);

        // Test 4: Individual course details
        if (testCourseIds.length > 0) {
          console.log('\n🔍 Test 4: Course Details Test...');
          const courseId = testCourseIds[0];
          
          const [studentsResult, assignmentsResult] = await Promise.all([
            gateway.getCourseStudents(courseId),
            gateway.getCourseAssignments(courseId),
          ]);

          console.log(`Course ${courseId} details:`);
          if (studentsResult.success) {
            console.log(`   ✅ Students: ${studentsResult.students.length} found`);
          } else {
            console.log(`   ❌ Students: Error - ${studentsResult.error}`);
          }

          if (assignmentsResult.success) {
            console.log(`   ✅ Assignments: ${assignmentsResult.assignments.length} found`);
          } else {
            console.log(`   ❌ Assignments: Error - ${assignmentsResult.error}`);
          }
        }
      }

      // Final API status check
      console.log('\n📊 Final API Status:');
      const finalStatus = gateway.getApiStatus();
      console.log(`   Total API calls made: ${finalStatus.schedulerMetrics.totalRequests}`);
      console.log(`   Rate limit usage: ${((finalStatus.rateLimitStatus.requestsInWindow / finalStatus.rateLimitStatus.maxRequests) * 100).toFixed(1)}%`);
      
      if (finalStatus.recommendations.length > 0) {
        console.log('   Recommendations:');
        finalStatus.recommendations.forEach(rec => {
          console.log(`     • ${rec}`);
        });
      }

    } else if (coursesResponse.errors) {
      console.log('❌ Error getting courses:');
      coursesResponse.errors.forEach(error => {
        console.log(`   ${error.error_code}: ${error.message}`);
      });
    }

  } catch (error) {
    console.error('💥 Test failed with error:', error);
  }

  console.log('\n✅ Canvas API Test Suite Complete!');
}

// Run the test
if (require.main === module) {
  testCanvasApi().catch(console.error);
}

export { testCanvasApi };