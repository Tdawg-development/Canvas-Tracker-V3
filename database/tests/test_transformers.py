"""
Unit Tests for Scalable Transformer System

Tests the new configuration-driven transformation architecture including:
- Individual transformer functionality
- Registry system behavior
- Configuration validation
- Field filtering capabilities
- Legacy compatibility
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from database.operations.transformers import (
    EntityType,
    EntityTransformer,
    TransformerRegistry,
    TransformationContext,
    TransformationResult,
    CourseTransformer,
    StudentTransformer,
    LegacyCanvasDataTransformer,
    ValidationSeverity,
    ValidationIssue,
    ConfigurationValidationResult,
    ConfigurationValidator,
    validate_sync_configuration,
    get_global_registry
)


class TestEntityTransformerBase(unittest.TestCase):
    """Test the base EntityTransformer functionality."""
    
    def setUp(self):
        """Set up test transformer."""
        # Create a concrete test transformer
        class TestTransformer(EntityTransformer):
            @property
            def entity_type(self):
                return EntityType.COURSES
            
            @property
            def required_fields(self):
                return {'id', 'name'}
            
            @property
            def optional_fields(self):
                return {'description', 'start_date'}
            
            def transform_entity(self, entity_data, context):
                return {
                    'transformed_id': entity_data['id'],
                    'transformed_name': entity_data['name'],
                    'context_type': context.entity_type.value
                }
        
        self.transformer = TestTransformer()
    
    def test_field_filtering_basic(self):
        """Test basic field filtering functionality."""
        entity_data = {
            'id': 123,
            'name': 'Test Course',
            'description': 'A test course',
            'extra_field': 'should be filtered'
        }
        
        # No configuration - should return all data
        context = TransformationContext(EntityType.COURSES, 1)
        filtered = self.transformer.apply_field_filtering(entity_data, context)
        self.assertEqual(filtered, entity_data)
        
        # Configuration with field filtering
        config = {
            'fields': {
                'courses': {
                    'description': True
                }
            }
        }
        context = TransformationContext(EntityType.COURSES, 1, configuration=config)
        filtered = self.transformer.apply_field_filtering(entity_data, context)
        
        # Should include required fields + enabled optional fields
        expected = {
            'id': 123,
            'name': 'Test Course',
            'description': 'A test course'
        }
        self.assertEqual(filtered, expected)
    
    def test_validation(self):
        """Test entity data validation."""
        # Valid data
        valid_data = {'id': 123, 'name': 'Test Course'}
        errors = self.transformer.validate_entity_data(valid_data)
        self.assertEqual(errors, [])
        
        # Missing required field
        invalid_data = {'id': 123}  # Missing 'name'
        errors = self.transformer.validate_entity_data(invalid_data)
        self.assertTrue(any('name' in error for error in errors))
    
    def test_batch_transformation(self):
        """Test batch transformation with result tracking."""
        entities_data = [
            {'id': 1, 'name': 'Course 1'},
            {'id': 2, 'name': 'Course 2'},
            {'name': 'Invalid Course'},  # Missing required 'id'
        ]
        
        context = TransformationContext(EntityType.COURSES, len(entities_data))
        result = self.transformer.transform_batch(entities_data, context)
        
        self.assertIsInstance(result, TransformationResult)
        self.assertEqual(result.source_count, 3)
        self.assertEqual(result.transformed_count, 2)
        self.assertEqual(result.skipped_count, 1)
        self.assertTrue(result.success)
        self.assertEqual(len(result.errors), 1)


class TestCourseTransformer(unittest.TestCase):
    """Test the CourseTransformer specifically."""
    
    def setUp(self):
        """Set up course transformer."""
        self.transformer = CourseTransformer()
    
    def test_basic_course_transformation(self):
        """Test basic course data transformation."""
        course_data = {
            'id': 12345,
            'name': 'Test Course',
            'course_code': 'TEST-101',
            'workflow_state': 'available',
            'start_at': '2024-01-01T00:00:00Z',
            'end_at': '2024-06-01T00:00:00Z'
        }
        
        context = TransformationContext(EntityType.COURSES, 1)
        result = self.transformer.transform_entity(course_data, context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 12345)
        self.assertEqual(result['name'], 'Test Course')
        self.assertEqual(result['course_code'], 'TEST-101')
        self.assertEqual(result['workflow_state'], 'available')
        self.assertIsInstance(result['last_synced'], datetime)
    
    def test_configuration_driven_fields(self):
        """Test configuration-driven field inclusion."""
        course_data = {
            'id': 12345,
            'name': 'Test Course',
            'course_code': 'TEST-101',
            'is_public': True,
            'storage_quota_mb': 500,
            'locale': 'en'
        }
        
        # Configuration with extended info enabled
        config = {
            'fields': {
                'courses': {
                    'extended_info': True,
                    'public_info': True,
                    'settings': True
                }
            }
        }
        
        context = TransformationContext(EntityType.COURSES, 1, configuration=config)
        result = self.transformer.transform_entity(course_data, context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['is_public'], True)
        self.assertEqual(result['storage_quota_mb'], 500)
        self.assertEqual(result['locale'], 'en')
    
    def test_datetime_parsing(self):
        """Test Canvas datetime parsing."""
        # Test various datetime formats
        test_cases = [
            '2024-01-01T00:00:00Z',
            '2024-01-01T00:00:00.000Z',
            '2024-01-01T00:00:00+00:00',
            '2024-01-01T00:00:00',
        ]
        
        for date_string in test_cases:
            result = self.transformer._parse_canvas_datetime(date_string)
            self.assertIsInstance(result, datetime)
            self.assertEqual(result.tzinfo, timezone.utc)
    
    def test_calendar_ics_extraction(self):
        """Test calendar ICS URL extraction."""
        course_data = {
            'id': 12345,
            'name': 'Test Course',
            'course_code': 'TEST-101',
            'calendar': {
                'ics': 'https://canvas.example.com/calendar.ics'
            }
        }
        
        ics_url = self.transformer._extract_calendar_ics(course_data)
        self.assertEqual(ics_url, 'https://canvas.example.com/calendar.ics')
        
        # Test with missing calendar
        course_data_no_cal = {
            'id': 12345,
            'name': 'Test Course',
            'course_code': 'TEST-101'
        }
        
        ics_url = self.transformer._extract_calendar_ics(course_data_no_cal)
        self.assertEqual(ics_url, '')


class TestStudentTransformer(unittest.TestCase):
    """Test the StudentTransformer specifically."""
    
    def setUp(self):
        """Set up student transformer."""
        self.transformer = StudentTransformer()
    
    def test_basic_student_transformation(self):
        """Test basic student data transformation."""
        student_data = {
            'id': 2001,
            'user_id': 2001,
            'created_at': '2024-01-01T00:00:00Z',
            'user': {
                'id': 2001,
                'name': 'John Doe',
                'login_id': 'john.doe',
                'email': 'john@example.com'
            },
            'grades': {
                'current_score': 85.5,
                'final_score': 87.0
            }
        }
        
        context = TransformationContext(EntityType.STUDENTS, 1)
        result = self.transformer.transform_entity(student_data, context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['id'], 2001)
        self.assertEqual(result['student_id'], 2001)
        self.assertEqual(result['user_id'], 2001)
        self.assertEqual(result['name'], 'John Doe')
        self.assertEqual(result['login_id'], 'john.doe')
        self.assertEqual(result['email'], 'john@example.com')
        self.assertEqual(result['current_score'], 86)  # Normalized to int
        self.assertEqual(result['final_score'], 87)
    
    def test_configuration_field_filtering(self):
        """Test configuration-driven field filtering for students."""
        student_data = {
            'id': 2001,
            'user_id': 2001,
            'created_at': '2024-01-01T00:00:00Z',
            'last_activity_at': '2024-01-10T12:00:00Z',
            'user': {
                'id': 2001,
                'name': 'John Doe',
                'login_id': 'john.doe',
                'email': 'john@example.com'
            },
            'grades': {
                'current_score': 85.5,
                'final_score': 87.0
            }
        }
        
        # Configuration with only basic info enabled
        config = {
            'fields': {
                'students': {
                    'basicInfo': True,
                    'scores': False,
                    'analytics': False,
                    'enrollmentDetails': False
                }
            }
        }
        
        context = TransformationContext(EntityType.STUDENTS, 1, configuration=config)
        result = self.transformer.transform_entity(student_data, context)
        
        self.assertIsNotNone(result)
        self.assertIn('name', result)
        self.assertIn('login_id', result)
        self.assertIn('email', result)
        # Scores should not be included (or should be default 0)
        self.assertNotIn('last_activity_at', result)
    
    def test_flat_structure_handling(self):
        """Test handling of flat student data structure."""
        student_data = {
            'id': 2001,
            'user_id': 2001,
            'name': 'Jane Smith',
            'login_id': 'jane.smith',
            'email': 'jane@example.com',
            'current_score': 92.5,
            'final_score': 94.0,
            'created_at': '2024-01-01T00:00:00Z'
        }
        
        context = TransformationContext(EntityType.STUDENTS, 1)
        result = self.transformer.transform_entity(student_data, context)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['name'], 'Jane Smith')
        self.assertEqual(result['current_score'], 92)  # Normalized (92.5 rounds to 92)
        self.assertEqual(result['final_score'], 94)
    
    def test_score_normalization(self):
        """Test score normalization functionality."""
        # Test various score formats
        test_cases = [
            (85.7, 86),
            (92, 92),
            ('88.3', 88),
            (None, 0),
            ('invalid', 0),
            (100.0, 100),
            (0, 0)
        ]
        
        for input_score, expected in test_cases:
            result = self.transformer._normalize_score(input_score)
            self.assertEqual(result, expected)


class TestTransformerRegistry(unittest.TestCase):
    """Test the TransformerRegistry functionality."""
    
    def setUp(self):
        """Set up test registry."""
        self.registry = TransformerRegistry()
    
    def test_transformer_registration(self):
        """Test transformer registration and retrieval."""
        transformer = CourseTransformer()
        
        self.registry.register_transformer(transformer)
        
        self.assertTrue(self.registry.has_transformer(EntityType.COURSES))
        retrieved = self.registry.get_transformer(EntityType.COURSES)
        self.assertIs(retrieved, transformer)
    
    def test_unknown_transformer_error(self):
        """Test error handling for unknown transformers."""
        with self.assertRaises(ValueError):
            self.registry.get_transformer(EntityType.DISCUSSIONS)
    
    def test_entity_transformation_with_config(self):
        """Test entity transformation with configuration."""
        # Register transformers
        self.registry.register_transformer(CourseTransformer())
        self.registry.register_transformer(StudentTransformer())
        
        # Sample data
        canvas_data = {
            'courses': [
                {'id': 123, 'name': 'Test Course', 'course_code': 'TEST-101'}
            ],
            'students': [
                {
                    'id': 2001,
                    'user_id': 2001,
                    'user': {'id': 2001, 'name': 'John Doe', 'login_id': 'john'},
                    'grades': {'current_score': 85}
                }
            ]
        }
        
        # Configuration
        config = {
            'entities': {
                'courses': True,
                'students': True
            }
        }
        
        results = self.registry.transform_entities(canvas_data, config)
        
        self.assertIn('courses', results)
        self.assertIn('students', results)
        self.assertTrue(results['courses'].success)
        self.assertTrue(results['students'].success)
        self.assertEqual(len(results['courses'].transformed_data), 1)
        self.assertEqual(len(results['students'].transformed_data), 1)
    
    def test_disabled_entity_skipping(self):
        """Test that disabled entities are skipped."""
        self.registry.register_transformer(CourseTransformer())
        
        canvas_data = {
            'courses': [
                {'id': 123, 'name': 'Test Course', 'course_code': 'TEST-101'}
            ]
        }
        
        config = {
            'entities': {
                'courses': False  # Disabled
            }
        }
        
        results = self.registry.transform_entities(canvas_data, config)
        
        # Should be empty since courses disabled
        self.assertEqual(len(results), 0)


class TestConfigurationValidation(unittest.TestCase):
    """Test the configuration validation system."""
    
    def setUp(self):
        """Set up test registry with transformers."""
        self.registry = TransformerRegistry()
        self.registry.register_transformer(CourseTransformer())
        self.registry.register_transformer(StudentTransformer())
        self.validator = ConfigurationValidator(self.registry)
    
    def test_valid_configuration(self):
        """Test validation of valid configuration."""
        config = {
            'entities': {
                'courses': True,
                'students': True,
                'assignments': False
            },
            'fields': {
                'students': {
                    'basicInfo': True,
                    'scores': True,
                    'analytics': False
                }
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertTrue(result.valid)
        self.assertEqual(len(result.errors), 0)
        self.assertIsNotNone(result.performance_estimate)
    
    def test_missing_entities_error(self):
        """Test error for missing entities section."""
        config = {
            'fields': {
                'students': {'basicInfo': True}
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.valid)
        self.assertTrue(any(
            issue.issue_code == 'MISSING_ENTITIES' 
            for issue in result.errors
        ))
    
    def test_unknown_entity_warning(self):
        """Test warning for unknown entity types."""
        config = {
            'entities': {
                'courses': True,
                'unknown_entity': True  # Unknown
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertTrue(result.valid)  # Should be valid with warnings
        self.assertTrue(any(
            issue.issue_code == 'UNKNOWN_ENTITY_TYPE' 
            for issue in result.warnings
        ))
    
    def test_no_transformer_error(self):
        """Test error for entities without transformers."""
        config = {
            'entities': {
                'courses': True,
                'discussions': True  # No transformer available
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertFalse(result.valid)
        self.assertTrue(any(
            issue.issue_code == 'NO_TRANSFORMER_AVAILABLE'
            for issue in result.errors
        ))
    
    def test_performance_estimation(self):
        """Test performance impact estimation."""
        config = {
            'entities': {
                'courses': True,
                'students': True
            },
            'fields': {
                'students': {
                    'basicInfo': True,
                    'scores': True,
                    'analytics': True
                }
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        self.assertIsNotNone(result.performance_estimate)
        estimate = result.performance_estimate
        self.assertIn('enabled_entities', estimate)
        self.assertIn('performance_category', estimate)
        self.assertIn('api_call_estimate', estimate)
        self.assertEqual(estimate['enabled_entities'], 2)
    
    def test_transformer_specific_validation(self):
        """Test that transformer-specific validation is called during configuration validation."""
        config = {
            'entities': {
                'courses': True,
                'students': True
            },
            'fields': {
                'courses': {
                    'unknown_field': True,  # Should trigger course-specific validation
                    'extended_info': True
                },
                'students': {
                    'analytics': True,
                    'basicInfo': False  # Should trigger student-specific validation warning
                }
            }
        }
        
        result = self.validator.validate_configuration(config)
        
        # Should have warnings from transformer-specific validation
        self.assertTrue(any(
            issue.issue_code == 'UNKNOWN_COURSE_FIELD'
            for issue in result.warnings
        ))
        
        self.assertTrue(any(
            issue.issue_code == 'INCOMPLETE_STUDENT_CONFIG'
            for issue in result.warnings
        ))


class TestLegacyCompatibility(unittest.TestCase):
    """Test legacy compatibility with existing interfaces."""
    
    def test_legacy_transformer_interface(self):
        """Test that legacy transformer maintains interface compatibility."""
        config = {
            'entities': {
                'courses': True,
                'students': True
            }
        }
        
        transformer = LegacyCanvasDataTransformer(config)
        
        # Mock Canvas data in legacy TypeScript format (legacy transformer expects 'course' not 'courses')
        canvas_data = {
            'success': True,
            'course': {'id': 123, 'name': 'Test Course', 'course_code': 'TEST-101'},  # Legacy format expects 'course' object
            'students': [
                {
                    'id': 2001,
                    'user_id': 2001,
                    'user': {'id': 2001, 'name': 'John Doe', 'login_id': 'john'},
                    'grades': {'current_score': 85}
                }
            ],
            'modules': []
        }
        
        result = transformer.transform_canvas_staging_data(canvas_data)
        
        # Should maintain legacy format
        self.assertIn('courses', result)
        self.assertIn('students', result)
        self.assertIn('assignments', result)
        self.assertIn('enrollments', result)
        self.assertEqual(len(result['courses']), 1)
        self.assertEqual(len(result['students']), 1)
    
    def test_legacy_validation_interface(self):
        """Test legacy validation interface."""
        canvas_data = {
            'success': True,
            'course': {'id': 123, 'name': 'Test Course', 'course_code': 'TEST-101'},
            'students': [],
            'modules': []
        }
        
        transformer = LegacyCanvasDataTransformer()
        summary = transformer.get_transformation_summary(canvas_data)
        
        self.assertTrue(summary['valid_structure'])
        self.assertEqual(summary['course_count'], 1)
        self.assertEqual(summary['student_count'], 0)


class TestGlobalRegistry(unittest.TestCase):
    """Test global registry functionality."""
    
    def test_global_registry_initialization(self):
        """Test that global registry is properly initialized."""
        registry = get_global_registry()
        
        self.assertIsInstance(registry, TransformerRegistry)
        
        # Should have course and student transformers registered
        self.assertTrue(registry.has_transformer(EntityType.COURSES))
        self.assertTrue(registry.has_transformer(EntityType.STUDENTS))
    
    def test_registry_status(self):
        """Test registry status reporting."""
        registry = get_global_registry()
        status = registry.get_registry_status()
        
        self.assertIn('registered_transformers', status)
        self.assertIn('available_entity_types', status)
        self.assertIn('transformer_details', status)
        self.assertGreaterEqual(status['registered_transformers'], 2)


if __name__ == '__main__':
    unittest.main()