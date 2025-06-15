from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..schemas import decision as decision_schema
from ..services import decision_service
from ..db.database import get_db

router = APIRouter(prefix="/decisions", tags=["Decisions"])

@router.post("/", response_model=decision_schema.DecisionRead, status_code=status.HTTP_201_CREATED)
def create_decision(decision: decision_schema.DecisionCreate, db: Session = Depends(get_db)):
    """Log a new project or architectural decision."""
    return decision_service.create(db=db, decision=decision)

@router.get("/", response_model=List[decision_schema.DecisionRead])
def read_decisions(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """Retrieve a list of all logged decisions."""
    return decision_service.get_multi(db, skip=skip, limit=limit)

@router.get("/{decision_id}", response_model=decision_schema.DecisionRead)
def read_decision(decision_id: int, db: Session = Depends(get_db)):
    """Retrieve a single decision by its ID."""
    db_decision = decision_service.get(db, decision_id=decision_id)
    if db_decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return db_decision

@router.delete("/{decision_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_decision(decision_id: int, db: Session = Depends(get_db)):
    """Delete a decision by its ID."""
    db_decision = decision_service.delete(db, decision_id=decision_id)
    if db_decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return