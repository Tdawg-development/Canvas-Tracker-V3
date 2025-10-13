/**
 * Unit Test: getCurriculumData Function
 * Tests the CanvasGatewayHttp.getCurriculumData() method with 1+ course IDs
 * File: test-get-curriculum-data.ts
 */

import * as dotenv from 'dotenv';
dotenv.config();

import { CanvasGatewayHttp } from '../../src/infrastructure/http/canvas/CanvasGatewayHttp';
import { CanvasApiConfig, CurriculumConfig } from '../../src/infrastructure/http/canvas/CanvasTypes';
import * as readline from 'readline';

async function testCurriculumData() {
  console.log('🧪 Unit Test: getCurriculumData with Multiple Course IDs');
  console.log('==========================================================\n');

  // Check environment
  const canvasUrl = process.env.CANVAS_URL;
  const canvasToken = process.env.CANVAS_TOKEN;

  if (!canvasUrl || !canvasToken) {
    console.error('❌ Missing Canvas configuration');
    console.error('Please set CANVAS_URL and CANVAS_TOKEN in your .env file');
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
    rateLimitRequestsPerHour: 600,
    accountType: 'free',
  };

  const gateway = new CanvasGatewayHttp(config);

  // Interactive course ID input
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  try {
    console.log('📚 Course ID Input Options:');
    console.log('   • Single course: 7982015');
    console.log('   • Multiple courses: 7982015,8095327');
    console.log('   • Press Enter for default test (7982015,8095327)');
    console.log('');

    const input = await new Promise<string>((resolve) => {
      rl.question('Enter Canvas Course ID(s) (comma-separated): ', (answer) => {
        resolve(answer.trim());
      });
    });

    // Parse course IDs
    let courseIds: number[];
    if (input === '') {
      courseIds = [7982015, 8095327]; // Default test courses
      console.log('🎯 Using default test courses: 7982015, 8095327');
    } else {
      courseIds = input.split(',').map(id => {
        const parsed = parseInt(id.trim());
        if (isNaN(parsed)) {
          throw new Error(`Invalid course ID: ${id.trim()}`);
        }
        return parsed;
      });
      console.log(`🎯 Testing with courses: ${courseIds.join(', ')}`);
    }

    console.log('');

    // Create curriculum config
    const curriculumConfig: CurriculumConfig = {
      id: `test-curriculum-${Date.now()}`,
      name: `Test Curriculum (${courseIds.length} courses)`,
      courseIds: courseIds,
      syncSettings: {
        syncCourses: true,
        syncStudents: true,
        syncAssignments: true,
        syncSubmissions: false,
        syncInterval: 15,
      },
    };

    console.log('⚙️ Curriculum Configuration:');
    console.log(`   ID: ${curriculumConfig.id}`);
    console.log(`   Name: ${curriculumConfig.name}`);
    console.log(`   Course Count: ${curriculumConfig.courseIds.length}`);
    console.log(`   Course IDs: [${curriculumConfig.courseIds.join(', ')}]`);
    console.log('   Sync Settings:', JSON.stringify(curriculumConfig.syncSettings, null, 4));
    console.log('');

    // Execute the test
    console.log('🚀 Executing getCurriculumData()...');
    console.log('=====================================');
    const startTime = Date.now();
    
    const result = await gateway.getCurriculumData(curriculumConfig);
    
    const executionTime = Date.now() - startTime;
    console.log(`✅ Completed in ${executionTime}ms\n`);

    // Display detailed results
    console.log('📊 DETAILED RESULTS:');
    console.log('====================');
    
    console.log('\n🎓 COURSES RETRIEVED:');
    console.log(`   Total courses: ${result.courses.length}`);
    result.courses.forEach((course, index) => {
      console.log(`   ${index + 1}. ${course.name} (ID: ${course.id})`);
      console.log(`      Code: ${course.course_code}`);
      console.log(`      State: ${course.workflow_state}`);
      console.log(`      Students: ${course.total_students || 'Unknown'}`);
      console.log(`      Start: ${course.start_at || 'Not set'}`);
      console.log(`      End: ${course.end_at || 'Not set'}`);
      console.log('');
    });

    console.log('📈 AGGREGATED TOTALS:');
    console.log(`   Total Students: ${result.totalStudents}`);
    console.log(`   Estimated Assignments: ${result.totalAssignments}`);
    console.log('');

    console.log('⚡ PERFORMANCE METRICS:');
    console.log(`   Sync Time: ${result.performance.syncTimeSeconds.toFixed(2)} seconds`);
    console.log(`   Requests Made: ${result.performance.requestsMade}`);
    console.log(`   Success Rate: ${result.performance.successRate.toFixed(1)}%`);
    console.log(`   Can Handle 8 Courses: ${result.performance.canHandle8Courses ? 'Yes' : 'No'}`);
    console.log(`   Status: ${result.performance.status.toUpperCase()}`);
    console.log('');

    console.log('🔍 SYNC STATUS:');
    console.log(`   Curriculum ID: ${result.syncStatus.curriculumId}`);
    console.log(`   Last Sync: ${result.syncStatus.lastSyncAt}`);
    console.log(`   Successful: ${result.syncStatus.lastSuccessfulSyncAt ? 'Yes' : 'No'}`);
    console.log(`   In Progress: ${result.syncStatus.syncInProgress}`);
    console.log(`   Errors: ${result.syncStatus.errors.length > 0 ? result.syncStatus.errors.join(', ') : 'None'}`);
    console.log(`   Courses Count: ${result.syncStatus.coursesCount}`);
    console.log(`   Students Count: ${result.syncStatus.studentsCount}`);
    console.log(`   Assignments Count: ${result.syncStatus.assignmentsCount}`);
    console.log('');

    // Performance analysis
    console.log('🎯 PERFORMANCE ANALYSIS:');
    console.log('==========================');
    const avgTimePerCourse = result.performance.syncTimeSeconds / courseIds.length;
    console.log(`   Average time per course: ${avgTimePerCourse.toFixed(2)}s`);
    console.log(`   Requests per course: ${(result.performance.requestsMade / courseIds.length).toFixed(1)}`);
    
    // Rate limit analysis
    const rateLimitUsage = (result.performance.requestsMade / 600) * 100; // Assuming 600 req/hour
    console.log(`   Rate limit usage: ${rateLimitUsage.toFixed(2)}%`);
    
    // Scale projection
    const projectedTimeFor8Courses = avgTimePerCourse * 8;
    console.log(`   Projected time for 8 courses: ${projectedTimeFor8Courses.toFixed(1)}s`);
    
    console.log('');

    // Raw data output (JSON)
    console.log('📋 RAW DATA OUTPUT (JSON):');
    console.log('===========================');
    console.log(JSON.stringify(result, null, 2));
    console.log('');

    // Test validation
    console.log('✅ TEST VALIDATION:');
    console.log('==================');
    
    const validations = [
      { check: result.courses.length === courseIds.length, desc: `Retrieved all ${courseIds.length} requested courses` },
      { check: result.courses.every(c => courseIds.includes(c.id)), desc: 'All course IDs match requested IDs' },
      { check: result.totalStudents >= 0, desc: 'Total students is non-negative' },
      { check: result.totalAssignments >= 0, desc: 'Total assignments is non-negative' },
      { check: result.performance.successRate >= 0, desc: 'Success rate is valid' },
      { check: result.syncStatus.coursesCount === result.courses.length, desc: 'Sync status matches actual course count' },
      { check: result.syncStatus.studentsCount === result.totalStudents, desc: 'Sync status matches actual student count' },
      { check: result.syncStatus.assignmentsCount === result.totalAssignments, desc: 'Sync status matches actual assignment count' },
    ];

    let allValid = true;
    validations.forEach(validation => {
      const status = validation.check ? '✅' : '❌';
      console.log(`   ${status} ${validation.desc}`);
      if (!validation.check) allValid = false;
    });

    console.log('');
    console.log(`🎯 OVERALL TEST RESULT: ${allValid ? '✅ PASSED' : '❌ FAILED'}`);
    
    if (allValid) {
      console.log('🚀 getCurriculumData() is working correctly with multiple course IDs!');
    } else {
      console.log('⚠️  Some validations failed - check the implementation');
    }

  } catch (error) {
    console.error('💥 Test failed:', error);
  } finally {
    rl.close();
  }
}

// Run the test
if (require.main === module) {
  testCurriculumData().catch(console.error);
}

export { testCurriculumData };