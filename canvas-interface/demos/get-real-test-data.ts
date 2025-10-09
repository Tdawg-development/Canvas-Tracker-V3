// Load environment variables
import dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from './src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig } from './src/infrastructure/http/canvas/CanvasTypes';

async function getRealTestData() {
  console.log('🔍 Getting real test data from Canvas course...');
  
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
    console.log(`\n📚 Getting data from course ${courseId}...`);

    // Get students
    console.log('👥 Getting students...');
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

    const students = (studentsResponse.data as any[]) || [];
    console.log(`✅ Found ${students.length} students`);

    // Get assignments
    console.log('📋 Getting assignments...');
    const assignmentsResponse = await gateway.getClient().requestWithFullResponse(
      `courses/${courseId}/assignments`,
      {
        params: {
          per_page: 100
        }
      }
    );

    const assignments = (assignmentsResponse.data as any[]) || [];
    
    // Filter active assignments (same logic as our tracker)
    const now = new Date();
    const activeAssignments = assignments.filter(assignment => {
      if (assignment.workflow_state !== 'published') return false;
      if (assignment.locked_for_user) return false;
      if (assignment.unlock_at && new Date(assignment.unlock_at) > now) return false;
      if (assignment.lock_at && new Date(assignment.lock_at) < now) return false;
      if (assignment.only_visible_to_overrides) return false;
      if (assignment.points_possible <= 0) return false;
      return true;
    });

    console.log(`✅ Found ${assignments.length} total assignments, ${activeAssignments.length} active`);

    // Output TypeScript arrays for copy-paste
    console.log('\n🎯 REAL TEST DATA FOR COPY-PASTE:');
    console.log('================================');

    console.log('\n// Real student IDs from the course:');
    const studentIds = students.slice(0, 10).map(s => s.id); // First 10 students
    console.log(`studentIds: [${studentIds.join(', ')}],`);

    console.log('\n// Real active assignment IDs from the course:');
    const assignmentIds = activeAssignments.slice(0, 15).map(a => a.id); // First 15 assignments
    console.log(`validAssignmentIds: [`);
    for (let i = 0; i < assignmentIds.length; i += 5) {
      const batch = assignmentIds.slice(i, i + 5);
      console.log(`  ${batch.join(', ')},`);
    }
    console.log(`]`);

    console.log('\n📊 Data Summary:');
    console.log(`   Course: ${courseId} (JDU 1st Section)`);
    console.log(`   Students for testing: ${studentIds.length}`);
    console.log(`   Active assignments for testing: ${assignmentIds.length}`);
    console.log(`   Expected API calls: ${assignmentIds.length} (1 per assignment)`);
    console.log(`   API efficiency: ${Math.round((1 - assignmentIds.length / (studentIds.length * assignmentIds.length)) * 100)}% reduction`);

    // Show a few names for context
    console.log('\n👥 Sample student names:');
    students.slice(0, 5).forEach((student, index) => {
      console.log(`   ${index + 1}. ${student.name} (ID: ${student.id})`);
    });

    console.log('\n📚 Sample assignment names:');
    activeAssignments.slice(0, 5).forEach((assignment, index) => {
      console.log(`   ${index + 1}. ${assignment.name} (${assignment.points_possible} pts, ID: ${assignment.id})`);
    });

  } catch (error) {
    console.error('💥 Failed to get real test data:', error);
  }
}

getRealTestData().catch(console.error);