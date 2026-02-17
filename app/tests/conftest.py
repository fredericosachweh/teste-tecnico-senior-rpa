"""Pytest configuration and fixtures for app/tests."""

import os
import warnings

import pytest

warnings.filterwarnings("ignore", category=ResourceWarning)


@pytest.fixture(scope="session", autouse=True)
def override_database_url_for_tests(postgres_url):
    """Set DATABASE_URL globally for the entire test session."""
    original_url = os.environ.get("DATABASE_URL")
    print(f"Overriding DATABASE_URL to: {postgres_url}")
    os.environ["DATABASE_URL"] = postgres_url
    yield
    # Reset after session
    if original_url:
        os.environ["DATABASE_URL"] = original_url
    else:
        del os.environ["DATABASE_URL"]
    print(f"Reset DATABASE_URL to: {original_url}")


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
    Connection URL for the session-scoped Postgres
    container (SQLAlchemy/psycopg2).
    """
    return postgres_container.get_connection_url()


# --- Testcontainers fixtures (RabbitMQ) ---


@pytest.fixture(scope="session")
def rabbitmq_container():
    """Start a RabbitMQ container for the test session (requires Docker)."""
    try:
        from testcontainers.rabbitmq import RabbitMqContainer
    except ImportError:
        pytest.skip("testcontainers not installed - skipping")

    container = RabbitMqContainer(image="rabbitmq:3-management-alpine")
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="session")
def rabbitmq_url(rabbitmq_container):
    """AMQP URL for the session-scoped RabbitMQ container."""
    host = rabbitmq_container.get_container_host_ip()
    port = rabbitmq_container.get_exposed_port(rabbitmq_container.port)
    vhost = (rabbitmq_container.vhost or "/").strip("/") or ""
    url = (
        f"amqp://{rabbitmq_container.username}:{rabbitmq_container.password}"
        f"@{host}:{port}/{vhost}"
    )
    print(f"Using RabbitMQ test URL: {url}")
    return url


@pytest.fixture
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
