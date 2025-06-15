from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..schemas import history as history_schema
from ..db import models, database

router = APIRouter(prefix="/history", tags=["History"])

@router.get("/{item_type}", response_model=List[history_schema.HistoryRead])
def get_item_history(
    item_type: str,
    db: Session = Depends(database.get_db),
    limit: int = Query(10, ge=1, le=100)
):
    """
    Retrieve the version history for 'product_context' or 'active_context'.
    """
    history_model = None
    if item_type == "product_context":
        history_model = models.ProductContextHistory
    elif item_type == "active_context":
        history_model = models.ActiveContextHistory
    else:
        raise HTTPException(status_code=400, detail="Invalid item_type. Must be 'product_context' or 'active_context'.")

    history_records = db.query(history_model).order_by(history_model.version.desc()).limit(limit).all()
    return history_records