"""
Unit tests for database configuration module.

Tests the DatabaseConfig class and related configuration functions
for all supported environments and edge cases.
"""

import pytest
import os
import tempfile
import warnings
from unittest.mock import patch, MagicMock

from database.config import (
    DatabaseConfig, get_config, get_database_url,
    create_engine_for_environment, validate_configuration
)
from database.utils.exceptions import ConfigurationError


class TestDatabaseConfig:
    """Test suite for DatabaseConfig class."""
    
    @pytest.mark.unit
    def test_development_config(self):
        """Test development environment configuration."""
        config = DatabaseConfig('dev')
        
        assert config.environment == 'dev'
        assert config.database_url.startswith('sqlite:///')
        assert config.is_sqlite() is True
        assert config.is_in_memory() is False
        
        # Test engine kwargs
        kwargs = config.engine_kwargs
        assert kwargs['echo'] is True
        assert kwargs['pool_pre_ping'] is True
        assert 'check_same_thread' in kwargs['connect_args']
    
    @pytest.mark.unit
    def test_test_config(self):
        """Test test environment configuration."""
        config = DatabaseConfig('test')
        
        assert config.environment == 'test'
        assert config.database_url == 'sqlite:///:memory:'
        assert config.is_sqlite() is True
        assert config.is_in_memory() is True
        
        # Test engine kwargs
        kwargs = config.engine_kwargs
        assert kwargs['echo'] is False
        assert 'check_same_thread' in kwargs['connect_args']
    
    @pytest.mark.unit
    def test_production_config_no_url(self):
        """Test production config without DATABASE_URL environment variable."""
        with patch.dict(os.environ, {}, clear=True):
            with warnings.catch_warnings(record=True) as w:
                config = DatabaseConfig('prod')
                
                # Should warn about fallback to SQLite
                assert len(w) == 1
                assert "falling back to SQLite" in str(w[0].message)
                
                assert config.environment == 'prod'
                assert config.database_url.startswith('sqlite:///')
                assert config.is_sqlite() is True
    
    @pytest.mark.unit
    def test_production_config_with_url(self):
        """Test production config with DATABASE_URL environment variable."""
        test_url = "postgresql://user:pass@localhost/testdb"
        
        with patch.dict(os.environ, {'DATABASE_URL': test_url}):
            config = DatabaseConfig('prod')
            
            assert config.database_url == test_url
            assert config.is_sqlite() is False
            assert config.is_in_memory() is False
    
    @pytest.mark.unit
    def test_invalid_environment(self):
        """Test configuration with invalid environment."""
        with pytest.raises(ValueError, match="Unknown environment"):
            DatabaseConfig('invalid_env')
    
    @pytest.mark.unit
    def test_custom_dev_database_path(self):
        """Test development config with custom database path."""
        custom_path = "custom_test.db"
        
        with patch.dict(os.environ, {'DEV_DATABASE_PATH': custom_path}):
            config = DatabaseConfig('dev')
            assert config.database_url == f"sqlite:///{custom_path}"
    
    @pytest.mark.unit
    def test_get_database_path(self):
        """Test database path extraction for SQLite."""
        config = DatabaseConfig('dev')
        path = config.get_database_path()
        assert path == config.database_url.replace('sqlite:///', '')
        
        # Test with non-SQLite database
        with patch.dict(os.environ, {'DATABASE_URL': 'postgresql://localhost/test'}):
            config = DatabaseConfig('prod')
            with pytest.raises(ValueError, match="only available for SQLite"):
                config.get_database_path()
    
    @pytest.mark.unit 
    def test_create_engine(self):
        """Test SQLAlchemy engine creation."""
        config = DatabaseConfig('test')
        engine = config.create_engine()
        
        assert engine is not None
        assert str(engine.url) == 'sqlite:///:memory:'
    
    @pytest.mark.unit
    def test_config_string_representation(self):
        """Test string representation of config object."""
        config = DatabaseConfig('test')
        repr_str = repr(config)
        
        assert 'DatabaseConfig' in repr_str
        assert 'test' in repr_str
        assert 'sqlite:///:memory:' in repr_str


class TestConfigurationFunctions:
    """Test suite for configuration utility functions."""
    
    @pytest.mark.unit
    def test_get_config_singleton(self):
        """Test that get_config returns singleton instance."""
        config1 = get_config('test')
        config2 = get_config()  # Should return same instance
        
        assert config1 is config2
        assert config1.environment == 'test'
    
    @pytest.mark.unit
    def test_get_config_new_environment(self):
        """Test that get_config creates new instance with different environment.""" 
        config1 = get_config('test')
        config2 = get_config('dev')  # Should create new instance
        
        assert config1 is not config2
        assert config1.environment == 'test'
        assert config2.environment == 'dev'
    
    @pytest.mark.unit
    def test_get_database_url(self):
        """Test get_database_url function."""
        url = get_database_url('test')
        assert url == 'sqlite:///:memory:'
        
        url = get_database_url('dev')
        assert url.startswith('sqlite:///')
    
    @pytest.mark.unit
    def test_create_engine_for_environment(self):
        """Test engine creation for different environments."""
        engine = create_engine_for_environment('test')
        assert str(engine.url) == 'sqlite:///:memory:'
        
        engine = create_engine_for_environment('dev')
        assert str(engine.url).startswith('sqlite:///')
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_validate_configuration_valid(self):
        """Test configuration validation with valid config."""
        # Test environment should always be valid
        result = validate_configuration('test')
        assert result is True
    
    @pytest.mark.unit
    def test_validate_configuration_invalid(self):
        """Test configuration validation with invalid config."""
        with patch('database.config.DatabaseConfig') as mock_config:
            mock_instance = MagicMock()
            mock_instance.create_engine.side_effect = Exception("Connection failed")
            mock_config.return_value = mock_instance
            
            with pytest.raises(ValueError, match="configuration validation failed"):
                validate_configuration('test')


class TestEnvironmentVariables:
    """Test suite for environment variable handling."""
    
    @pytest.mark.unit
    def test_database_env_variable(self):
        """Test DATABASE_ENV environment variable."""
        with patch.dict(os.environ, {'DATABASE_ENV': 'prod'}):
            config = DatabaseConfig()  # No explicit environment
            assert config.environment == 'prod'
    
    @pytest.mark.unit
    def test_default_environment(self):
        """Test default environment when no env var set."""
        with patch.dict(os.environ, {}, clear=True):
            config = DatabaseConfig()
            assert config.environment == 'dev'
    
    @pytest.mark.unit
    def test_explicit_environment_overrides_env_var(self):
        """Test that explicit environment overrides env variable."""
        with patch.dict(os.environ, {'DATABASE_ENV': 'prod'}):
            config = DatabaseConfig('test')  # Explicit override
            assert config.environment == 'test'


class TestConfigurationEdgeCases:
    """Test suite for edge cases and error conditions."""
    
    @pytest.mark.unit
    def test_empty_database_url(self):
        """Test handling of empty DATABASE_URL."""
        with patch.dict(os.environ, {'DATABASE_URL': ''}):
            with warnings.catch_warnings(record=True) as w:
                config = DatabaseConfig('prod')
                
                # Should fallback to SQLite and warn
                assert len(w) == 1
                assert config.is_sqlite() is True
    
    @pytest.mark.unit
    def test_malformed_database_url(self):
        """Test handling of malformed DATABASE_URL."""
        with patch.dict(os.environ, {'DATABASE_URL': 'not-a-valid-url'}):
            config = DatabaseConfig('prod')
            
            # Should accept the URL as-is (SQLAlchemy will handle validation)
            assert config.database_url == 'not-a-valid-url'
    
    @pytest.mark.unit
    def test_engine_creation_failure(self):
        """Test engine creation with invalid configuration."""
        # This is more of an integration test, but good to have
        with patch.dict(os.environ, {'DATABASE_URL': 'invalid://bad-url'}):
            config = DatabaseConfig('prod')
            
            # Engine creation might fail depending on SQLAlchemy version
            # Just test that we can create the config without immediate error
            assert config.database_url == 'invalid://bad-url'


class TestFileBasedDatabase:
    """Test suite for file-based database operations."""
    
    @pytest.mark.unit
    def test_temporary_database_file(self, temporary_db_file):
        """Test configuration with temporary database file."""
        custom_config = {
            'database_url': f'sqlite:///{temporary_db_file}',
            'echo': False,
            'connect_args': {'check_same_thread': False}
        }
        
        # Create a custom config instance
        config = DatabaseConfig('dev')
        config._config = custom_config
        
        assert config.database_url == f'sqlite:///{temporary_db_file}'
        assert config.get_database_path() == temporary_db_file
        
        # Test that engine can be created
        engine = config.create_engine()
        assert engine is not None


# Integration test that can be run separately
@pytest.mark.integration
@pytest.mark.database  
class TestConfigurationIntegration:
    """Integration tests for configuration with actual database operations."""
    
    def test_full_configuration_workflow(self, temporary_db_file):
        """Test complete configuration workflow with database operations."""
        # Create config for file-based database
        custom_config = DatabaseConfig('dev')
        custom_config._config['database_url'] = f'sqlite:///{temporary_db_file}'
        
        # Create engine and test connection
        engine = custom_config.create_engine()
        
        with engine.connect() as conn:
            from sqlalchemy import text
            result = conn.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        
        # Validate configuration
        assert validate_configuration('test') is True