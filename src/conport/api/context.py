from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..schemas import context as context_schema
from ..services import context_service
from ..db.database import get_db
from ..core.config import decode_workspace_id

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/context", tags=["Context"])

@router.get("/product", response_model=context_schema.ContextRead)
def read_product_context(workspace_id_b64: str, db: Session = Depends(get_db)):
    """Retrieve the global product context for the workspace."""
    ctx = context_service.get_product_context(db)
    return ctx

@router.put("/product", response_model=context_schema.ContextRead)
def update_product_context(workspace_id_b64: str, update_data: context_schema.ContextUpdate, db: Session = Depends(get_db)):
    """
    Update the product context.
    Use 'content' for a full overwrite or 'patch_content' for a partial update.
    """
    instance = context_service.get_product_context(db)
    return context_service.update_context(db, instance, update_data)

@router.get("/active", response_model=context_schema.ContextRead)
def read_active_context(workspace_id_b64: str, db: Session = Depends(get_db)):
    """Retrieve the current active/session context for the workspace."""
    ctx = context_service.get_active_context(db)
    return ctx

@router.put("/active", response_model=context_schema.ContextRead)
def update_active_context(workspace_id_b64: str, update_data: context_schema.ContextUpdate, db: Session = Depends(get_db)):
    """
    Update the active context.
    Use 'content' for a full overwrite or 'patch_content' for a partial update.
    """
    instance = context_service.get_active_context(db)
    return context_service.update_context(db, instance, update_data)