import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import config
from database.models import Base

# Database engine configuration with SQLite WAL mode and indices
engine = create_engine(
    config.DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 15} if config.DATABASE_URL.startswith("sqlite") else {},
    echo=False
)

SessionFactory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
db_session = scoped_session(SessionFactory)


def init_db():
    """Initializes database schema tables."""
    Base.metadata.create_all(bind=engine)


def reset_db():
    """Drops and re-creates all tables for clean schema updates."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db():
    """Context manager for safe transactional database sessions."""
    session = db_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def close_db(exception=None):
    """Closes scoped session upon application teardown."""
    db_session.remove()
