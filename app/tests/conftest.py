"""Pytest configuration and fixtures for app/tests."""

import warnings

import pytest

warnings.filterwarnings("ignore", category=ResourceWarning)


def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration (uses Testcontainers, needs Docker)",
    )


# --- Testcontainers fixtures (PostgreSQL) ---


@pytest.fixture(scope="session")
def postgres_container():
    """Start a PostgreSQL container for the test session (requires Docker)."""
    try:
        from testcontainers.postgres import PostgresContainer
    except ImportError:
        pytest.skip("testcontainers not installed")
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """
    Connection URL for the session-scoped Postgres
    container (SQLAlchemy/psycopg2).
    """
    return postgres_container.get_connection_url()


@pytest.fixture
def integration_engine(postgres_url):
    """SQLAlchemy engine bound to the Testcontainer Postgres."""
    from sqlalchemy import create_engine

    # Ensure all models are registered with Base before create_all
    import app.models.films  # noqa: F401
    import app.models.hockey_teams  # noqa: F401
    import app.models.jobs  # noqa: F401
    from app.database import Base

    engine = create_engine(postgres_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture
def integration_session(integration_engine):
    """SQLAlchemy session bound to the Testcontainer Postgres."""
    from sqlalchemy.orm import sessionmaker

    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=integration_engine
    )
    with session_factory() as session:
        yield session
        session.rollback()
        session.close()
