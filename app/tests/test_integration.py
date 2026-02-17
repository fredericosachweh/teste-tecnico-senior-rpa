"""
Integration tests using Testcontainers (PostgreSQL).

Requires Docker. Run with: pytest app/tests/test_integration.py -v
Skip if no Docker: pytest -m "not integration" ...
"""

import pytest

pytestmark = pytest.mark.integration


def test_postgres_container_accepts_connections(integration_session):
    """Test that the Postgres container is up and we can run a query."""
    from sqlalchemy import text

    result = integration_session.execute(text("SELECT 1"))
    assert result.scalar() == 1


def test_create_tables_and_insert_job(integration_session):
    """Test that app models work against the containerized Postgres."""
    from app.models.jobs import Job, JobStatus, JobType

    job = Job(
        job_id="integration-test-job-1",
        job_type=JobType.HOCKEY,
        status=JobStatus.PENDING,
    )
    integration_session.add(job)
    integration_session.commit()
    integration_session.refresh(job)

    assert job.id is not None
    assert job.job_id == "integration-test-job-1"
    assert job.job_type == JobType.HOCKEY
    assert job.status == JobStatus.PENDING

    found = (
        integration_session.query(Job)
        .filter(Job.job_id == "integration-test-job-1")
        .first()
    )
    assert found is not None
    assert found.id == job.id


def test_api_health_over_container_db(integration_engine):
    """Test FastAPI app using the Testcontainer DB via dependency override."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.database import get_session
    from app.main import app

    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=integration_engine
    )

    def override_get_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json() == {"status": "healthy"}

        r = client.get("/")
        assert r.status_code == 200
        assert "RPA Crawler API" in r.json()["message"]

        r = client.get("/jobs")
        assert r.status_code == 200
        assert isinstance(r.json(), list)
    finally:
        app.dependency_overrides.pop(get_session, None)


def test_api_create_job_over_container_db(integration_engine):
    """Test POST /crawl/hockey creates a job in the container DB."""
    from fastapi.testclient import TestClient
    from sqlalchemy.orm import sessionmaker

    from app.database import Base, get_session
    from app.main import app

    Base.metadata.create_all(integration_engine)
    session_factory = sessionmaker(
        autocommit=False, autoflush=False, bind=integration_engine
    )

    def override_get_session():
        session = session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    app.dependency_overrides[get_session] = override_get_session
    try:
        client = TestClient(app)
        r = client.post("/crawl/hockey")
        assert r.status_code == 200
        data = r.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["job_type"] == "hockey"

        r = client.get("/jobs")
        assert r.status_code == 200
        jobs = r.json()
        assert len(jobs) >= 1
        assert jobs[0]["job_id"] == data["job_id"]
    finally:
        app.dependency_overrides.pop(get_session, None)
