"""
Session management and database connection handling for Canvas Tracker V3.

This module provides:
- Session factory and management
- Database connection lifecycle
- Transaction handling utilities
- Context managers for clean database operations
"""

import logging
from contextlib import contextmanager
from typing import Optional, Generator, Any
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, Session, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from .config import get_config, DatabaseConfig
from .base import Base

# Set up logging
logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Database manager that handles engine creation, session management,
    and database lifecycle operations.
    """
    
    def __init__(self, config: DatabaseConfig = None):
        """
        Initialize database manager.
        
        Args:
            config (DatabaseConfig, optional): Database configuration.
                                             Defaults to global config.
        """
        self.config = config or get_config()
        self._engine: Optional[Engine] = None
        self._session_factory: Optional[sessionmaker] = None
        self._scoped_session: Optional[scoped_session] = None
        
        # Initialize on first access
        self._initialize()
    
    def _initialize(self):
        """Initialize engine and session factory."""
        try:
            # Create engine
            self._engine = self.config.create_engine()
            
            # Create session factory
            self._session_factory = sessionmaker(
                bind=self._engine,
                expire_on_commit=False,  # Keep objects usable after commit
                autoflush=True,          # Auto-flush before queries
                autocommit=False         # Manual transaction control
            )
            
            # Create scoped session for thread-safe operations
            self._scoped_session = scoped_session(self._session_factory)
            
            logger.info(f"Database initialized: {self.config.database_url}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    @property
    def engine(self) -> Engine:
        """Get SQLAlchemy engine."""
        if self._engine is None:
            self._initialize()
        return self._engine
    
    def get_session(self) -> Session:
        """
        Create a new database session.
        
        Returns:
            Session: New SQLAlchemy session
            
        Note:
            Caller is responsible for closing the session.
        """
        if self._session_factory is None:
            self._initialize()
        return self._session_factory()
    
    def get_scoped_session(self) -> scoped_session:
        """
        Get thread-local scoped session.
        
        Returns:
            scoped_session: Thread-safe scoped session
        """
        if self._scoped_session is None:
            self._initialize()
        return self._scoped_session
    
    def create_all_tables(self):
        """Create all database tables defined in models."""
        try:
            Base.metadata.create_all(self.engine)
            logger.info("All tables created successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise
    
    def drop_all_tables(self):
        """Drop all database tables. Use with caution!"""
        try:
            Base.metadata.drop_all(self.engine)
            logger.info("All tables dropped successfully")
        except Exception as e:
            logger.error(f"Failed to drop tables: {e}")
            raise
    
    def recreate_all_tables(self):
        """Drop and recreate all tables. Use with extreme caution!"""
        logger.warning("Recreating all tables - all data will be lost!")
        self.drop_all_tables()
        self.create_all_tables()
    
    def close(self):
        """Close database connections and clean up resources."""
        try:
            if self._scoped_session:
                self._scoped_session.remove()
            
            if self._engine:
                self._engine.dispose()
                
            logger.info("Database connections closed")
            
        except Exception as e:
            logger.error(f"Error closing database: {e}")
        finally:
            self._engine = None
            self._session_factory = None
            self._scoped_session = None
    
    def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            bool: True if database is accessible, False otherwise
        """
        try:
            with self.session_scope() as session:
                # Simple test query
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions with automatic transaction handling.
        
        Yields:
            Session: Database session
            
        Usage:
            with db_manager.session_scope() as session:
                # Your database operations here
                session.add(new_object)
                # Automatically commits on success, rolls back on exception
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
            logger.debug("Session committed successfully")
        except Exception as e:
            session.rollback()
            logger.error(f"Session rolled back due to error: {e}")
            raise
        finally:
            session.close()
    
    @contextmanager
    def transaction_scope(self, session: Session = None) -> Generator[Session, None, None]:
        """
        Context manager for explicit transaction control.
        
        Args:
            session (Session, optional): Existing session to use. Creates new if None.
            
        Yields:
            Session: Database session
            
        Usage:
            with db_manager.transaction_scope() as session:
                # Your operations here
                session.add(obj1)
                session.add(obj2)
                # Both committed together or both rolled back
        """
        if session is None:
            # Create new session and manage it
            with self.session_scope() as new_session:
                yield new_session
        else:
            # Use provided session but still handle transaction
            try:
                yield session
                if session.is_active:
                    session.commit()
            except Exception as e:
                if session.is_active:
                    session.rollback()
                raise
    
    def execute_raw_sql(self, sql: str, params: dict = None) -> Any:
        """
        Execute raw SQL statement.
        
        Args:
            sql (str): SQL statement to execute
            params (dict, optional): Parameters for the SQL statement
            
        Returns:
            Any: Query result
            
        Warning:
            Use with caution - prefer SQLAlchemy ORM when possible
        """
        with self.session_scope() as session:
            result = session.execute(text(sql), params or {})
            return result.fetchall()


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: DatabaseConfig = None) -> DatabaseManager:
    """
    Get or create global database manager instance.
    
    Args:
        config (DatabaseConfig, optional): Database configuration
        
    Returns:
        DatabaseManager: Database manager instance
    """
    global _db_manager
    
    if _db_manager is None or config is not None:
        _db_manager = DatabaseManager(config)
    
    return _db_manager


@contextmanager
def get_session(config: DatabaseConfig = None) -> Generator[Session, None, None]:
    """
    Context manager to get a database session.
    
    Args:
        config (DatabaseConfig, optional): Database configuration
        
    Yields:
        Session: Database session
        
    Usage:
        with get_session() as session:
            student = session.query(CanvasStudent).first()
    """
    db_manager = get_db_manager(config)
    with db_manager.session_scope() as session:
        yield session


def initialize_database(config: DatabaseConfig = None):
    """
    Initialize database and create all tables.
    
    Args:
        config (DatabaseConfig, optional): Database configuration
    """
    db_manager = get_db_manager(config)
    db_manager.create_all_tables()


def close_database():
    """Close global database connections."""
    global _db_manager
    if _db_manager:
        _db_manager.close()
        _db_manager = None


# Convenience functions for common operations
def create_tables(config: DatabaseConfig = None):
    """Create all database tables."""
    get_db_manager(config).create_all_tables()


def drop_tables(config: DatabaseConfig = None):
    """Drop all database tables."""
    get_db_manager(config).drop_all_tables()


def recreate_tables(config: DatabaseConfig = None):
    """Recreate all database tables."""
    get_db_manager(config).recreate_all_tables()


def health_check(config: DatabaseConfig = None) -> bool:
    """Check database health."""
    return get_db_manager(config).health_check()


# Standalone context managers for easy usage in tests and operations
@contextmanager
def session_scope(config: DatabaseConfig = None) -> Generator[Session, None, None]:
    """
    Standalone context manager for database sessions with automatic transaction handling.
    
    Args:
        config (DatabaseConfig, optional): Database configuration
        
    Yields:
        Session: Database session
        
    Usage:
        with session_scope() as session:
            # Your database operations here
            session.add(new_object)
            # Automatically commits on success, rolls back on exception
    """
    db_manager = get_db_manager(config)
    with db_manager.session_scope() as session:
        yield session


@contextmanager
def transaction_scope(session: Session = None, config: DatabaseConfig = None) -> Generator[Session, None, None]:
    """
    Standalone context manager for explicit transaction control.
    
    Args:
        session (Session, optional): Existing session to use. Creates new if None.
        config (DatabaseConfig, optional): Database configuration
        
    Yields:
        Session: Database session
        
    Usage:
        with transaction_scope() as session:
            # Your operations here
            session.add(obj1)
            session.add(obj2)
            # Both committed together or both rolled back
    """
    if session is None:
        # Create new session and manage it
        with session_scope(config) as new_session:
            yield new_session
    else:
        # Use provided session but still handle transaction
        try:
            yield session
            if session.is_active:
                session.commit()
        except Exception as e:
            if session.is_active:
                session.rollback()
            raise


# Session decorators for easy transaction management
def with_session(func):
    """
    Decorator that provides a database session to the decorated function.
    
    Usage:
        @with_session
        def my_function(session, other_args):
            # session is automatically provided
            return session.query(Model).all()
    """
    def wrapper(*args, **kwargs):
        with get_session() as session:
            return func(session, *args, **kwargs)
    return wrapper


def with_transaction(func):
    """
    Decorator that wraps function in a database transaction.
    
    Usage:
        @with_transaction  
        def my_function(session, data):
            # Any exception will rollback the transaction
            session.add(Model(data=data))
            return "success"
    """
    def wrapper(*args, **kwargs):
        with get_session() as session:
            try:
                result = func(session, *args, **kwargs)
                session.commit()
                return result
            except Exception as e:
                session.rollback()
                logger.error(f"Transaction failed: {e}")
                raise
    return wrapper


if __name__ == "__main__":
    # Test session management
    import sys
    
    print("Testing database session management...")
    
    try:
        # Test different environments
        for env in ['test', 'dev']:
            print(f"\n--- Testing {env} environment ---")
            
            config = DatabaseConfig(env)
            db_manager = DatabaseManager(config)
            
            # Test engine creation
            engine = db_manager.engine
            print(f"✓ Engine created: {engine}")
            
            # Test session creation
            session = db_manager.get_session()
            print(f"✓ Session created: {session}")
            session.close()
            
            # Test context manager
            with db_manager.session_scope() as session:
                print(f"✓ Context manager session: {session}")
            
            # Test health check
            is_healthy = db_manager.health_check()
            print(f"✓ Health check: {is_healthy}")
            
            # Cleanup
            db_manager.close()
            
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"✗ Test failed: {e}")
        sys.exit(1)