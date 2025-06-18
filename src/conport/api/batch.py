from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import decode_workspace_id
from ..db.database import get_db
from ..schemas import batch as batch_schema
from ..services import meta_service

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/batch", tags=["Batch Operations"])

@router.post("/log-items", status_code=status.HTTP_200_OK)
def batch_log_items(
    workspace_id_b64: str,
    request: batch_schema.BatchLogRequest,
    db: Session = Depends(get_db)
):
    """Log multiple items of the same type in a single request for a specific workspace."""
    try:
        workspace_id = decode_workspace_id(workspace_id_b64)
        result = meta_service.batch_log_items(db, workspace_id, request.item_type, request.items)
        return result
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
