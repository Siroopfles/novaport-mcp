from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from ..schemas import progress as progress_schema
from ..services import progress_service
from ..db.database import get_db

router = APIRouter(prefix="/progress", tags=["Progress"])

@router.post("/", response_model=progress_schema.ProgressEntryRead, status_code=status.HTTP_201_CREATED)
def create_progress_entry(entry: progress_schema.ProgressEntryCreate, db: Session = Depends(get_db)):
    """Log a new progress entry or task."""
    return progress_service.create(db=db, entry=entry)

@router.get("/", response_model=List[progress_schema.ProgressEntryRead])
def read_progress_entries(skip: int = 0, limit: int = 100, status: Optional[str] = None, db: Session = Depends(get_db)):
    """Retrieve a list of progress entries, optionally filtered by status."""
    return progress_service.get_multi(db, skip=skip, limit=limit, status=status)

@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_progress_entry(entry_id: int, db: Session = Depends(get_db)):
    """Delete a progress entry by its ID."""
    db_entry = progress_service.delete(db, entry_id=entry_id)
    if db_entry is None:
        raise HTTPException(status_code=404, detail="Progress entry not found")
    return