"""
Database configuration and connection settings for Canvas Tracker V3.

This module handles:
- Database URL configuration for different environments
- SQLAlchemy engine configuration
- Connection pooling and performance settings
- Environment-specific database settings
"""

import os
from typing import Dict, Any
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


class DatabaseConfig:
    """
    Database configuration class that handles different environments
    and provides engine creation with appropriate settings.
    """
    
    # Default configuration values
    DEFAULT_SQLITE_PATH = "canvas_tracker.db"
    DEFAULT_POOL_SIZE = 5
    DEFAULT_MAX_OVERFLOW = 10
    DEFAULT_POOL_TIMEOUT = 30
    
    def __init__(self, environment: str = None):
        """
        Initialize database configuration.
        
        Args:
            environment (str, optional): Environment name ('dev', 'test', 'prod'). 
                                       Defaults to checking DATABASE_ENV env var or 'dev'.
        """
        self.environment = environment or os.getenv('DATABASE_ENV', 'dev')
        self._config = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """
        Load configuration based on environment.
        
        Returns:
            Dict[str, Any]: Configuration dictionary for the current environment
        """
        configs = {
            'dev': self._get_development_config(),
            'test': self._get_test_config(),
            'prod': self._get_production_config()
        }
        
        if self.environment not in configs:
            raise ValueError(f"Unknown environment: {self.environment}")
        
        return configs[self.environment]
    
    def _get_development_config(self) -> Dict[str, Any]:
        """Development environment configuration."""
        db_path = os.getenv('DEV_DATABASE_PATH', self.DEFAULT_SQLITE_PATH)
        
        return {
            'database_url': f"sqlite:///{db_path}",
            'echo': True,  # Log all SQL statements for debugging
            'pool_pre_ping': True,  # Validate connections before use
            'connect_args': {
                'check_same_thread': False,  # Allow SQLite usage across threads
                'timeout': 20  # Connection timeout for SQLite
            },
            'pool_size': 1,  # SQLite doesn't support connection pooling
            'max_overflow': 0,
            'pool_timeout': self.DEFAULT_POOL_TIMEOUT
        }
    
    def _get_test_config(self) -> Dict[str, Any]:
        """Test environment configuration - uses in-memory SQLite."""
        return {
            'database_url': "sqlite:///:memory:",
            'echo': False,  # Don't spam test output with SQL
            'connect_args': {
                'check_same_thread': False
            }
            # SQLite doesn't support pool_size, max_overflow, or pool_timeout
        }
    
    def _get_production_config(self) -> Dict[str, Any]:
        """Production environment configuration."""
        # Production should use PostgreSQL or similar
        database_url = os.getenv('DATABASE_URL')
        
        if not database_url:
            # Fallback to SQLite for now, but log warning
            import warnings
            warnings.warn("No DATABASE_URL found, falling back to SQLite for production")
            database_url = f"sqlite:///{self.DEFAULT_SQLITE_PATH}"
        
        return {
            'database_url': database_url,
            'echo': False,  # Don't log SQL in production
            'pool_pre_ping': True,
            'pool_size': self.DEFAULT_POOL_SIZE,
            'max_overflow': self.DEFAULT_MAX_OVERFLOW,
            'pool_timeout': self.DEFAULT_POOL_TIMEOUT,
            'pool_recycle': 3600  # Recycle connections every hour
        }
    
    @property
    def database_url(self) -> str:
        """Get the database URL for the current environment."""
        return self._config['database_url']
    
    @property
    def engine_kwargs(self) -> Dict[str, Any]:
        """
        Get SQLAlchemy engine creation arguments.
        
        Returns:
            Dict[str, Any]: Arguments to pass to create_engine()
        """
        # Return all config except database_url (that's passed separately)
        return {k: v for k, v in self._config.items() if k != 'database_url'}
    
    def create_engine(self) -> Engine:
        """
        Create and configure SQLAlchemy engine.
        
        Returns:
            Engine: Configured SQLAlchemy engine
        """
        return create_engine(
            self.database_url,
            **self.engine_kwargs
        )
    
    def get_database_path(self) -> str:
        """
        Get the database file path (for SQLite only).
        
        Returns:
            str: Path to database file, or None if not using SQLite
            
        Raises:
            ValueError: If not using SQLite database
        """
        if not self.database_url.startswith('sqlite:'):
            raise ValueError("Database path only available for SQLite databases")
        
        # Extract path from sqlite:///path format
        return self.database_url.replace('sqlite:///', '')
    
    def is_sqlite(self) -> bool:
        """Check if current configuration uses SQLite."""
        return self.database_url.startswith('sqlite:')
    
    def is_in_memory(self) -> bool:
        """Check if current configuration uses in-memory database."""
        return self.database_url == "sqlite:///:memory:"
    
    def __repr__(self):
        """String representation of the configuration."""
        return f"<DatabaseConfig(env='{self.environment}', url='{self.database_url}')>"


# Global configuration instances for easy access
_config_instance = None


def get_config(environment: str = None) -> DatabaseConfig:
    """
    Get or create global database configuration instance.
    
    Args:
        environment (str, optional): Environment name. If not provided,
                                   uses existing instance or creates new one.
    
    Returns:
        DatabaseConfig: Database configuration instance
    """
    global _config_instance
    
    if _config_instance is None or environment is not None:
        _config_instance = DatabaseConfig(environment)
    
    return _config_instance


def get_database_url(environment: str = None) -> str:
    """
    Get database URL for the specified environment.
    
    Args:
        environment (str, optional): Environment name
    
    Returns:
        str: Database URL
    """
    return get_config(environment).database_url


def create_engine_for_environment(environment: str = None) -> Engine:
    """
    Create SQLAlchemy engine for the specified environment.
    
    Args:
        environment (str, optional): Environment name
    
    Returns:
        Engine: Configured SQLAlchemy engine
    """
    return get_config(environment).create_engine()


# Environment-specific convenience functions
def get_development_engine() -> Engine:
    """Get engine configured for development environment."""
    return create_engine_for_environment('dev')


def get_test_engine() -> Engine:
    """Get engine configured for test environment."""
    return create_engine_for_environment('test')


def get_production_engine() -> Engine:
    """Get engine configured for production environment."""
    return create_engine_for_environment('prod')


# Configuration validation
def validate_configuration(environment: str = None) -> bool:
    """
    Validate that the database configuration is correct.
    
    Args:
        environment (str, optional): Environment to validate
    
    Returns:
        bool: True if configuration is valid
        
    Raises:
        ValueError: If configuration is invalid
    """
    config = get_config(environment)
    
    # Test engine creation
    try:
        engine = config.create_engine()
        
        # Test basic connection (for non-in-memory databases)
        if not config.is_in_memory():
            with engine.connect() as conn:
                from sqlalchemy import text
                # Simple test query
                conn.execute(text("SELECT 1"))
        
        return True
        
    except Exception as e:
        raise ValueError(f"Database configuration validation failed: {e}")


if __name__ == "__main__":
    # Configuration testing script
    print("Testing database configurations...")
    
    for env in ['dev', 'test', 'prod']:
        try:
            config = DatabaseConfig(env)
            print(f"✓ {env}: {config}")
            
            # Test engine creation
            engine = config.create_engine()
            print(f"  Engine created successfully")
            
        except Exception as e:
            print(f"✗ {env}: Failed - {e}")
    
    print("\nDone!")