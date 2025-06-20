from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import decode_workspace_id
from ..db.database import get_db
from ..schemas import progress as progress_schema
from ..services import progress_service

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/progress", tags=["Progress"])


@router.post(
    "/",
    response_model=progress_schema.ProgressEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_progress_entry(
    workspace_id_b64: str,
    entry: progress_schema.ProgressEntryCreate,
    db: Session = Depends(get_db),
):
    """Log a new progress entry or task."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    # The create function for progress via HTTP API doesn't support linked items; this is an MCP-specific feature.
    return progress_service.create(
        db, workspace_id, entry, None, None, "relates_to_progress"
    )


@router.get("/", response_model=List[progress_schema.ProgressEntryRead])
def read_progress_entries(
    workspace_id_b64: str,
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Retrieve a list of progress entries, optionally filtered by status."""
    return progress_service.get_multi(db, skip=skip, limit=limit, status=status)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_progress_entry(
    workspace_id_b64: str, entry_id: int, db: Session = Depends(get_db)
):
    """Delete a progress entry by its ID."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    deleted = progress_service.delete(db, workspace_id, entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Progress entry not found")
    return
