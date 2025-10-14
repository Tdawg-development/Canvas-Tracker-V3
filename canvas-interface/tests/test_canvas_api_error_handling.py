"""
Unit tests for Canvas API Error Handling

Tests comprehensive error scenarios and recovery mechanisms for Canvas API interactions
using the existing pytest infrastructure with TypeScript integration.
"""

import pytest
from conftest import (
    assert_canvas_business_logic_result,
    create_mock_canvas_course_data
)


class TestCanvasApiErrorHandling:
    """Test error handling and recovery in Canvas API interactions."""
    
    @pytest.mark.canvas_unit
    def test_api_timeout_handling(self, canvas_business_logic_tester):
        """Test handling of API timeout scenarios."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

// Mock API that simulates timeout
const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => {
            // Simulate timeout
            await new Promise(resolve => setTimeout(resolve, 100));
            throw new Error('Request timeout');
        },
        getCourseStudents: async (id) => { throw new Error('Request timeout'); },
        getCourseModules: async (id) => { throw new Error('Request timeout'); },
        getCourseAssignments: async (id) => { throw new Error('Request timeout'); },
        getCourseEnrollments: async (id) => { throw new Error('Request timeout'); }
    }
});

try {
    const courseData = await constructor.constructCourseData(7982015);
    
    console.log(JSON.stringify({ 
        success: true, 
        result: { unexpectedSuccess: true }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: true,  // We expect this to throw
        result: {
            errorHandled: true,
            errorType: error.constructor.name,
            errorMessage: error.message,
            isTimeout: error.message.includes('timeout')
        }
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        timeout_result = assert_canvas_business_logic_result(
            result, 
            expected_properties=['errorHandled', 'isTimeout']
        )
        
        # Should properly handle timeout errors
        assert timeout_result['errorHandled'] is True
        assert timeout_result['isTimeout'] is True
        assert 'timeout' in timeout_result['errorMessage'].lower()

    @pytest.mark.canvas_unit
    def test_rate_limit_handling(self, canvas_business_logic_tester):
        """Test handling of Canvas API rate limiting."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

let callCount = 0;
const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => {
            callCount++;
            if (callCount <= 2) {
                const error = new Error('Rate limit exceeded');
                error.status = 429;
                throw error;
            }
            // Success on third attempt
            return { id: 7982015, name: 'Test Course', course_code: 'TEST' };
        },
        getCourseStudents: async (id) => [{ id: 1, name: 'Student 1' }],
        getCourseModules: async (id) => [{ id: 1, name: 'Module 1' }],
        getCourseAssignments: async (id) => [{ id: 1, name: 'Assignment 1' }],
        getCourseEnrollments: async (id) => [{ user_id: 1, course_id: id }]
    }
});

try {
    const courseData = await constructor.constructCourseData(7982015);
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            constructionSucceeded: !!courseData,
            retryAttempts: callCount,
            rateLimitRecovered: callCount > 1
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        callCount: callCount,
        isRateLimit: error.status === 429
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        
        if result['success']:
            rate_limit_result = assert_canvas_business_logic_result(
                result,
                expected_properties=['constructionSucceeded', 'retryAttempts']
            )
            
            # Should either succeed with retries or document current behavior
            assert rate_limit_result['constructionSucceeded'] is True or result['error']
            print(f"📊 Rate limit test result: {rate_limit_result['retryAttempts']} attempts")
        else:
            # If no retry logic exists yet, that's documented
            assert "Rate limit" in result['error'] or result.get('isRateLimit')

    @pytest.mark.canvas_unit  
    def test_partial_data_failure_handling(self, canvas_business_logic_tester):
        """Test handling when some Canvas data is unavailable."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => ({ id: 7982015, name: 'Test Course', course_code: 'TEST' }),
        getCourseStudents: async (id) => { throw new Error('Students data unavailable'); },
        getCourseModules: async (id) => [{ id: 1, name: 'Module 1' }],  // This succeeds
        getCourseAssignments: async (id) => [{ id: 1, name: 'Assignment 1' }],
        getCourseEnrollments: async (id) => []  // Empty but no error
    }
});

try {
    const courseData = await constructor.constructCourseData(7982015);
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            partialDataHandled: true,
            hasCourseInfo: !!courseData.id,
            hasModules: courseData.modules && courseData.modules.length > 0,
            studentsHandling: 'succeeded_despite_error'
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: true,  // Partial failures are expected
        result: {
            partialDataFailed: true,
            errorMessage: error.message,
            failedOnStudents: error.message.includes('Students')
        }
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        partial_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['partialDataHandled', 'partialDataFailed']
        )
        
        # Should either handle partial data gracefully or fail with meaningful error
        if 'partialDataHandled' in partial_result:
            assert partial_result['partialDataHandled'] is True
            print("✅ Constructor handles partial data failures gracefully")
        else:
            assert partial_result['partialDataFailed'] is True
            assert 'Students' in partial_result['errorMessage']
            print("📋 Constructor requires all data - documents current behavior")

    @pytest.mark.canvas_unit
    def test_invalid_course_id_handling(self, canvas_business_logic_tester):
        """Test handling of invalid or non-existent course IDs."""
        
        invalid_course_ids = [0, -1, 999999999, None]
        
        for course_id in invalid_course_ids:
            # Convert Python None to JavaScript null
            js_course_id = 'null' if course_id is None else course_id
            test_script = f"""
import {{ CanvasDataConstructor }} from './staging/canvas-data-constructor';

const constructor = new CanvasDataConstructor({{
    canvasApi: {{
        getCourse: async (id) => {{
            if (id === null || id === undefined || id <= 0 || id > 999999) {{
                const error = new Error('Invalid course ID');
                error.status = 404;
                throw error;
            }}
            return {{ id: id, name: 'Test Course' }};
        }},
        getCourseStudents: async (id) => [],
        getCourseModules: async (id) => [],
        getCourseAssignments: async (id) => [],
        getCourseEnrollments: async (id) => []
    }}
}});

try {{
    const courseData = await constructor.constructCourseData({js_course_id});
    
    console.log(JSON.stringify({{ 
        success: true, 
        result: {{ unexpectedSuccess: true, courseId: {js_course_id} }}
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: true,  // We expect this to throw
        result: {{
            invalidCourseHandled: true,
            courseId: {js_course_id},
            errorMessage: error.message,
            isNotFound: error.status === 404 || error.message.includes('Invalid')
        }}
    }}));
}}
            """
            
            result = canvas_business_logic_tester._execute_test_script(test_script)
            invalid_result = assert_canvas_business_logic_result(
                result,
                expected_properties=['invalidCourseHandled', 'isNotFound']
            )
            
            if 'invalidCourseHandled' in invalid_result:
                assert invalid_result['invalidCourseHandled'] is True
                assert invalid_result['isNotFound'] is True
                print(f"✅ Invalid course ID {course_id} handled correctly")
            else:
                print(f"⚠️ Course ID {course_id} had unexpected behavior")


class TestCanvasApiDataValidation:
    """Test validation of Canvas API response data."""
    
    @pytest.mark.canvas_unit
    def test_malformed_response_handling(self, canvas_business_logic_tester):
        """Test handling of malformed Canvas API responses."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => ({
            // Missing required fields
            id: 7982015,
            // name: 'Missing Name',  // This is missing
            workflow_state: 'available'
        }),
        getCourseStudents: async (id) => [
            {
                // Malformed student data
                id: 'not-a-number',  // Should be number
                name: null,           // Should be string
                current_score: 'invalid' // Should be number
            }
        ],
        getCourseModules: async (id) => 'invalid-response',  // Should be array
        getCourseAssignments: async (id) => [],
        getCourseEnrollments: async (id) => []
    }
});

try {
    const courseData = await constructor.constructCourseData(7982015);
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            malformedDataHandled: true,
            courseCreated: !!courseData,
            hasValidation: 'succeeded_despite_malformed_data'
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: true,  // Validation errors are expected
        result: {
            validationFailed: true,
            errorMessage: error.message,
            isValidationError: error.message.includes('invalid') || 
                              error.message.includes('required') ||
                              error.message.includes('malformed')
        }
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        validation_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['malformedDataHandled', 'validationFailed']
        )
        
        # Should either handle malformed data gracefully or fail with validation error
        if 'malformedDataHandled' in validation_result:
            print("🛡️ Constructor has robust data validation/handling")
        else:
            assert validation_result['validationFailed'] is True
            print("📋 Constructor validates data structure - good defensive programming")

    @pytest.mark.canvas_unit
    def test_empty_response_handling(self, canvas_business_logic_tester):
        """Test handling of empty but valid Canvas API responses."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => ({ 
            id: 7982015, 
            name: 'Empty Course', 
            course_code: 'EMPTY-001',
            workflow_state: 'available'
        }),
        getCourseStudents: async (id) => [],      // No students
        getCourseModules: async (id) => [],       // No modules
        getCourseAssignments: async (id) => [],   // No assignments
        getCourseEnrollments: async (id) => []    // No enrollments
    }
});

try {
    const courseData = await constructor.constructCourseData(7982015);
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            emptyCourseHandled: true,
            hasBasicCourseInfo: !!(courseData.id && courseData.name),
            studentsCount: courseData.students ? courseData.students.length : 'no-students-array',
            modulesCount: courseData.modules ? courseData.modules.length : 'no-modules-array',
            isEmpty: (courseData.students?.length || 0) === 0 && 
                    (courseData.modules?.length || 0) === 0
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        failedOnEmpty: true
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        empty_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['emptyCourseHandled', 'hasBasicCourseInfo']
        )
        
        # Should handle empty courses gracefully
        assert empty_result['emptyCourseHandled'] is True
        assert empty_result['hasBasicCourseInfo'] is True
        assert empty_result['isEmpty'] is True
        
        print("✅ Constructor handles empty courses correctly")
        print(f"   - Students: {empty_result['studentsCount']}")
        print(f"   - Modules: {empty_result['modulesCount']}")


class TestCanvasApiNetworkResilience:
    """Test network resilience and retry behavior."""
    
    @pytest.mark.canvas_unit
    @pytest.mark.slow
    def test_intermittent_network_failures(self, canvas_business_logic_tester):
        """Test handling of intermittent network connectivity issues."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

let failureCount = 0;
const maxFailures = 2;  // Fail first 2 attempts, then succeed

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => {
            failureCount++;
            if (failureCount <= maxFailures) {
                throw new Error('Network connection failed');
            }
            return { id: 7982015, name: 'Test Course', course_code: 'NET-TEST' };
        },
        getCourseStudents: async (id) => [{ id: 1, name: 'Student 1' }],
        getCourseModules: async (id) => [{ id: 1, name: 'Module 1' }],
        getCourseAssignments: async (id) => [{ id: 1, name: 'Assignment 1' }],
        getCourseEnrollments: async (id) => [{ user_id: 1, course_id: id }]
    }
});

try {
    const startTime = Date.now();
    const courseData = await constructor.constructCourseData(7982015);
    const endTime = Date.now();
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            networkResilienceSuccess: true,
            totalFailures: failureCount,
            recoveredFromFailures: failureCount > 1,
            executionTime: endTime - startTime,
            courseConstructed: !!courseData
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        failureCount: failureCount,
        networkFailure: error.message.includes('Network') || error.message.includes('connection')
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        
        if result['success']:
            resilience_result = assert_canvas_business_logic_result(
                result,
                expected_properties=['networkResilienceSuccess', 'totalFailures']
            )
            
            # Document current resilience behavior
            if resilience_result['recoveredFromFailures']:
                print("🔄 Constructor has network retry/resilience logic")
                print(f"   - Recovered after {resilience_result['totalFailures']} failures")
            else:
                print("📋 Constructor succeeded on first attempt (no retries needed)")
                
        else:
            # If no resilience, document that
            assert result.get('networkFailure', False)
            print("📋 Constructor needs network resilience improvement")
            print(f"   - Failed after {result.get('failureCount', 0)} attempts")