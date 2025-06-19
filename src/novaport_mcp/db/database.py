import asyncio
import importlib.resources
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator

from alembic import command
from alembic.config import Config
from fastapi import HTTPException, status
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from ..core import config as core_config

log = logging.getLogger(__name__)

_engines: dict[str, Any] = {}
_session_locals: dict[str, Any] = {}
_workspace_locks: dict[str, Any] = {}


def run_migrations_for_workspace(engine, db_path: Path):
    """This function is blocking and will be executed in a thread."""
    log.info(f"Running Alembic migrations for database: {db_path}...")

    package_root = importlib.resources.files("conport")
    script_location = str(package_root / "db" / "alembic")

    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", script_location)
    alembic_cfg.set_main_option("sqlalchemy.url", str(engine.url))

    with engine.begin() as connection:
        alembic_cfg.attributes["connection"] = connection
        command.upgrade(alembic_cfg, "head")
    log.info("Alembic migrations successfully committed.")


async def get_session_local(workspace_id: str) -> sessionmaker:
    """Retrieves or creates a SessionLocal for a specific workspace in a thread-safe and async-friendly manner."""
    if workspace_id not in _workspace_locks:
        _workspace_locks[workspace_id] = asyncio.Lock()

    workspace_lock = _workspace_locks[workspace_id]

    if workspace_id in _session_locals:
        return _session_locals[workspace_id]

    async with workspace_lock:
        # Double-check after acquiring the lock
        if workspace_id in _session_locals:
            return _session_locals[workspace_id]

        log.info(f"Initialization lock acquired for workspace: {workspace_id}")
        try:
            db_url = core_config.get_database_url_for_workspace(workspace_id)
            db_path = Path(db_url.replace("sqlite:///", ""))

            # Engine creation is fast, can remain in the main thread.
            engine = create_engine(db_url, connect_args={"check_same_thread": False})

            # RUN THE LONG MIGRATION IN A SEPARATE THREAD
            # This prevents blocking the server event loop.
            await asyncio.to_thread(run_migrations_for_workspace, engine, db_path)

            _engines[workspace_id] = engine
            _session_locals[workspace_id] = sessionmaker(
                autocommit=False, autoflush=False, bind=engine
            )
            log.info(
                f"Database session successfully configured and cached for '{workspace_id}'"
            )
        except Exception as e:
            log.error(
                f"Error initializing database for '{workspace_id}': {e}", exc_info=True
            )
            if workspace_id in _session_locals:
                del _session_locals[workspace_id]
            if workspace_id in _engines:
                del _engines[workspace_id]
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database initialization error: {e}",
            )

    return _session_locals[workspace_id]


# Dependency for the FastAPI HTTP API
async def get_db(workspace_id_b64: str) -> AsyncGenerator[Session, None]:
    db = None
    try:
        workspace_id = core_config.decode_workspace_id(workspace_id_b64)
        session_local = await get_session_local(workspace_id)
        db = session_local()
        yield db
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    finally:
        if db:
            db.close()


# Context Manager for the MCP tools - NOW ASYNCHRONOUS
@asynccontextmanager
async def get_db_session_for_workspace(
    workspace_id: str,
) -> AsyncGenerator[Session, None]:
    db = None
    try:
        session_local = await get_session_local(workspace_id)
        db = session_local()
        yield db
    except Exception as e:
        log.error(
            f"Error while retrieving DB session for workspace '{workspace_id}': {e}",
            exc_info=True,
        )
        # Rollback is not needed if autocommit is False and we don't commit on error
        raise
    finally:
        if db:
            db.close()
