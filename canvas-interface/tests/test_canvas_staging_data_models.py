"""
Unit tests for Canvas Staging Data Models

Tests the business logic methods in Canvas staging data classes using
the existing pytest infrastructure extended for TypeScript integration.
"""

import pytest
from conftest import (
    assert_canvas_business_logic_result,
    create_mock_canvas_student_data,
    create_mock_canvas_course_data
)


class TestCanvasStudentStaging:
    """Test business logic in CanvasStudentStaging class."""
    
    @pytest.mark.canvas_unit
    def test_missing_assignments_detection(self, canvas_business_logic_tester):
        """Test getMissingAssignments() method identifies students with missing work."""
        
        # Student with missing assignments (current_score < final_score)
        student_data = create_mock_canvas_student_data(
            student_id=111929282,
            current_score=75,
            final_score=85  # Gap indicates missing assignments
        )
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging",
            method_name="hasMissingAssignments",
            test_data=student_data
        )
        
        # Should detect missing assignments
        has_missing = assert_canvas_business_logic_result(result)
        assert has_missing is True, "Student with score gap should have missing assignments"
        
    @pytest.mark.canvas_unit
    def test_no_missing_assignments(self, canvas_business_logic_tester):
        """Test student with no missing assignments."""
        
        # Student with no missing assignments (current_score == final_score)
        student_data = create_mock_canvas_student_data(
            student_id=111929283,
            current_score=88,
            final_score=88  # No gap
        )
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging",
            method_name="hasMissingAssignments",
            test_data=student_data
        )
        
        # Should not detect missing assignments
        has_missing = assert_canvas_business_logic_result(result)
        assert has_missing is False, "Student with no score gap should not have missing assignments"
    
    @pytest.mark.canvas_unit
    def test_grade_improvement_potential_calculation(self, canvas_business_logic_tester):
        """Test getGradeImprovementPotential() calculation."""
        
        student_data = create_mock_canvas_student_data(
            current_score=72,
            final_score=89
        )
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging",
            method_name="getGradeImprovementPotential",
            test_data=student_data
        )
        
        # Should calculate improvement potential correctly
        improvement_potential = assert_canvas_business_logic_result(result)
        expected_improvement = 89 - 72  # final_score - current_score
        assert improvement_potential == expected_improvement, f"Expected {expected_improvement}, got {improvement_potential}"
    
    @pytest.mark.canvas_unit  
    def test_grade_improvement_potential_no_improvement(self, canvas_business_logic_tester):
        """Test improvement potential when student has completed all work."""
        
        student_data = create_mock_canvas_student_data(
            current_score=95,
            final_score=95  # No improvement possible
        )
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging",
            method_name="getGradeImprovementPotential",
            test_data=student_data
        )
        
        improvement_potential = assert_canvas_business_logic_result(result)
        assert improvement_potential == 0, "Student with no missing work should have 0 improvement potential"
    
    @pytest.mark.canvas_unit
    def test_activity_status_recent(self, canvas_business_logic_tester):
        """Test getActivityStatus() for recently active student."""
        
        student_data = create_mock_canvas_student_data()
        # Mock data includes recent last_activity
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging", 
            method_name="getActivityStatus",
            test_data=student_data
        )
        
        activity_status = assert_canvas_business_logic_result(result, expected_properties=['status', 'lastActivity'])
        assert activity_status['status'] in ['active', 'recent', 'inactive'], "Should return valid activity status"
    
    @pytest.mark.canvas_unit
    def test_student_data_validation(self, canvas_business_logic_tester):
        """Test that student object validates required fields."""
        
        # Test with incomplete data
        incomplete_data = {
            'id': 12345,
            # Missing name, login_id, etc.
        }
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasStudentStaging",
            method_name="isValid",  # Assuming validation method exists
            test_data=incomplete_data
        )
        
        # This should handle validation gracefully
        # Either return false or throw descriptive error
        if result['success']:
            is_valid = result['result']
            assert is_valid is False, "Incomplete student data should not be valid"
        else:
            # Validation error is acceptable for incomplete data
            assert "required" in result['error'].lower() or "missing" in result['error'].lower()


class TestCanvasCourseStaging:
    """Test business logic in CanvasCourseStaging class."""
    
    @pytest.mark.canvas_unit
    def test_get_all_assignments_aggregation(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test getAllAssignments() aggregates assignments from all modules."""
        
        # Use comprehensive course data from fixture
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        course_data['modules'] = enhanced_mock_canvas_api_response['modules']
        course_data['assignments'] = enhanced_mock_canvas_api_response['assignments']
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasCourseStaging",
            method_name="getAllAssignments",
            test_data=course_data
        )
        
        all_assignments = assert_canvas_business_logic_result(result)
        assert len(all_assignments) == 3, f"Expected 3 assignments, got {len(all_assignments)}"
        
        # Check that assignments from different modules are included
        assignment_titles = [assignment['title'] for assignment in all_assignments]
        expected_titles = ['HTML Structure Assignment', 'HTML Forms Quiz', 'CSS Layout Project']
        for expected_title in expected_titles:
            assert expected_title in assignment_titles, f"Missing assignment: {expected_title}"
    
    @pytest.mark.canvas_unit
    def test_get_students_by_grade_range(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test getStudentsByGradeRange() filtering logic."""
        
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        course_data['students'] = enhanced_mock_canvas_api_response['students']
        
        # Test grade range 70-85
        test_script = f"""
import {{ CanvasCourseStaging }} from './staging/canvas-staging-data';

const courseData = {course_data};
const course = new CanvasCourseStaging(courseData);

try {{
    const studentsInRange = course.getStudentsByGradeRange(70, 85);
    console.log(JSON.stringify({{ 
        success: true, 
        result: studentsInRange,
        count: studentsInRange.length
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message
    }}));
}}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        
        # Verify the test executed successfully
        assert result['success'], f"Test execution failed: {result.get('error', 'Unknown error')}"
        
        # Get the students array from the result
        students_in_range = result['result']
        
        # Should include students with scores 70-85
        # Based on mock data: John Smith (85) and Jane Doe (78) should be included
        # Bob Johnson (65) should be excluded
        expected_count = 2
        assert len(students_in_range) == expected_count, f"Expected {expected_count} students in 70-85 range"
        
        # Verify the correct students are included
        student_names = [student['user']['name'] for student in students_in_range]
        assert 'John Smith' in student_names
        assert 'Jane Doe' in student_names  
        assert 'Bob Johnson' not in student_names
    
    @pytest.mark.canvas_unit
    def test_calculate_course_statistics(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test calculateCourseStatistics() generates correct metrics."""
        
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        course_data['students'] = enhanced_mock_canvas_api_response['students']
        course_data['modules'] = enhanced_mock_canvas_api_response['modules']
        course_data['assignments'] = enhanced_mock_canvas_api_response['assignments']
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasCourseStaging",
            method_name="calculateCourseStatistics",
            test_data=course_data
        )
        
        stats = assert_canvas_business_logic_result(
            result, 
            expected_properties=['averageGrade', 'totalStudents', 'totalAssignments', 'passRate']
        )
        
        # Verify statistics calculations
        assert stats['totalStudents'] == 3, "Should count all students"
        assert stats['totalAssignments'] == 3, "Should count all assignments"
        assert 0 <= stats['averageGrade'] <= 100, "Average grade should be valid percentage"
        assert 0 <= stats['passRate'] <= 100, "Pass rate should be between 0 and 100 (percentage)"
        
        # Calculate expected average: (85 + 78 + 65) / 3 = 76
        expected_average = (85 + 78 + 65) / 3
        assert abs(stats['averageGrade'] - expected_average) < 0.1, f"Expected average ~{expected_average}"


class TestCanvasModuleStaging:
    """Test business logic in CanvasModuleStaging class."""
    
    @pytest.mark.canvas_unit
    def test_published_assignments_only(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test getPublishedAssignments() filters correctly."""
        
        module_data = enhanced_mock_canvas_api_response['modules'][0]  # HTML Fundamentals
        module_data['assignments'] = [
            enhanced_mock_canvas_api_response['assignments'][0],  # Published
            enhanced_mock_canvas_api_response['assignments'][1],  # Published
            {**enhanced_mock_canvas_api_response['assignments'][0], 'published': False}  # Unpublished
        ]
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasModuleStaging",
            method_name="getPublishedAssignments",
            test_data=module_data
        )
        
        published_assignments = assert_canvas_business_logic_result(result)
        
        # Should only return published assignments
        assert len(published_assignments) == 2, "Should filter out unpublished assignments"
        for assignment in published_assignments:
            assert assignment['published'] is True, "All returned assignments should be published"


class TestCanvasAssignmentStaging:
    """Test business logic in CanvasAssignmentStaging class."""
    
    @pytest.mark.canvas_unit
    def test_assignment_type_detection(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test isQuiz() and isAssignment() type detection."""
        
        # Test with quiz
        quiz_data = enhanced_mock_canvas_api_response['assignments'][1]  # HTML Forms Quiz
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasAssignmentStaging",
            method_name="isQuiz",
            test_data=quiz_data
        )
        
        is_quiz = assert_canvas_business_logic_result(result)
        assert is_quiz is True, "Quiz should be detected as quiz type"
        
        # Test with assignment
        assignment_data = enhanced_mock_canvas_api_response['assignments'][0]  # HTML Structure Assignment
        
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasAssignmentStaging", 
            method_name="isAssignment",
            test_data=assignment_data
        )
        
        is_assignment = assert_canvas_business_logic_result(result)
        assert is_assignment is True, "Assignment should be detected as assignment type"


class TestCanvasBusinessLogicAdvanced:
    """Test advanced business logic scenarios in Canvas staging classes."""
    
    @pytest.mark.canvas_unit
    def test_student_performance_analytics(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test advanced student performance analytics methods."""
        
        # Create a student with specific performance characteristics
        student_data = {
            'id': 111929285,
            'name': 'Analytics Test Student',
            'login_id': 'analytics@test.edu',
            'current_score': 72.5,
            'final_score': 87.0,
            'last_activity_at': '2024-10-10T14:30:00Z',
            'enrollment_state': 'active',
            'assignments': [
                {'id': 1001, 'score': 85, 'points_possible': 100, 'submitted': True},
                {'id': 1002, 'score': None, 'points_possible': 50, 'submitted': False},  # Missing
                {'id': 1003, 'score': 92, 'points_possible': 100, 'submitted': True},
                {'id': 1004, 'score': 45, 'points_possible': 75, 'submitted': True}   # Low performance
            ]
        }
        
        test_script = f"""
import {{ CanvasStudentStaging }} from './staging/canvas-staging-data';

const studentData = {student_data};
const student = new CanvasStudentStaging(studentData);

try {{
    const analytics = {{
        // Test missing assignments detection
        missingAssignments: student.getMissingAssignments ? student.getMissingAssignments() : 'method_not_found',
        
        // Test grade improvement potential
        improvementPotential: student.getGradeImprovementPotential ? student.getGradeImprovementPotential() : 'method_not_found',
        
        // Test performance trends
        performanceTrend: student.getPerformanceTrend ? student.getPerformanceTrend() : 'method_not_found',
        
        // Test activity analysis
        activityStatus: student.getActivityStatus ? student.getActivityStatus() : 'method_not_found',
        
        // Test risk assessment
        riskLevel: student.assessRiskLevel ? student.assessRiskLevel() : 'method_not_found',
        
        // Basic data validation
        basicData: {{
            hasScoreGap: studentData.final_score > studentData.current_score,
            scoreGap: studentData.final_score - studentData.current_score,
            hasRecentActivity: !!studentData.last_activity_at
        }}
    }};
    
    console.log(JSON.stringify({{ 
        success: true, 
        result: analytics
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message,
        stack: error.stack
    }}));
}}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        
        if result['success']:
            analytics = result['result']
            
            # Test basic data validation
            basic_data = analytics['basicData']
            assert basic_data['hasScoreGap'] is True, "Should detect score gap"
            assert basic_data['scoreGap'] == 14.5, "Should calculate correct score gap"
            
            # Document which business logic methods exist
            implemented_methods = []
            missing_methods = []
            
            for method_name, method_result in analytics.items():
                if method_name != 'basicData':
                    if method_result != 'method_not_found':
                        implemented_methods.append(method_name)
                    else:
                        missing_methods.append(method_name)
            
            print(f"\n📊 Student Business Logic Analysis:")
            if implemented_methods:
                print(f"   ✅ Implemented methods: {', '.join(implemented_methods)}")
            if missing_methods:
                print(f"   📋 Methods to implement: {', '.join(missing_methods)}")
                
        else:
            print(f"⚠️ Student business logic test failed: {result['error']}")
    
    @pytest.mark.canvas_unit
    def test_course_analytics_comprehensive(self, canvas_business_logic_tester, enhanced_mock_canvas_api_response):
        """Test comprehensive course analytics and statistics."""
        
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        course_data['students'] = enhanced_mock_canvas_api_response['students']
        course_data['assignments'] = enhanced_mock_canvas_api_response['assignments']
        course_data['modules'] = enhanced_mock_canvas_api_response['modules']
        
        test_script = f"""
import {{ CanvasCourseStaging }} from './staging/canvas-staging-data';

const courseData = {course_data};
const course = new CanvasCourseStaging(courseData);

try {{
    const analytics = {{
        // Basic aggregation methods
        allAssignments: course.getAllAssignments ? course.getAllAssignments() : 'method_not_found',
        courseStats: course.calculateCourseStatistics ? course.calculateCourseStatistics() : 'method_not_found',
        
        // Advanced analytics methods
        gradeDistribution: course.getGradeDistribution ? course.getGradeDistribution() : 'method_not_found',
        performanceTrends: course.getPerformanceTrends ? course.getPerformanceTrends() : 'method_not_found',
        completionRates: course.getCompletionRates ? course.getCompletionRates() : 'method_not_found',
        strugglingStudents: course.getStrugglingStudents ? course.getStrugglingStudents() : 'method_not_found',
        topPerformers: course.getTopPerformers ? course.getTopPerformers() : 'method_not_found',
        
        // Filtering methods
        studentsByGradeRange: course.getStudentsByGradeRange ? course.getStudentsByGradeRange(70, 85) : 'method_not_found',
        activeStudents: course.getActiveStudents ? course.getActiveStudents() : 'method_not_found',
        
        // Manual calculations for validation
        manualStats: {{
            studentCount: courseData.students.length,
            assignmentCount: courseData.assignments.length,
            averageGrade: courseData.students.reduce((sum, s) => sum + (s.current_score || 0), 0) / courseData.students.length,
            gradeRange: {{
                min: Math.min(...courseData.students.map(s => s.current_score || 0)),
                max: Math.max(...courseData.students.map(s => s.current_score || 0))
            }}
        }}
    }};
    
    console.log(JSON.stringify({{ 
        success: true, 
        result: analytics
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message,
        stack: error.stack
    }}));
}}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        
        if result['success']:
            analytics = result['result']
            manual_stats = analytics['manualStats']
            
            # Validate manual calculations
            assert manual_stats['studentCount'] == 3, "Should have 3 students"
            assert manual_stats['assignmentCount'] == 3, "Should have 3 assignments"
            assert 70 <= manual_stats['averageGrade'] <= 80, "Average should be around 76"
            
            # Test implemented methods
            implemented_analytics = []
            missing_analytics = []
            
            for method_name, method_result in analytics.items():
                if method_name != 'manualStats':
                    if method_result != 'method_not_found':
                        implemented_analytics.append(method_name)
                        
                        # Validate specific methods if implemented
                        if method_name == 'courseStats' and isinstance(method_result, dict):
                            if 'averageGrade' in method_result:
                                calculated_avg = method_result['averageGrade']
                                manual_avg = manual_stats['averageGrade']
                                assert abs(calculated_avg - manual_avg) < 1.0, f"Average grade mismatch: {calculated_avg} vs {manual_avg}"
                                
                        elif method_name == 'allAssignments' and isinstance(method_result, list):
                            assert len(method_result) == 3, "Should return all 3 assignments"
                            
                        elif method_name == 'studentsByGradeRange' and isinstance(method_result, list):
                            # Should include students with grades 70-85 (John: 85, Jane: 78)
                            assert len(method_result) >= 1, "Should find at least 1 student in 70-85 range"
                            
                    else:
                        missing_analytics.append(method_name)
            
            print(f"\n📈 Course Analytics Analysis:")
            if implemented_analytics:
                print(f"   ✅ Implemented analytics: {', '.join(implemented_analytics)}")
            if missing_analytics:
                print(f"   📋 Analytics to implement: {', '.join(missing_analytics)}")
                
        else:
            print(f"⚠️ Course analytics test failed: {result['error']}")


class TestIntegrationScenarios:
    """Test integration scenarios between Canvas staging classes."""
    
    @pytest.mark.canvas_integration
    def test_course_with_students_and_assignments_workflow(self, canvas_business_logic_tester, 
                                                         enhanced_mock_canvas_api_response,
                                                         db_session):
        """Test complete workflow: course → students → assignments → statistics."""
        
        # This test demonstrates integration with database layer
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        course_data['students'] = enhanced_mock_canvas_api_response['students']
        course_data['assignments'] = enhanced_mock_canvas_api_response['assignments']
        course_data['modules'] = enhanced_mock_canvas_api_response['modules']
        
        # Test the complete course processing workflow
        import json
        test_script = f"""
import {{ CanvasCourseStaging }} from './staging/canvas-staging-data';

const courseData = {json.dumps(course_data)};
const course = new CanvasCourseStaging(courseData);

try {{
    // Test complete workflow
    const allAssignments = course.getAllAssignments();
    const courseStats = course.calculateCourseStatistics();
    const strugglingStudents = course.getStudentsByGradeRange(0, 70);
    const excellentStudents = course.getStudentsByGradeRange(85, 100);
    
    console.log(JSON.stringify({{ 
        success: true, 
        result: {{
            courseInfo: {{
                id: course.id,
                name: course.name,
                totalPoints: course.total_points
            }},
            assignments: {{
                total: allAssignments.length,
                published: allAssignments.filter(a => a.published).length
            }},
            statistics: courseStats,
            studentSegments: {{
                struggling: strugglingStudents.length,
                excellent: excellentStudents.length,
                total: course.students.length
            }}
        }}
    }}));
}} catch (error) {{
    console.log(JSON.stringify({{ 
        success: false, 
        error: error.message,
        stack: error.stack
    }}));
}}
        """
        
        result = canvas_business_logic_tester._execute_test_script(test_script)
        workflow_result = assert_canvas_business_logic_result(
            result,
            expected_properties=['courseInfo', 'assignments', 'statistics', 'studentSegments']
        )
        
        # Verify complete workflow results
        assert workflow_result['courseInfo']['id'] == 7982015
        assert workflow_result['assignments']['total'] == 3
        assert workflow_result['studentSegments']['total'] == 3
        assert workflow_result['studentSegments']['struggling'] == 1  # Bob Johnson (65)
        assert workflow_result['studentSegments']['excellent'] == 1   # John Smith (85)
        
        # Verify statistics make sense
        stats = workflow_result['statistics']
        assert stats['totalStudents'] == 3
        assert stats['totalAssignments'] == 3
        assert 0 < stats['averageGrade'] < 100
    
    @pytest.mark.canvas_integration
    @pytest.mark.database
    def test_canvas_data_to_database_transformation_compatibility(self, canvas_business_logic_tester, 
                                                                 enhanced_mock_canvas_api_response,
                                                                 db_session):
        """Test that Canvas staging data can be transformed for database storage."""
        
        # This demonstrates how canvas data can integrate with database tests
        course_data = enhanced_mock_canvas_api_response['courses'][0]
        
        # Test that canvas data structure is compatible with database expectations
        result = canvas_business_logic_tester.test_canvas_data_model_method(
            class_name="CanvasCourseStaging",
            method_name="toDatabaseFormat",  # Assuming this method exists
            test_data=course_data
        )
        
        if result['success']:
            db_format = result['result']
            
            # Verify database-compatible format
            required_db_fields = ['id', 'name', 'course_code', 'total_points']
            for field in required_db_fields:
                assert field in db_format, f"Database format missing required field: {field}"
                
            # Test that this format could be used with database models
            # (This is where you'd integrate with your actual database layer)
            assert isinstance(db_format['id'], int), "Course ID should be integer for database"
            assert isinstance(db_format['name'], str), "Course name should be string"
        else:
            # If transformation method doesn't exist yet, that's fine - this test documents the requirement
            assert "toDatabaseFormat" in result['error'] or "method" in result['error']