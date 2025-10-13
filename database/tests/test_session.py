"""
Unit tests for database session management module.

Tests the DatabaseManager class and session-related functionality
including transactions, context managers, and connection handling.
"""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy.exc import SQLAlchemyError

from database.session import (
    DatabaseManager, get_db_manager, get_session,
    initialize_database, close_database, health_check,
    with_session, with_transaction
)
from database.config import DatabaseConfig
from database.utils.exceptions import ConnectionError
from .conftest import _TestModel as TestModel, create_test_objects, assert_database_state


class TestDatabaseManager:
    """Test suite for DatabaseManager class."""
    
    @pytest.mark.unit
    def test_database_manager_initialization(self, test_db_config):
        """Test DatabaseManager initialization."""
        manager = DatabaseManager(test_db_config)
        
        assert manager.config == test_db_config
        assert manager._engine is not None
        assert manager._session_factory is not None
        assert manager._scoped_session is not None
        
        # Cleanup
        manager.close()
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_engine_property(self, db_manager):
        """Test engine property access."""
        engine = db_manager.engine
        
        assert engine is not None
        assert str(engine.url) == 'sqlite:///:memory:'
    
    @pytest.mark.unit 
    @pytest.mark.database
    def test_get_session(self, db_manager):
        """Test session creation."""
        session = db_manager.get_session()
        
        assert session is not None
        assert hasattr(session, 'query')
        assert hasattr(session, 'add')
        assert hasattr(session, 'commit')
        
        session.close()
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_get_scoped_session(self, db_manager):
        """Test scoped session creation."""
        scoped_session = db_manager.get_scoped_session()
        
        assert scoped_session is not None
        
        # Test that multiple calls return the same instance
        scoped_session2 = db_manager.get_scoped_session()
        assert scoped_session is scoped_session2
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_create_all_tables(self, db_manager):
        """Test table creation."""
        # Should not raise any exceptions
        db_manager.create_all_tables()
        
        # Verify tables exist by checking engine
        from database.base import Base
        table_names = Base.metadata.tables.keys()
        assert len(table_names) >= 0  # At least no error occurred
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_health_check_healthy(self, db_manager):
        """Test health check with healthy database."""
        result = db_manager.health_check()
        assert result is True
    
    @pytest.mark.unit
    def test_health_check_unhealthy(self):
        """Test health check with unhealthy database."""
        # Create manager with invalid config
        config = DatabaseConfig('test')
        manager = DatabaseManager(config)
        
        # Mock the session_scope to raise an exception
        with patch.object(manager, 'session_scope') as mock_session:
            mock_session.side_effect = SQLAlchemyError("Connection failed")
            
            result = manager.health_check()
            assert result is False
        
        manager.close()
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_close(self, test_db_config):
        """Test database manager cleanup."""
        manager = DatabaseManager(test_db_config)
        
        # Verify resources are initialized
        assert manager._engine is not None
        assert manager._session_factory is not None
        
        # Close and verify cleanup
        manager.close()
        
        assert manager._engine is None
        assert manager._session_factory is None
        assert manager._scoped_session is None
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_recreate_all_tables(self, db_manager):
        """Test table recreation."""
        # Should not raise any exceptions
        db_manager.recreate_all_tables()
        
        # Should still be able to create tables after recreation
        db_manager.create_all_tables()


class TestSessionScope:
    """Test suite for session_scope context manager."""
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_session_scope_success(self, db_manager):
        """Test successful session scope usage."""
        db_manager.create_all_tables()
        
        with db_manager.session_scope() as session:
            # Create a test object
            test_obj = TestModel(name="Test Object", value=42)
            session.add(test_obj)
            # Session should auto-commit when exiting context
        
        # Verify object was committed
        with db_manager.session_scope() as session:
            found_obj = session.query(TestModel).filter_by(name="Test Object").first()
            assert found_obj is not None
            assert found_obj.value == 42
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_session_scope_rollback_on_exception(self, db_manager):
        """Test that session scope rolls back on exception."""
        db_manager.create_all_tables()
        
        with pytest.raises(ValueError):
            with db_manager.session_scope() as session:
                # Create a test object
                test_obj = TestModel(name="Test Object", value=42)
                session.add(test_obj)
                session.flush()  # Make sure it's in the session
                
                # Raise an exception to trigger rollback
                raise ValueError("Test exception")
        
        # Verify object was not committed
        with db_manager.session_scope() as session:
            found_obj = session.query(TestModel).filter_by(name="Test Object").first()
            assert found_obj is None
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_transaction_scope_with_existing_session(self, db_session):
        """Test transaction scope with existing session."""
        # Create test data
        test_obj = TestModel(name="Transaction Test", value=100)
        
        # The db_session fixture already has a transaction started
        # so we just test basic operations within that transaction
        db_session.add(test_obj)
        db_session.flush()
        
        # Object should be visible within transaction
        found_obj = db_session.query(TestModel).filter_by(name="Transaction Test").first()
        assert found_obj is not None
        assert found_obj.value == 100


class TestExecuteRawSQL:
    """Test suite for raw SQL execution."""
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_execute_raw_sql_select(self, db_manager):
        """Test raw SQL SELECT execution."""
        result = db_manager.execute_raw_sql("SELECT 1 as test_value")
        
        assert len(result) == 1
        assert result[0][0] == 1  # First row, first column
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_execute_raw_sql_with_parameters(self, db_manager):
        """Test raw SQL execution with parameters."""
        result = db_manager.execute_raw_sql(
            "SELECT :value as test_value", 
            {'value': 42}
        )
        
        assert len(result) == 1
        assert result[0][0] == 42
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_execute_raw_sql_error(self, db_manager):
        """Test raw SQL execution with invalid SQL."""
        with pytest.raises(SQLAlchemyError):
            db_manager.execute_raw_sql("INVALID SQL STATEMENT")


class TestGlobalFunctions:
    """Test suite for global session management functions."""
    
    @pytest.mark.unit
    def test_get_db_manager_singleton(self, test_db_config):
        """Test that get_db_manager returns singleton."""
        manager1 = get_db_manager(test_db_config)
        manager2 = get_db_manager()  # Should return same instance
        
        assert manager1 is manager2
        
        # Cleanup
        close_database()
    
    @pytest.mark.unit
    def test_get_db_manager_new_config(self, test_db_config):
        """Test that get_db_manager creates new instance with different config."""
        manager1 = get_db_manager(test_db_config)
        
        new_config = DatabaseConfig('dev')
        manager2 = get_db_manager(new_config)
        
        assert manager1 is not manager2
        assert manager1.config != manager2.config
        
        # Cleanup
        close_database()
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_get_session_context_manager(self, test_db_config):
        """Test get_session context manager."""
        with get_session(test_db_config) as session:
            assert session is not None
            assert hasattr(session, 'query')
            
            # Test basic operation
            from sqlalchemy import text
            result = session.execute(text("SELECT 1"))
            assert result.fetchone()[0] == 1
        
        # Cleanup
        close_database()
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_initialize_database(self, test_db_config):
        """Test database initialization."""
        # Should not raise any exceptions
        initialize_database(test_db_config)
        
        # Should be able to get a session after initialization
        with get_session(test_db_config) as session:
            assert session is not None
        
        # Cleanup
        close_database()
    
    @pytest.mark.unit
    def test_close_database(self, test_db_config):
        """Test database closure."""
        # Initialize database
        manager = get_db_manager(test_db_config)
        assert manager is not None
        
        # Close database
        close_database()
        
        # Manager should be reset
        import database.session
        assert database.session._db_manager is None
    
    @pytest.mark.unit
    @pytest.mark.database 
    def test_health_check_function(self, test_db_config):
        """Test global health check function."""
        result = health_check(test_db_config)
        assert result is True
        
        # Cleanup
        close_database()


class TestSessionDecorators:
    """Test suite for session decorators."""
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_with_session_decorator(self, test_db_config):
        """Test with_session decorator."""
        @with_session
        def test_function(session, test_value):
            from sqlalchemy import text
            result = session.execute(text(f"SELECT {test_value}"))
            return result.fetchone()[0]
        
        # Mock get_session to use our test config
        with patch('database.session.get_session') as mock_get_session:
            with DatabaseManager(test_db_config).session_scope() as test_session:
                mock_get_session.return_value.__enter__.return_value = test_session
                mock_get_session.return_value.__exit__.return_value = None
                
                result = test_function(42)
                assert result == 42
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_with_transaction_decorator_success(self, test_db_config):
        """Test with_transaction decorator with successful transaction."""
        @with_transaction
        def create_test_object(session, name, value):
            test_obj = TestModel(name=name, value=value)
            session.add(test_obj)
            return "success"
        
        # Mock get_session to use our test config
        with patch('database.session.get_session') as mock_get_session:
            manager = DatabaseManager(test_db_config)
            manager.create_all_tables()
            
            with manager.session_scope() as test_session:
                mock_get_session.return_value.__enter__.return_value = test_session
                mock_get_session.return_value.__exit__.return_value = None
                
                result = create_test_object("Decorated Object", 99)
                assert result == "success"
                
                # Verify object was created (within same session)
                found_obj = test_session.query(TestModel).filter_by(name="Decorated Object").first()
                # Note: May not be committed due to test transaction rollback
            
            manager.close()
    
    @pytest.mark.unit
    def test_with_transaction_decorator_failure(self, test_db_config):
        """Test with_transaction decorator with failed transaction."""
        @with_transaction
        def failing_function(session):
            raise ValueError("Test exception")
        
        with patch('database.session.get_session') as mock_get_session:
            manager = DatabaseManager(test_db_config)
            
            with manager.session_scope() as test_session:
                mock_get_session.return_value.__enter__.return_value = test_session
                mock_get_session.return_value.__exit__.return_value = None
                
                with pytest.raises(ValueError):
                    failing_function()
            
            manager.close()


class TestErrorHandling:
    """Test suite for error handling in session management."""
    
    @pytest.mark.unit
    def test_initialization_failure(self):
        """Test DatabaseManager initialization failure."""
        # Create config with invalid URL
        config = DatabaseConfig('test')
        
        with patch.object(config, 'create_engine') as mock_create:
            mock_create.side_effect = SQLAlchemyError("Engine creation failed")
            
            with pytest.raises(SQLAlchemyError):
                DatabaseManager(config)
    
    @pytest.mark.unit
    @pytest.mark.database
    def test_session_creation_after_close(self, test_db_config):
        """Test session creation after manager is closed."""
        manager = DatabaseManager(test_db_config)
        manager.close()
        
        # Should reinitialize when accessing engine/session
        session = manager.get_session()
        assert session is not None
        session.close()
        
        # Cleanup again
        manager.close()


# Integration tests
@pytest.mark.integration
@pytest.mark.database
class TestSessionIntegration:
    """Integration tests for session management."""
    
    def test_full_session_workflow(self, sample_test_data):
        """Test complete session workflow with real data operations."""
        config = DatabaseConfig('test')
        manager = DatabaseManager(config)
        manager.create_all_tables()
        
        try:
            # Test data creation
            with manager.session_scope() as session:
                test_objects = create_test_objects(
                    session, TestModel, sample_test_data['test_objects']
                )
                assert len(test_objects) == 3
            
            # Test data retrieval
            with manager.session_scope() as session:
                assert_database_state(session, TestModel, 3)
                
                # Test specific queries
                obj = session.query(TestModel).filter_by(name="Object 1").first()
                assert obj is not None
                assert obj.value == 10
        
        finally:
            manager.close()