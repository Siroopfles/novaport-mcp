from fastapi import FastAPI

from .api import (
    batch,
    context,
    custom_data,
    decisions,
    history,
    io,
    links,
    meta,
    progress,
    search,
    system_patterns,
)
from .core.config import settings
from .services import history_service


def create_app() -> FastAPI:
    """Factory to create the FastAPI application instance."""
    # Initialize the history service to register event listeners
    _history_service_initialized = history_service

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="A robust, multi-workspace MCP server for NovaPort.",
        version="2.1.0",
    )

    # Health check at root
    @app.get("/", tags=["Root"])
    def read_root():
        """Provides a simple health check response."""
        return {"status": "ok", "project_name": settings.PROJECT_NAME}

    @app.get("/health", tags=["Health"])
    def health_check():
        """Provides a simple health check response for monitoring."""
        return {"status": "ok"}

    # Include all API routers
    # These routers now expect a workspace_id in their path
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
