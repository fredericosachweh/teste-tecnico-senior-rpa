from urllib.parse import urlparse, urlunparse

from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

# Default DB name to create if not exist (from DATABASE_URL)
DATABASE_NAME = "rpa"


def ensure_database_exists() -> None:
    """Create database DATABASE_NAME if missing (connects to 'postgres')."""
    parsed = urlparse(DATABASE_URL)
    db_name = parsed.path.lstrip("/") or DATABASE_NAME
    # Connect to default 'postgres' database to run CREATE DATABASE
    base_url = urlunparse(
        (
            parsed.scheme,
            parsed.netloc,
            "/postgres",
            parsed.params,
            parsed.query,
            parsed.fragment,
        )
    )
    engine = create_engine(base_url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": db_name},
        ).scalar()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
    engine.dispose()


engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)

Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_session():
    """Yield a DB session (context manager). Use with: with get_session() as session:"""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
