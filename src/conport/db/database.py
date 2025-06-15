from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from ..core.config import settings

# Arguments for create_engine, specific for SQLite to allow multi-threading in FastAPI
engine_args = {}
if "sqlite" in settings.DATABASE_URL:
    engine_args["connect_args"] = {"check_same_thread": False}

engine = create_engine(settings.DATABASE_URL, **engine_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """FastAPI dependency to manage DB sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()