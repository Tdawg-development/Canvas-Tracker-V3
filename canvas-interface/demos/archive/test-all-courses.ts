/**
 * Test All Active Courses Demo
 * 
 * Tests the function that gets all active courses from Canvas API
 * and builds CanvasCourseStaging objects for each one
 */

import { CanvasDataConstructor } from '../staging/canvas-data-constructor';

async function testAllActiveCourses() {
  console.log('🏫 All Active Courses Test');
  console.log('==========================\n');

  try {
    const constructor = new CanvasDataConstructor();

    console.log('📡 Calling Canvas API to get all active courses...\n');
    
    const startTime = Date.now();
    const allCourses = await constructor.getAllActiveCoursesStaging();
    const totalTime = Date.now() - startTime;
    
    console.log(`\n🎉 Successfully retrieved ${allCourses.length} active course objects!`);
    console.log(`⚡ Total processing time: ${totalTime}ms\n`);
    
    if (allCourses.length > 0) {
      console.log('📋 COMPLETE COURSE LIST:');
      console.log('========================');
      
      allCourses.forEach((course, index) => {
        console.log(`\n${index + 1}. Course ID: ${course.id}`);
        console.log(`   Name: ${course.name}`);
        console.log(`   Course Code: ${course.course_code}`);
        console.log(`   Calendar ICS: ${course.calendar.ics ? 'Available' : 'Not available'}`);
      });
      
      // Show statistics
      console.log('\n📊 COURSE STATISTICS:');
      console.log('=====================');
      console.log(`Total Active Courses: ${allCourses.length}`);
      
      // Course codes analysis
      const courseCodes = allCourses.map(course => course.course_code);
      const uniqueCodes = [...new Set(courseCodes)];
      console.log(`Unique Course Codes: ${uniqueCodes.length}`);
      console.log(`Course Codes: ${uniqueCodes.join(', ')}`);
      
      // Sample course details
      if (allCourses.length > 0) {
        const sampleCourse = allCourses[0];
        console.log('\n🔍 SAMPLE COURSE STRUCTURE:');
        console.log('============================');
        console.log(`Course ID: ${sampleCourse.id}`);
        console.log(`Name: ${sampleCourse.name}`);
        console.log(`Course Code: ${sampleCourse.course_code}`);
        console.log(`Calendar ICS: ${sampleCourse.calendar.ics}`);
        console.log(`Students Array: ${sampleCourse.students.length} (empty - not populated yet)`);
        console.log(`Modules Array: ${sampleCourse.modules.length} (empty - not populated yet)`);
      }
      
    } else {
      console.log('ℹ️ No active courses found.');
      console.log('   This could mean:');
      console.log('   - No courses are associated with this API key');
      console.log('   - All courses are in deleted/completed state');
      console.log('   - API permissions may not include course access');
    }

    // Show API performance
    const apiStatus = constructor.getApiStatus();
    console.log('\n⚡ API PERFORMANCE:');
    console.log('==================');
    console.log(`Total API Calls: ${apiStatus.schedulerMetrics.totalRequests}`);
    console.log(`Success Rate: ${((apiStatus.schedulerMetrics.successfulRequests / apiStatus.schedulerMetrics.totalRequests) * 100).toFixed(1)}%`);
    console.log(`Rate Limit Usage: ${((apiStatus.schedulerMetrics.totalRequests / 600) * 100).toFixed(1)}%`);

    console.log('\n🎯 Test Complete!');
    
  } catch (error) {
    console.error('💥 Test failed:', error);
  }
}

// Run the test
testAllActiveCourses().catch(console.error);