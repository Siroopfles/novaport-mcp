from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from pathlib import Path
import logging
from fastapi import Depends, HTTPException, status
from typing import Generator
import importlib.resources
import threading

from alembic.config import Config
from alembic import command

from ..core import config as core_config
from .models import Base

log = logging.getLogger(__name__)

_engines = {}
_session_locals = {}
_workspace_locks = {}

def run_migrations_for_workspace(engine, db_path: Path):
    """Voert Alembic migraties uit op een BESTAANDE engine verbinding."""
    log.info(f"Alembic migraties uitvoeren voor database: {db_path}...")
    
    package_root = importlib.resources.files('conport')
    script_location = str(package_root / 'db' / 'alembic')
    
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))
    
    # Voer de upgrade uit binnen een expliciete verbinding en transactie
    with engine.begin() as connection:
        alembic_cfg.attributes['connection'] = connection
        command.upgrade(alembic_cfg, "head")
    log.info("Alembic migraties succesvol gecommit.")

def get_session_local(workspace_id: str) -> sessionmaker:
    """Haalt of creëert een SessionLocal voor een specifieke workspace op een thread-safe manier."""
    if workspace_id not in _workspace_locks:
        _workspace_locks[workspace_id] = threading.Lock()
    
    workspace_lock = _workspace_locks[workspace_id]

    if workspace_id in _session_locals:
        return _session_locals[workspace_id]

    with workspace_lock:
        if workspace_id in _session_locals:
            return _session_locals[workspace_id]

        log.info(f"Initialisatie lock verkregen voor workspace: {workspace_id}")
        try:
            db_url = core_config.get_database_url_for_workspace(workspace_id)
            db_path = Path(db_url.replace("sqlite:///", ""))
            
            # Maak de engine aan. Deze zal de .db file aanraken/aanmaken.
            engine = create_engine(db_url, connect_args={"check_same_thread": False})
            
            # Geef deze engine direct door aan de migratiefunctie.
            run_migrations_for_workspace(engine, db_path)

            _engines[workspace_id] = engine
            _session_locals[workspace_id] = sessionmaker(autocommit=False, autoflush=False, bind=engine)
            log.info(f"Database sessie succesvol geconfigureerd en gecached voor workspace '{workspace_id}'")
        except Exception as e:
            log.error(f"Fout bij het initialiseren van de database voor workspace '{workspace_id}': {e}", exc_info=True)
            if workspace_id in _session_locals: del _session_locals[workspace_id]
            if workspace_id in _engines: del _engines[workspace_id]
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database initialization error: {e}")
            
    return _session_locals[workspace_id]

# Dependency voor de FastAPI HTTP API
def get_db(workspace_id_b64: str) -> Generator[Session, None, None]:
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