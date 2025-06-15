from sqlalchemy import create_engine, pool
from sqlalchemy.orm import sessionmaker, declarative_base, Session
from contextlib import contextmanager
from pathlib import Path
import logging
from fastapi import Depends, HTTPException, status
from typing import Generator
import importlib.resources

from alembic.config import Config
from alembic import command
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory

from ..core import config as core_config

log = logging.getLogger(__name__)

# Base voor SQLAlchemy modellen, dit moet geimporteerd worden door models.py
# Dus we importeren models NA de definitie van Base.
Base = declarative_base()
from ..db import models

def run_migrations_for_workspace(engine, db_path: Path):
    """Voert Alembic migraties programmatisch uit voor een specifieke database."""
    log.info(f"Alembic migraties uitvoeren voor database: {db_path}...")
    
    # Bepaal het pad naar de alembic script directory
    package_root = Path(importlib.resources.files('conport'))
    script_location = str(package_root / 'db' / 'alembic')
    
    # Maak een Alembic configuratie object in-memory
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", script_location)
    
    # Draai de migraties in de context van de engine van de workspace
    with engine.connect() as connection:
        alembic_cfg.attributes['connection'] = connection
        command.upgrade(alembic_cfg, "head")

def get_session_local(workspace_id: str) -> sessionmaker:
    """Haalt of creëert een SessionLocal voor een specifieke workspace."""
    if workspace_id not in _session_locals:
        try:
            db_url = core_config.get_database_url_for_workspace(workspace_id)
            db_path = Path(db_url.replace("sqlite:///", ""))

            # Maak een nieuwe engine aan voor deze workspace
            engine = create_engine(
                db_url,
                connect_args={"check_same_thread": False},
                poolclass=pool.StaticPool # Geschikt voor SQLite per-thread
            )

            # Voer migraties uit als de database nog niet bestaat.
            if not db_path.exists() or db_path.stat().st_size == 0:
                log.info(f"Database voor workspace '{workspace_id}' niet gevonden of leeg. Aanmaken en migreren...")
                # We moeten de tabellen van de Base eerst aanmaken
                Base.metadata.create_all(engine)
                # Daarna stempelen we de DB met de laatste Alembic revisie
                alembic_cfg = Config()
                alembic_cfg.set_main_option("script_location", str(Path(importlib.resources.files('conport')) / 'db' / 'alembic'))
                command.stamp(alembic_cfg, "head")
                log.info(f"Nieuwe database gestempeld met Alembic head.")
            
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