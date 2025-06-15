from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from ..schemas import batch as batch_schema
from ..services import meta_service
from ..db.database import get_db

router = APIRouter(prefix="/batch", tags=["Batch Operations"])

@router.post("/log-items", status_code=status.HTTP_200_OK)
def batch_log_items(request: batch_schema.BatchLogRequest, db: Session = Depends(get_db)):
    """
    Logs multiple items of the same type in a single request.
    Supported item_types are: 'decision', 'progress', 'system_pattern', 'custom_data'.
    """
    try:
        result = meta_service.batch_log_items(db, item_type=request.item_type, items=request.items)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))