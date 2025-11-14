"""
Database connection management for Poolula Platform

Handles SQLite/PostgreSQL connections with SQLModel

Design:
- Development: SQLite (file-based, simple)
- Production: PostgreSQL (when scaling needed)
- Connection pooling for performance
- Automatic table creation in development

Author: Poolula Platform
Date: 2025-11-13
"""

import os
from pathlib import Path
from typing import Generator, Optional

from sqlmodel import SQLModel, Session, create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import StaticPool

from core.logging_config import get_logger

logger = get_logger(__name__)


# Global engine instance (initialized on first use)
_engine: Optional[Engine] = None


def get_database_url() -> str:
    """
    Get database URL from environment or use default SQLite

    Reads DATABASE_URL environment variable, falls back to SQLite

    Returns:
        Database connection string

    Examples:
        - SQLite: "sqlite:///./poolula.db"
        - PostgreSQL: "postgresql://user:pass@localhost/poolula"
    """
    env_url = os.getenv("DATABASE_URL")

    if env_url:
        # Handle Heroku/Railway postgres:// → postgresql://
        if env_url.startswith("postgres://"):
            env_url = env_url.replace("postgres://", "postgresql://", 1)
        return env_url

    # Default: SQLite in current directory
    db_path = Path("poolula.db")
    return f"sqlite:///{db_path}"


def get_engine(echo: bool = None) -> Engine:
    """
    Get or create database engine (singleton pattern)

    Args:
        echo: If True, log all SQL queries (useful for debugging)
              If None, uses ENV variable DEBUG (default False)

    Returns:
        SQLAlchemy Engine instance

    Example:
        >>> engine = get_engine()
        >>> with Session(engine) as session:
        ...     session.add(property_obj)
        ...     session.commit()
    """
    global _engine

    if _engine is not None:
        return _engine

    # Determine echo setting
    if echo is None:
        echo = os.getenv("DEBUG", "false").lower() == "true"

    database_url = get_database_url()

    # Configure engine based on database type
    if database_url.startswith("sqlite"):
        # SQLite-specific configuration
        logger.info(f"Initializing SQLite database: {database_url}")

        _engine = create_engine(
            database_url,
            echo=echo,
            connect_args={"check_same_thread": False},  # Allow FastAPI async
            poolclass=StaticPool,  # Single connection for SQLite
        )

    else:
        # PostgreSQL configuration
        logger.info(f"Initializing PostgreSQL database: {database_url.split('@')[1] if '@' in database_url else 'localhost'}")

        _engine = create_engine(
            database_url,
            echo=echo,
            pool_size=5,  # Connection pool
            max_overflow=10,  # Max additional connections
            pool_pre_ping=True,  # Verify connections before use
        )

    return _engine


def create_tables() -> None:
    """
    Create all database tables

    Should be called:
    - On application startup in development
    - After running migrations in production

    Note: In production, use Alembic migrations instead

    Example:
        >>> from core.database.connection import create_tables
        >>> create_tables()  # Creates all tables
    """
    engine = get_engine()

    logger.info("Creating database tables...")

    # Import all models to register them with SQLModel
    from .models import Property, Transaction, Document, Obligation, AuditLog

    # Create all tables
    SQLModel.metadata.create_all(engine)

    logger.info("✅ Database tables created successfully")


def drop_tables() -> None:
    """
    Drop all database tables

    ⚠️ WARNING: Destructive operation, use with caution!

    Only use in:
    - Development/testing
    - When you want to reset the database completely

    Example:
        >>> from core.database.connection import drop_tables
        >>> drop_tables()  # Drops all tables
    """
    engine = get_engine()

    logger.warning("⚠️  Dropping all database tables...")

    # Import all models
    from .models import Property, Transaction, Document, Obligation, AuditLog

    # Drop all tables
    SQLModel.metadata.drop_all(engine)

    logger.warning("Database tables dropped")


def get_session() -> Generator[Session, None, None]:
    """
    Get database session (FastAPI dependency)

    Use this as a FastAPI dependency to get a session per request

    Yields:
        SQLModel Session

    Example (in FastAPI):
        >>> from fastapi import Depends
        >>> from core.database.connection import get_session
        >>>
        >>> @app.get("/properties")
        >>> def get_properties(session: Session = Depends(get_session)):
        ...     properties = session.exec(select(Property)).all()
        ...     return properties
    """
    engine = get_engine()

    with Session(engine) as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Session error: {e}", exc_info=True)
            session.rollback()
            raise
        finally:
            session.close()


def init_database() -> None:
    """
    Initialize database for development

    Creates tables and optionally seeds with sample data

    Call this on application startup in development mode

    Example:
        >>> from core.database.connection import init_database
        >>> init_database()
    """
    engine = get_engine()

    # Create tables
    create_tables()

    # Check if database is empty
    from sqlmodel import select
    from .models import Property

    with Session(engine) as session:
        properties = session.exec(select(Property)).first()

        if properties is None:
            logger.info("Database is empty - ready for data import")
        else:
            logger.info(f"Database initialized - found existing data")


# Connection health check
def check_connection() -> bool:
    """
    Check if database connection is healthy

    Returns:
        True if connection works, False otherwise

    Example:
        >>> from core.database.connection import check_connection
        >>> if check_connection():
        ...     print("Database is healthy")
    """
    try:
        engine = get_engine()

        with Session(engine) as session:
            # Simple query to test connection
            session.exec(text("SELECT 1"))

        logger.info("✅ Database connection healthy")
        return True

    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False


# Cleanup function
def close_engine() -> None:
    """
    Close database engine and connection pool

    Call this on application shutdown

    Example:
        >>> from core.database.connection import close_engine
        >>>
        >>> @app.on_event("shutdown")
        >>> def shutdown():
        ...     close_engine()
    """
    global _engine

    if _engine is not None:
        logger.info("Closing database connections...")
        _engine.dispose()
        _engine = None
        logger.info("✅ Database connections closed")
