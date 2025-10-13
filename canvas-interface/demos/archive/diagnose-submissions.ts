// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

async function diagnoseSubmissions() {
  console.log('🔍 DIAGNOSING Canvas Submissions API');
  console.log('====================================\n');

  // Get environment variables
  const canvasUrl = process.env.CANVAS_URL;
  const canvasToken = process.env.CANVAS_TOKEN;

  if (!canvasUrl || !canvasToken) {
    console.error('❌ Error: Missing Canvas configuration');
    return;
  }

  // Initialize Canvas Gateway
  const config: CanvasApiConfig = {
    baseUrl: canvasUrl,
    token: canvasToken,
    rateLimitRequestsPerHour: 600,
    accountType: 'free',
  };

  const gateway = new CanvasGatewayHttp(config);
  const courseId = 7982015;

  try {
    // Step 1: Get basic course info
    console.log('📋 Getting course info...');
    const courseResponse = await gateway.getClient().requestWithFullResponse(`courses/${courseId}`, {});
    const course = courseResponse.data as any;
    console.log(`✅ Course: ${course.name}`);

    // Step 2: Get assignments count
    console.log('\n📚 Getting assignments...');
    const assignmentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${courseId}/assignments`,
      { params: { per_page: 100 } }
    );
    const assignments = assignmentsResponse.data as any[];
    console.log(`✅ Found ${assignments.length} assignments`);

    // Step 3: Get students count
    console.log('\n👥 Getting students...');
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
    const students = studentsResponse.data as any[];
    console.log(`✅ Found ${students.length} students`);

    console.log(`\n🧮 Expected submissions: ${students.length} students × ${assignments.length} assignments = ${students.length * assignments.length} max submissions`);

    // Step 4: Diagnose submissions API - get just first page
    console.log('\n📊 Testing submissions API (first page only)...');
    const submissionsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${courseId}/students/submissions`,
      {
        params: {
          per_page: 10, // Just 10 to analyze
          include: ['assignment', 'grade', 'score']
        }
      }
    );

    if (submissionsResponse.data && Array.isArray(submissionsResponse.data)) {
      const submissions = submissionsResponse.data as any[];
      console.log(`✅ Retrieved ${submissions.length} submissions on first page`);

      // Analyze what we got
      console.log('\n🔍 SUBMISSION ANALYSIS:');
      console.log('=======================');

      // Check unique courses
      const uniqueCourseIds = new Set(submissions.map(s => s.course_id));
      console.log(`📋 Unique course IDs found: ${Array.from(uniqueCourseIds).join(', ')}`);
      if (uniqueCourseIds.size > 1) {
        console.log('⚠️  WARNING: Submissions from multiple courses detected!');
      }

      // Check unique students
      const uniqueStudentIds = new Set(submissions.map(s => s.user_id));
      console.log(`👥 Unique student IDs found: ${uniqueStudentIds.size} students`);
      
      // Check unique assignments
      const uniqueAssignmentIds = new Set(submissions.map(s => s.assignment_id));
      console.log(`📚 Unique assignment IDs found: ${uniqueAssignmentIds.size} assignments`);

      // Show some sample data
      console.log('\n📝 Sample submissions:');
      submissions.slice(0, 5).forEach((submission, index) => {
        console.log(`   ${index + 1}. Course: ${submission.course_id}, Student: ${submission.user_id}, Assignment: ${submission.assignment_id}, State: ${submission.workflow_state}`);
      });

      // Check Link header for total pages
      console.log('\n📄 Pagination info:');
      const linkHeader = submissionsResponse.headers.link;
      console.log(`   Link header: ${linkHeader || 'None'}`);
      
      if (linkHeader) {
        // Try to extract last page number
        const lastMatch = linkHeader.match(/page=(\d+)[^>]*>;\s*rel="last"/);
        if (lastMatch) {
          const lastPage = parseInt(lastMatch[1]);
          const estimatedTotal = lastPage * 10; // 10 per page in our test
          console.log(`   📊 Estimated total submissions: ~${estimatedTotal} (${lastPage} pages × 10 per page)`);
          console.log(`   🤔 This seems ${estimatedTotal > (students.length * assignments.length) ? 'HIGH' : 'reasonable'} for ${students.length * assignments.length} expected submissions`);
        }
      }

    } else {
      console.log('❌ No submissions data received');
      console.log('Response:', submissionsResponse);
    }

    // Step 5: Try alternative API endpoint
    console.log('\n🔄 Testing alternative API endpoint...');
    try {
      const altResponse = await gateway.getClient().requestWithFullResponse(
        `courses/${courseId}/assignments/${assignments[0].id}/submissions`,
        {
          params: {
            per_page: 10,
            include: ['grade', 'score']
          }
        }
      );

      if (altResponse.data && Array.isArray(altResponse.data)) {
        console.log(`✅ Alternative endpoint returned ${(altResponse.data as any[]).length} submissions for assignment ${assignments[0].id}`);
        console.log(`   Expected: ${students.length} submissions (one per student)`);
        
        if ((altResponse.data as any[]).length === students.length) {
          console.log('✅ This matches expected count perfectly!');
        } else {
          console.log('⚠️  Count mismatch detected');
        }
      }
    } catch (error) {
      console.log('❌ Alternative endpoint failed:', error);
    }

  } catch (error) {
    console.error('💥 Diagnosis failed:', error);
  }
}

// Run the diagnosis
diagnoseSubmissions().catch(console.error);