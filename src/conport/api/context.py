from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..schemas import context as context_schema
from ..services import context_service
from ..db.database import get_db

router = APIRouter(tags=["Context"])

@router.get("/product-context", response_model=context_schema.ContextRead)
def read_product_context(db: Session = Depends(get_db)):
    """Retrieve the global product context for the workspace."""
    ctx = context_service.get_product_context(db)
    return ctx

@router.put("/product-context", response_model=context_schema.ContextRead)
def update_product_context(update_data: context_schema.ContextUpdate, db: Session = Depends(get_db)):
    """
    Update the product context.
    Use 'content' for a full overwrite or 'patch_content' for a partial update.
    To delete a key with patch, provide its key with `__DELETE__` as the value.
    """
    instance = context_service.get_product_context(db)
    return context_service.update_context(db, instance, update_data)

@router.get("/active-context", response_model=context_schema.ContextRead)
def read_active_context(db: Session = Depends(get_db)):
    """Retrieve the current active/session context for the workspace."""
    ctx = context_service.get_active_context(db)
    return ctx

@router.put("/active-context", response_model=context_schema.ContextRead)
def update_active_context(update_data: context_schema.ContextUpdate, db: Session = Depends(get_db)):
    """
    Update the active context.
    Use 'content' for a full overwrite or 'patch_content' for a partial update.
    To delete a key with patch, provide its key with `__DELETE__` as the value.
    """
    instance = context_service.get_active_context(db)
    return context_service.update_context(db, instance, update_data)