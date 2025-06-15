from fastapi import FastAPI
from .core.config import settings
from .services import history_service
from .api import (
    decisions, context, progress, system_patterns, 
    custom_data, search, links, batch, meta, io, history
)

def create_app() -> FastAPI:
    """Factory to create the FastAPI application instance."""
    # This line ensures the event listeners in history_service are registered
    _ = history_service

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="Context Portal v2: A robust, database-backed server.",
        version="2.0.0"
    )

    # Include all the API routers
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

    @app.get("/", tags=["Root"])
    def read_root():
        """Provides a simple health check response."""
        return {"status": "ok", "project_name": settings.PROJECT_NAME}
        
    return app