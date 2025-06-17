from fastapi import FastAPI
from .core.config import settings
from .services import history_service
from .api import (
    decisions, context, progress, system_patterns, 
    custom_data, search, links, batch, meta, io, history
)
import base64

def create_app() -> FastAPI:
    """Factory to create the FastAPI application instance."""
    # Initialiseer de history service om event listeners te registreren
    _history_service_initialized = history_service

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="A robust, multi-workspace MCP server for NovaPort.",
        version="2.1.0"
    )

    # Health check at root
    @app.get("/", tags=["Root"])
    def read_root():
        """Provides a simple health check response."""
        return {"status": "ok", "project_name": settings.PROJECT_NAME}

    # Include all API routers
    # Deze routers verwachten nu een workspace_id in hun pad
    app.include_router(context.router)
    app.include_router(decisions.router)
    app.include_router(progress.router)
    app.include_router(system_patterns.router)
    app.include_router(custom_data.router)
    app.include_router(search.router)
    app.include_router(links.router)
    app.include_router(batch.router)
    app.include_router(meta.router)
    app.include_router(io.router)
    app.include_router(history.router)
        
    return app