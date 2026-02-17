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
        pytest.skip("testcontainers not installed - skipping integration tests")

    # Use a recent image; alpine is fast and lightweight
    container = PostgresContainer(
        image="postgres:16-alpine",
        dbname="app1",
        username="app1",
        password="app1",
    )
    container.start()

    yield container

    # Cleanup
    container.stop()


@pytest.fixture(scope="session")
def postgres_url(postgres_container):
    """
    Get the REAL connection URL from the container (critical in CI/DinD).
    This returns something like postgresql+psycopg2://app1:app1@localhost:49173/app1
    """
    url = postgres_container.get_connection_url()
    # Optional: force psycopg2 driver if your env prefers it
    # url = url.replace("psycopg:", "psycopg2:")
    print(f"Using Postgres test URL: {url}")  # ← Helpful debug in CI logs
    return url


@pytest.fixture(scope="function")
def integration_engine(postgres_url):
    """SQLAlchemy engine bound to the Testcontainer Postgres."""
    from sqlalchemy import create_engine

    # Import models so Base.metadata knows about them
    import app.models.films  # noqa: F401
    import app.models.hockey_teams  # noqa: F401
    import app.models.jobs  # noqa: F401
    from app.database import Base

    engine = create_engine(
        postgres_url,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        # Helpful in CI: reduce timeouts if runner is slow
        connect_args={"connect_timeout": 10},
    )

    # Create tables once per function (safe & isolated)
    Base.metadata.create_all(engine)

    yield engine

    # Cleanup per test
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def integration_session(integration_engine):
    """SQLAlchemy session with transaction rollback for test isolation."""
    from sqlalchemy.orm import sessionmaker

    connection = integration_engine.connect()
    transaction = connection.begin()

    session_local = sessionmaker(
        bind=connection,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    session = session_local()

    yield session

    # Rollback + close (keeps DB clean between tests)
    session.close()
    transaction.rollback()
    connection.close()
