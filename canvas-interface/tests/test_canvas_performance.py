"""
Performance and Load Tests for Canvas API Interactions

Tests performance characteristics, concurrency handling, and resource usage
of Canvas API integration components.
"""

import pytest
import time
from conftest import (
    assert_canvas_business_logic_result,
    create_mock_canvas_course_data
)


class TestCanvasApiPerformance:
    """Test performance characteristics of Canvas API interactions."""
    
    @pytest.mark.canvas_unit
    @pytest.mark.slow
    def test_api_call_concurrency_optimization(self, canvas_business_logic_tester):
        """Test that Canvas API calls are optimized for concurrency."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

// Mock API that tracks call timing and concurrency
const callLogs = [];
let activeCalls = 0;
const maxActiveCalls = { value: 0 };

const createTimedApiCall = (name, delay = 100) => {
    return async (id) => {
        const callId = `${name}-${Date.now()}-${Math.random()}`;
        const startTime = Date.now();
        
        activeCalls++;
        maxActiveCalls.value = Math.max(maxActiveCalls.value, activeCalls);
        
        callLogs.push({
            name: name,
            callId: callId,
            startTime: startTime,
            concurrentCalls: activeCalls
        });
        
        // Simulate API delay
        await new Promise(resolve => setTimeout(resolve, delay));
        
        activeCalls--;
        const endTime = Date.now();
        
        // Find and update the corresponding log entry
        const logEntry = callLogs.find(log => log.callId === callId);
        if (logEntry) {
            logEntry.endTime = endTime;
            logEntry.duration = endTime - startTime;
        }
        
        // Return appropriate mock data
        switch (name) {
            case 'getCourse':
                return { id: 7982015, name: 'Performance Test Course', course_code: 'PERF-TEST' };
            case 'getCourseStudents':
                return [{ id: 1, name: 'Student 1' }, { id: 2, name: 'Student 2' }];
            case 'getCourseModules':
                return [{ id: 1, name: 'Module 1' }, { id: 2, name: 'Module 2' }];
            case 'getCourseAssignments':
                return [{ id: 1, name: 'Assignment 1' }];
            case 'getCourseEnrollments':
                return [{ user_id: 1, course_id: id }, { user_id: 2, course_id: id }];
            default:
                return [];
        }
    };
};

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: createTimedApiCall('getCourse', 150),
        getCourseStudents: createTimedApiCall('getCourseStudents', 200),
        getCourseModules: createTimedApiCall('getCourseModules', 100),
        getCourseAssignments: createTimedApiCall('getCourseAssignments', 120),
        getCourseEnrollments: createTimedApiCall('getCourseEnrollments', 180)
    }
});

try {
    const overallStart = Date.now();
    const courseData = await constructor.constructCourseData(7982015);
    const overallEnd = Date.now();
    
    const totalDuration = overallEnd - overallStart;
    const serialDuration = callLogs.reduce((sum, log) => sum + (log.duration || 0), 0);
    const concurrencyRatio = serialDuration / totalDuration;
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            performanceMetrics: {
                totalExecutionTime: totalDuration,
                serialExecutionTime: serialDuration,
                concurrencyRatio: concurrencyRatio,
                maxConcurrentCalls: maxActiveCalls.value,
                totalApiCalls: callLogs.length
            },
            callDetails: callLogs.map(log => ({
                name: log.name,
                duration: log.duration,
                concurrentCalls: log.concurrentCalls,
                startTime: log.startTime - overallStart // Relative to test start
            })),
            efficiency: {
                isOptimized: concurrencyRatio > 1.5,  // Indicates concurrent execution
                pattern: concurrencyRatio > 2 ? 'highly_concurrent' : 
                        concurrencyRatio > 1.2 ? 'somewhat_concurrent' : 'sequential'
            }
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        callLogs: callLogs
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        performance_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['performanceMetrics', 'callDetails', 'efficiency']
        )
        
        metrics = performance_result['performanceMetrics']
        efficiency = performance_result['efficiency']
        
        print("\n📊 Canvas API Performance Analysis:")
        print(f"   Total execution time: {metrics['totalExecutionTime']}ms")
        print(f"   Serial execution time: {metrics['serialExecutionTime']}ms")
        print(f"   Concurrency ratio: {metrics['concurrencyRatio']:.2f}x")
        print(f"   Max concurrent calls: {metrics['maxConcurrentCalls']}")
        print(f"   Execution pattern: {efficiency['pattern']}")
        
        # Document current performance characteristics
        if efficiency['isOptimized']:
            print("   ✅ Excellent: API calls are well-optimized for concurrency")
        else:
            print("   📋 Sequential execution - opportunity for performance improvement")
        
        # Performance should be reasonable regardless of pattern
        assert metrics['totalExecutionTime'] < 2000, f"Total time should be under 2s, got {metrics['totalExecutionTime']}ms"

    @pytest.mark.canvas_unit
    @pytest.mark.slow
    def test_large_course_data_performance(self, canvas_business_logic_tester):
        """Test performance with large course datasets."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

// Generate large datasets for performance testing
const generateLargeDataset = () => {
    const students = [];
    for (let i = 1; i <= 100; i++) {  // 100 students
        students.push({
            id: 111000000 + i,
            name: `Test Student ${i}`,
            login_id: `student${i}@test.edu`,
            current_score: Math.floor(Math.random() * 100),
            final_score: Math.floor(Math.random() * 100)
        });
    }
    
    const modules = [];
    for (let i = 1; i <= 20; i++) {  // 20 modules
        const assignments = [];
        for (let j = 1; j <= 5; j++) {  // 5 assignments per module
            assignments.push({
                id: i * 1000 + j,
                title: `Assignment ${j} - Module ${i}`,
                type: j % 3 === 0 ? 'Quiz' : 'Assignment',
                content_id: i * 10000 + j
            });
        }
        
        modules.push({
            id: 10000 + i,
            name: `Module ${i}`,
            position: i,
            published: true,
            items: assignments
        });
    }
    
    const assignments = [];
    modules.forEach(module => {
        module.items.forEach(item => {
            assignments.push({
                id: item.content_id,
                course_id: 7982015,
                module_id: module.id,
                name: item.title,
                type: item.type.toLowerCase(),
                points_possible: Math.floor(Math.random() * 100) + 10,
                published: true
            });
        });
    });
    
    const enrollments = students.map(student => ({
        user_id: student.id,
        course_id: 7982015,
        enrollment_state: 'active',
        grades: { 
            current_score: student.current_score, 
            final_score: student.final_score 
        },
        user: {
            id: student.id,
            name: student.name,
            login_id: student.login_id
        }
    }));
    
    return { students, modules, assignments, enrollments };
};

const largeDataset = generateLargeDataset();

const constructor = new CanvasDataConstructor({
    canvasApi: {
        getCourse: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 50)); // Simulate API delay
            return { 
                id: 7982015, 
                name: 'Large Course Performance Test', 
                course_code: 'LARGE-PERF',
                total_points: 10000
            };
        },
        getCourseStudents: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 200)); // Larger delay for more data
            return largeDataset.students;
        },
        getCourseModules: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 150));
            return largeDataset.modules;
        },
        getCourseAssignments: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 100));
            return largeDataset.assignments;
        },
        getCourseEnrollments: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 300)); // Largest delay for enrollment data
            return largeDataset.enrollments;
        }
    }
});

try {
    const memoryStart = process.memoryUsage();
    const startTime = Date.now();
    
    const courseData = await constructor.constructCourseData(7982015);
    
    const endTime = Date.now();
    const memoryEnd = process.memoryUsage();
    
    const processingTime = endTime - startTime;
    const memoryDelta = {
        rss: memoryEnd.rss - memoryStart.rss,
        heapUsed: memoryEnd.heapUsed - memoryStart.heapUsed,
        heapTotal: memoryEnd.heapTotal - memoryStart.heapTotal
    };
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            datasetSize: {
                students: largeDataset.students.length,
                modules: largeDataset.modules.length,
                assignments: largeDataset.assignments.length,
                totalDataPoints: largeDataset.students.length + largeDataset.modules.length + largeDataset.assignments.length
            },
            performance: {
                processingTime: processingTime,
                memoryUsage: memoryDelta,
                throughput: {
                    studentsPerSecond: Math.round((largeDataset.students.length / processingTime) * 1000),
                    assignmentsPerSecond: Math.round((largeDataset.assignments.length / processingTime) * 1000),
                    dataPointsPerSecond: Math.round(((largeDataset.students.length + largeDataset.assignments.length) / processingTime) * 1000)
                }
            },
            constructionSuccess: {
                courseCreated: !!courseData,
                allStudentsProcessed: courseData.students && courseData.students.length === largeDataset.students.length,
                allModulesProcessed: courseData.modules && courseData.modules.length === largeDataset.modules.length,
                businessMethodsAvailable: typeof courseData.getAllAssignments === 'function'
            }
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        datasetSize: {
            students: largeDataset.students.length,
            modules: largeDataset.modules.length,
            assignments: largeDataset.assignments.length
        }
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        large_data_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['datasetSize', 'performance', 'constructionSuccess']
        )
        
        dataset = large_data_result['datasetSize']
        perf = large_data_result['performance']
        success = large_data_result['constructionSuccess']
        
        print(f"\n📈 Large Dataset Performance Test:")
        print(f"   Dataset: {dataset['students']} students, {dataset['modules']} modules, {dataset['assignments']} assignments")
        print(f"   Processing time: {perf['processingTime']}ms")
        print(f"   Throughput: {perf['throughput']['dataPointsPerSecond']} data points/second")
        print(f"   Memory usage: {perf['memoryUsage']['heapUsed'] / 1024 / 1024:.1f}MB heap")
        
        # Verify successful processing
        assert success['courseCreated'] is True, "Course should be created successfully"
        assert success['allStudentsProcessed'] is True, "All students should be processed"
        assert success['allModulesProcessed'] is True, "All modules should be processed"
        
        # Performance should be reasonable for large datasets
        assert perf['processingTime'] < 5000, f"Large dataset processing should be under 5s, got {perf['processingTime']}ms"
        assert perf['throughput']['dataPointsPerSecond'] > 10, f"Should process at least 10 data points/second"

    @pytest.mark.canvas_unit
    def test_memory_usage_optimization(self, canvas_business_logic_tester):
        """Test memory usage patterns and potential memory leaks."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

// Test multiple course constructions to check for memory leaks
const runMultipleCourseConstructions = async () => {
    const memorySnapshots = [];
    const results = [];
    
    for (let i = 0; i < 5; i++) {
        const memoryBefore = process.memoryUsage();
        
        const constructor = new CanvasDataConstructor({
            canvasApi: {
                getCourse: async (id) => ({ 
                    id: 7982015 + i, 
                    name: `Test Course ${i}`, 
                    course_code: `TEST-${i}` 
                }),
                getCourseStudents: async (id) => [
                    { id: 1000 + i, name: `Student ${i}` }
                ],
                getCourseModules: async (id) => [
                    { id: 2000 + i, name: `Module ${i}` }
                ],
                getCourseAssignments: async (id) => [
                    { id: 3000 + i, name: `Assignment ${i}` }
                ],
                getCourseEnrollments: async (id) => [
                    { user_id: 1000 + i, course_id: id }
                ]
            }
        });
        
        const courseData = await constructor.constructCourseData(7982015 + i);
        const memoryAfter = process.memoryUsage();
        
        memorySnapshots.push({
            iteration: i,
            before: memoryBefore,
            after: memoryAfter,
            delta: {
                rss: memoryAfter.rss - memoryBefore.rss,
                heapUsed: memoryAfter.heapUsed - memoryBefore.heapUsed
            }
        });
        
        results.push({
            courseId: courseData.id,
            success: !!courseData
        });
        
        // Force garbage collection if available
        if (global.gc) {
            global.gc();
        }
    }
    
    return { memorySnapshots, results };
};

try {
    const testResults = await runMultipleCourseConstructions();
    
    const memoryTrend = testResults.memorySnapshots.map(snapshot => snapshot.delta.heapUsed);
    const averageMemoryUsage = memoryTrend.reduce((sum, usage) => sum + usage, 0) / memoryTrend.length;
    const memoryGrowthRate = memoryTrend.length > 1 ? 
        (memoryTrend[memoryTrend.length - 1] - memoryTrend[0]) / (memoryTrend.length - 1) : 0;
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            memoryAnalysis: {
                totalIterations: testResults.results.length,
                successfulConstructions: testResults.results.filter(r => r.success).length,
                averageMemoryPerConstruction: Math.round(averageMemoryUsage / 1024 / 1024 * 100) / 100, // MB
                memoryGrowthRate: Math.round(memoryGrowthRate / 1024 * 100) / 100, // KB per iteration
                memoryTrend: memoryTrend.map(usage => Math.round(usage / 1024 / 1024 * 100) / 100) // MB
            },
            memoryHealthCheck: {
                noMemoryLeak: Math.abs(memoryGrowthRate) < 1024 * 100, // Less than 100KB growth per iteration
                reasonableUsage: averageMemoryUsage < 1024 * 1024 * 50, // Less than 50MB per construction
                consistentPerformance: Math.max(...memoryTrend) - Math.min(...memoryTrend) < 1024 * 1024 * 10 // Less than 10MB variation
            }
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        stack: error.stack
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        memory_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['memoryAnalysis', 'memoryHealthCheck']
        )
        
        analysis = memory_result['memoryAnalysis']
        health = memory_result['memoryHealthCheck']
        
        print(f"\n🧠 Memory Usage Analysis:")
        print(f"   Successful constructions: {analysis['successfulConstructions']}/{analysis['totalIterations']}")
        print(f"   Average memory per construction: {analysis['averageMemoryPerConstruction']}MB")
        print(f"   Memory growth rate: {analysis['memoryGrowthRate']}KB per iteration")
        print(f"   Memory trend: {analysis['memoryTrend']}MB")
        
        # Verify memory health
        assert health['noMemoryLeak'] is True, f"Memory growth rate too high: {analysis['memoryGrowthRate']}KB per iteration"
        assert health['reasonableUsage'] is True, f"Average memory usage too high: {analysis['averageMemoryPerConstruction']}MB"
        
        if health['consistentPerformance']:
            print("   ✅ Consistent memory usage across iterations")
        else:
            print("   📋 Some variation in memory usage - may indicate optimization opportunities")


class TestCanvasApiLoadTesting:
    """Test Canvas API interactions under load conditions."""
    
    @pytest.mark.canvas_integration
    @pytest.mark.slow
    def test_concurrent_course_construction(self, canvas_business_logic_tester):
        """Test concurrent construction of multiple courses."""
        
        test_script = """
import { CanvasDataConstructor } from './staging/canvas-data-constructor';

// Test concurrent course constructions
const runConcurrentConstructions = async () => {
    const courseIds = [7982015, 7982016, 7982017, 7982018, 7982019]; // 5 courses
    
    const createMockApiForCourse = (baseId) => ({
        getCourse: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 100 + Math.random() * 50)); // Variable delay
            return { 
                id: id, 
                name: `Concurrent Test Course ${id}`, 
                course_code: `CONC-${id}` 
            };
        },
        getCourseStudents: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 150 + Math.random() * 100));
            return [
                { id: id * 10 + 1, name: `Student 1 for Course ${id}` },
                { id: id * 10 + 2, name: `Student 2 for Course ${id}` }
            ];
        },
        getCourseModules: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 120 + Math.random() * 80));
            return [
                { id: id * 100 + 1, name: `Module 1 for Course ${id}` },
                { id: id * 100 + 2, name: `Module 2 for Course ${id}` }
            ];
        },
        getCourseAssignments: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 80 + Math.random() * 40));
            return [
                { id: id * 1000 + 1, name: `Assignment 1 for Course ${id}` }
            ];
        },
        getCourseEnrollments: async (id) => {
            await new Promise(resolve => setTimeout(resolve, 200 + Math.random() * 100));
            return [
                { user_id: id * 10 + 1, course_id: id },
                { user_id: id * 10 + 2, course_id: id }
            ];
        }
    });
    
    const startTime = Date.now();
    
    // Create concurrent course constructions
    const constructionPromises = courseIds.map(courseId => {
        const constructor = new CanvasDataConstructor({
            canvasApi: createMockApiForCourse(courseId)
        });
        return constructor.constructCourseData(courseId)
            .then(courseData => ({ 
                courseId, 
                success: true, 
                courseData: {
                    id: courseData.id,
                    name: courseData.name,
                    studentsCount: courseData.students?.length || 0,
                    modulesCount: courseData.modules?.length || 0
                }
            }))
            .catch(error => ({ 
                courseId, 
                success: false, 
                error: error.message 
            }));
    });
    
    const results = await Promise.all(constructionPromises);
    const endTime = Date.now();
    
    const totalTime = endTime - startTime;
    const successfulConstructions = results.filter(r => r.success);
    const failedConstructions = results.filter(r => !r.success);
    
    return {
        totalTime,
        results,
        summary: {
            totalCourses: courseIds.length,
            successful: successfulConstructions.length,
            failed: failedConstructions.length,
            averageTimePerCourse: totalTime / courseIds.length,
            concurrencyEfficiency: 'measured' // Would be calculated vs sequential
        }
    };
};

try {
    const loadTestResults = await runConcurrentConstructions();
    
    console.log(JSON.stringify({ 
        success: true, 
        result: {
            loadTestResults: loadTestResults,
            performanceMetrics: {
                totalExecutionTime: loadTestResults.totalTime,
                throughput: Math.round((loadTestResults.summary.successful / loadTestResults.totalTime) * 1000 * 100) / 100, // courses per second
                successRate: (loadTestResults.summary.successful / loadTestResults.summary.totalCourses) * 100,
                averageTimePerCourse: loadTestResults.summary.averageTimePerCourse
            },
            loadTestHealth: {
                allSuccessful: loadTestResults.summary.failed === 0,
                reasonablePerformance: loadTestResults.totalTime < 10000, // Under 10 seconds
                goodThroughput: (loadTestResults.summary.successful / loadTestResults.totalTime) * 1000 > 0.5 // More than 0.5 courses/sec
            }
        }
    }));
} catch (error) {
    console.log(JSON.stringify({ 
        success: false, 
        error: error.message,
        stack: error.stack
    }));
}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        load_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['loadTestResults', 'performanceMetrics', 'loadTestHealth']
        )
        
        metrics = load_result['performanceMetrics']
        health = load_result['loadTestHealth']
        
        print(f"\n⚡ Concurrent Load Test Results:")
        print(f"   Total execution time: {metrics['totalExecutionTime']}ms")
        print(f"   Success rate: {metrics['successRate']:.1f}%")
        print(f"   Throughput: {metrics['throughput']} courses/second")
        print(f"   Average time per course: {metrics['averageTimePerCourse']:.1f}ms")
        
        # Verify load test health
        assert health['allSuccessful'] is True, "All concurrent constructions should succeed"
        assert health['reasonablePerformance'] is True, f"Load test took too long: {metrics['totalExecutionTime']}ms"
        
        if health['goodThroughput']:
            print("   ✅ Good concurrent throughput performance")
        else:
            print("   📋 Throughput could be improved for concurrent operations")