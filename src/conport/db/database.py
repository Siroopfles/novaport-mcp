from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from pathlib import Path
import logging
from fastapi import Depends, HTTPException, status
from typing import Generator
import importlib.resources

from alembic.config import Config
from alembic import command

from ..core import config as core_config
from .models import Base  # Importeer Base van de nieuwe locatie

log = logging.getLogger(__name__)

_engines = {}
_session_locals = {}

def get_alembic_config(db_path: Path) -> Config:
    """Maakt een Alembic configuratie object in-memory."""
    # Gebruik importlib.resources.files om een Traversable object te krijgen
    package_root = importlib.resources.files('conport')
    script_location = str(package_root / 'db' / 'alembic')
    
    config = Config()
    config.set_main_option("script_location", script_location)
    config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path.resolve()}")
    return config

def run_migrations_for_workspace(engine, db_path: Path):
    """Voert Alembic migraties programmatisch uit voor een specifieke database."""
    log.info(f"Alembic migraties uitvoeren voor database: {db_path}...")
    alembic_cfg = get_alembic_config(db_path)
    with engine.connect() as connection:
        alembic_cfg.attributes['connection'] = connection
        command.upgrade(alembic_cfg, "head")
        log.info("Alembic migraties succesvol.")

def get_session_local(workspace_id: str) -> sessionmaker:
    """Haalt of creëert een SessionLocal voor een specifieke workspace."""
    if workspace_id not in _session_locals:
        try:
            db_url = core_config.get_database_url_for_workspace(workspace_id)
            db_path = Path(db_url.replace("sqlite:///", ""))

            engine = create_engine(db_url, connect_args={"check_same_thread": False})

            # Als de database niet bestaat, maak de tabellen en stempel met Alembic
            if not db_path.exists() or db_path.stat().st_size == 0:
                log.info(f"Database voor workspace '{workspace_id}' niet gevonden of leeg. Aanmaken en stempelen...")
                Base.metadata.create_all(engine)
                command.stamp(get_alembic_config(db_path), "head")
                log.info(f"Nieuwe database gestempeld met Alembic head.")
            else:
                log.info(f"Bestaande database gevonden voor '{workspace_id}'. Controleren op migraties...")
                # run_migrations_for_workspace(engine, db_path) # Optioneel: draai migraties bij elke start

            _engines[workspace_id] = engine
            _session_locals[workspace_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        except Exception as e:
            log.error(f"Fout bij het initialiseren van de database voor workspace '{workspace_id}': {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Database initialization error: {e}")
    return _session_locals[workspace_id]

# Dependency voor de FastAPI HTTP API
def get_db(workspace_id_b64: str) -> Generator[Session, None, None]:
    """FastAPI dependency om een DB sessie per request te beheren, gebaseerd op workspace_id."""
    db = None
    try:
        workspace_id = core_config.decode_workspace_id(workspace_id_b64)
        SessionLocal = get_session_local(workspace_id)
        db = SessionLocal()
        yield db
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        if db:
            db.close()

# Context Manager voor de MCP tools
@contextmanager
def get_db_session_for_workspace(workspace_id: str):
    """Context manager voor MCP tools."""
    db = None
    try:
        SessionLocal = get_session_local(workspace_id)
        db = SessionLocal()
        yield db
    except Exception as e:
        log.error(f"Fout tijdens het ophalen van de DB-sessie voor workspace '{workspace_id}': {e}", exc_info=True)
        raise
    finally:
        if db:
            db.close()