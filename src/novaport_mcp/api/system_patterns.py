from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import decode_workspace_id
from ..db.database import get_db
from ..schemas import system_pattern as sp_schema
from ..services import system_pattern_service

router = APIRouter(
    prefix="/workspaces/{workspace_id_b64}/system-patterns", tags=["System Patterns"]
)


@router.post(
    "/", response_model=sp_schema.SystemPatternRead, status_code=status.HTTP_201_CREATED
)
def create_system_pattern(
    workspace_id_b64: str,
    pattern: sp_schema.SystemPatternCreate,
    db: Session = Depends(get_db),
):
    """Log a new system or architectural pattern."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    return system_pattern_service.create(
        db=db, workspace_id=workspace_id, pattern=pattern
    )


@router.get("/", response_model=List[sp_schema.SystemPatternRead])
def read_system_patterns(
    workspace_id_b64: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """Retrieve a list of all logged system patterns."""
    return system_pattern_service.get_multi(db, skip=skip, limit=limit)


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_pattern(
    workspace_id_b64: str, pattern_id: int, db: Session = Depends(get_db)
):
    """Delete a system pattern by its ID."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    deleted = system_pattern_service.delete(db, workspace_id, pattern_id=pattern_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="System pattern not found")
    return
