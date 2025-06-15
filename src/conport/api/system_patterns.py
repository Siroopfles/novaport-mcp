from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..schemas import system_pattern as sp_schema
from ..services import system_pattern_service
from ..db.database import get_db

router = APIRouter(prefix="/system-patterns", tags=["System Patterns"])

@router.post("/", response_model=sp_schema.SystemPatternRead, status_code=status.HTTP_201_CREATED)
def create_system_pattern(pattern: sp_schema.SystemPatternCreate, db: Session = Depends(get_db)):
    """Log a new system or architectural pattern."""
    return system_pattern_service.create(db=db, pattern=pattern)

@router.get("/", response_model=List[sp_schema.SystemPatternRead])
def read_system_patterns(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve a list of all logged system patterns."""
    return system_pattern_service.get_multi(db, skip=skip, limit=limit)

@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_system_pattern(pattern_id: int, db: Session = Depends(get_db)):
    """Delete a system pattern by its ID."""
    db_pattern = system_pattern_service.delete(db, pattern_id=pattern_id)
    if db_pattern is None:
        raise HTTPException(status_code=404, detail="System pattern not found")
    return