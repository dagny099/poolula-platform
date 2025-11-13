"""
Pytest configuration and fixtures for Poolula Platform tests

Provides test database, session, and FastAPI test client
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlalchemy.pool import StaticPool

from apps.api.main import app
from core.database.connection import get_session


@pytest.fixture(name="engine_test")
def engine_test_fixture():
    """
    Create in-memory SQLite engine for testing

    Uses :memory: database that is destroyed after each test
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    SQLModel.metadata.create_all(engine)

    yield engine

    # Drop all tables
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="session_test")
def session_test_fixture(engine_test):
    """
    Create database session for testing

    Yields a fresh session for each test
    """
    with Session(engine_test) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session_test: Session):
    """
    Create FastAPI test client with dependency override

    Overrides the get_session dependency to use the test database
    """

    def get_session_override():
        return session_test

    app.dependency_overrides[get_session] = get_session_override

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()
