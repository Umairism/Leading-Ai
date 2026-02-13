"""
Database connection and session management.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import StaticPool
from contextlib import contextmanager
import logging

from config.settings import Config
from database.models import Base

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager."""
    
    _engine = None
    _session_factory = None
    
    @classmethod
    def initialize(cls):
        """Initialize database engine and create tables."""
        if cls._engine is None:
            # Create engine with appropriate settings
            if Config.DATABASE_URL.startswith('sqlite'):
                cls._engine = create_engine(
                    Config.DATABASE_URL,
                    connect_args={'check_same_thread': False},
                    poolclass=StaticPool,
                    echo=False  # Set to True for SQL debugging
                )
            else:
                cls._engine = create_engine(
                    Config.DATABASE_URL,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20
                )
            
            # Create all tables
            Base.metadata.create_all(cls._engine)
            logger.info("Database initialized successfully")
            
            # Create session factory
            cls._session_factory = scoped_session(
                sessionmaker(bind=cls._engine, expire_on_commit=False)
            )
    
    @classmethod
    def get_session(cls):
        """Get a new database session."""
        if cls._session_factory is None:
            cls.initialize()
        return cls._session_factory()
    
    @classmethod
    @contextmanager
    def session_scope(cls):
        """Provide a transactional scope for database operations."""
        session = cls.get_session()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    @classmethod
    def close(cls):
        """Close database connections."""
        if cls._session_factory:
            cls._session_factory.remove()
        if cls._engine:
            cls._engine.dispose()
            logger.info("Database connections closed")
