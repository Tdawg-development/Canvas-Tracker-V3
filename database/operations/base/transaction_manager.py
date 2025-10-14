"""
Transaction Management for Database Operations.

Provides transaction coordination, rollback support, and nested transaction
handling for database operations.

This is a basic implementation for Layer 1 operations support.
"""

from typing import Optional, Any
from contextlib import contextmanager
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from .exceptions import TransactionError


class TransactionManager:
    """
    Simple transaction manager for database operations.
    
    Provides transaction coordination and rollback capabilities.
    This is a basic implementation to support Layer 1 operations.
    """
    
    def __init__(self, session: Session):
        """
        Initialize transaction manager.
        
        Args:
            session: SQLAlchemy session for transaction management
        """
        self.session = session
        self._transaction_stack = []
    
    @contextmanager
    def begin_nested_transaction(self):
        """
        Begin a nested transaction with automatic rollback on error.
        
        Yields:
            The nested transaction context
            
        Raises:
            TransactionError: If transaction operations fail
        """
        nested_transaction = None
        try:
            # Begin a nested transaction (SAVEPOINT)
            nested_transaction = self.session.begin(nested=True)
            self._transaction_stack.append(nested_transaction)
            
            yield nested_transaction
            
            # Commit if successful
            nested_transaction.commit()
            
        except Exception as e:
            # Rollback on any error
            if nested_transaction and nested_transaction.is_active:
                nested_transaction.rollback()
            raise TransactionError(f"Nested transaction failed: {e}") from e
        finally:
            # Clean up transaction stack
            if nested_transaction and self._transaction_stack and self._transaction_stack[-1] == nested_transaction:
                self._transaction_stack.pop()
    
    def rollback_nested_transaction(self):
        """
        Rollback the current nested transaction.
        
        Raises:
            TransactionError: If rollback fails
        """
        try:
            if self._transaction_stack:
                transaction = self._transaction_stack.pop()
                if transaction.is_active:
                    transaction.rollback()
            else:
                # Fallback to session rollback
                self.session.rollback()
        except SQLAlchemyError as e:
            raise TransactionError(f"Transaction rollback failed: {e}") from e
    
    def commit_transaction(self):
        """
        Commit the current transaction.
        
        Raises:
            TransactionError: If commit fails
        """
        try:
            self.session.commit()
        except SQLAlchemyError as e:
            self.session.rollback()
            raise TransactionError(f"Transaction commit failed: {e}") from e
    
    @property
    def has_active_transaction(self) -> bool:
        """Check if there's an active transaction."""
        return len(self._transaction_stack) > 0 or self.session.in_transaction()