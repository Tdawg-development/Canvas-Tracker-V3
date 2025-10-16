/**
 * Direct Canvas API Integration Script
 * 
 * This script makes REAL Canvas API calls using your existing infrastructure
 * and outputs structured JSON data for the Python pipeline test.
 */

import dotenv from 'dotenv';
dotenv.config();

import { CanvasCourseApiDataSet } from './canvas-interface/staging/api-call-staging';
import { CanvasDataConstructor } from './canvas-interface/staging/canvas-data-constructor';

const TEST_COURSE_ID = 7982015; // Your JDU course

async function executeRealCanvasApiCall() {
    console.log('=== REAL CANVAS API INTEGRATION TEST ===');
    console.log(`Making REAL Canvas API calls for course ${TEST_COURSE_ID}...`);
    
    // Ensure Canvas credentials are available
    if (!process.env.CANVAS_URL || !process.env.CANVAS_TOKEN) {
        throw new Error('Missing Canvas credentials. Set CANVAS_URL and CANVAS_TOKEN in .env file');
    }
    
    try {
        const startTime = Date.now();
        
        // Initialize real Canvas data constructor and staging classes
        const dataConstructor = new CanvasDataConstructor();
        const courseDataSet = new CanvasCourseApiDataSet(TEST_COURSE_ID);
        
        console.log('🏗️ Executing complete Canvas API workflow...');
        
        // Execute complete real API workflow
        await courseDataSet.rebuildCourseInfo(dataConstructor);
        await courseDataSet.rebuildEnrollments(dataConstructor);
        await courseDataSet.rebuildAssignments(dataConstructor);
        
        courseDataSet.completeConstruction();
        
        // Get all the reconstructed data
        const courseRecords = courseDataSet.reconstructCourses();
        const studentRecords = courseDataSet.reconstructStudents();
        const assignmentRecords = courseDataSet.reconstructAssignments();
        const enrollmentRecords = courseDataSet.reconstructEnrollments();
        
        const endTime = Date.now();
        const apiTime = endTime - startTime;
        
        // Create structured output for Python pipeline
        const pipelineData = {
            success: true,
            course_id: TEST_COURSE_ID,
            api_execution_time: apiTime,
            course: courseRecords.length > 0 ? {
                id: courseRecords[0].id,
                name: courseRecords[0].name,
                course_code: courseRecords[0].course_code,
                workflow_state: courseRecords[0].workflow_state || "available",
                start_at: courseRecords[0].start_at,
                end_at: courseRecords[0].end_at,
                created_at: courseRecords[0].created_at,
                updated_at: courseRecords[0].updated_at,
                enrollment_term_id: courseRecords[0].enrollment_term_id,
                default_view: courseRecords[0].default_view || "modules",
                is_public: courseRecords[0].is_public || false,
                is_public_to_auth_users: courseRecords[0].is_public_to_auth_users || false,
                public_syllabus: courseRecords[0].public_syllabus || false,
                storage_quota_mb: courseRecords[0].storage_quota_mb || 524288000,
                is_favorite: courseRecords[0].is_favorite || false,
                locale: courseRecords[0].locale || "en",
                time_zone: courseRecords[0].time_zone || "America/New_York",
                calendar: courseRecords[0].calendar || null
            } : null,
            students: studentRecords.map(student => ({
                id: student.student_id,
                user_id: student.user_id,
                name: student.name,
                email: student.email,
                enrollment_state: student.enrollment_status,
                current_score: student.current_score,
                final_score: student.final_score,
                last_activity_at: student.last_activity_at,
                course_section_id: student.course_section_id,
                user: {
                    id: student.user_id,
                    name: student.name,
                    email: student.email,
                    created_at: student.created_at || new Date().toISOString()
                },
                grades: {
                    current_score: student.current_score,
                    final_score: student.final_score,
                    current_grade: student.current_grade || "N/A",
                    final_grade: student.final_grade || "N/A"
                }
            })),
            modules: assignmentRecords.reduce((modules, assignment) => {
                let module = modules.find(m => m.id === assignment.module_id);
                if (!module) {
                    module = {
                        id: assignment.module_id,
                        name: `Module for assignments (ID: ${assignment.module_id})`,
                        position: modules.length + 1,
                        workflow_state: "active",
                        published: true,
                        items: []
                    };
                    modules.push(module);
                }
                
                module.items.push({
                    id: assignment.id,
                    title: assignment.name,
                    type: assignment.assignment_type === 'quiz' ? 'Quiz' : 'Assignment',
                    points_possible: assignment.points_possible,
                    published: assignment.published,
                    module_id: assignment.module_id
                });
                
                return modules;
            }, [])
        };
        
        console.log('📊 REAL Canvas API Results:');
        console.log(`   API execution time: ${apiTime}ms`);
        console.log(`   Course records: ${courseRecords.length}`);
        console.log(`   Student records: ${studentRecords.length}`);
        console.log(`   Assignment records: ${assignmentRecords.length}`);
        console.log(`   Enrollment records: ${enrollmentRecords.length}`);
        
        if (courseRecords.length > 0) {
            console.log(`   Course name: "${courseRecords[0].name}"`);
        }
        
        if (studentRecords.length > 0) {
            console.log(`   Sample student: "${studentRecords[0].name}" (Score: ${studentRecords[0].current_score})`);
        }
        
        if (assignmentRecords.length > 0) {
            console.log(`   Sample assignment: "${assignmentRecords[0].name}" (${assignmentRecords[0].points_possible} pts)`);
        }
        
        // Output structured JSON for Python parsing
        console.log('===CANVAS_API_RESULT_START===');
        console.log(JSON.stringify(pipelineData, null, 2));
        console.log('===CANVAS_API_RESULT_END===');
        
    } catch (error) {
        console.error('❌ REAL Canvas API call failed:', error.message);
        console.log('===CANVAS_API_RESULT_START===');
        console.log(JSON.stringify({
            success: false,
            error: {
                message: error.message,
                name: error.constructor.name,
                stack: error.stack
            }
        }, null, 2));
        console.log('===CANVAS_API_RESULT_END===');
        throw error;
    }
}

executeRealCanvasApiCall().catch(console.error);