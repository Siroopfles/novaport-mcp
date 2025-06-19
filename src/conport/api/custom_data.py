from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..core.config import decode_workspace_id
from ..db.database import get_db
from ..schemas import custom_data as cd_schema
from ..services import custom_data_service

router = APIRouter(
    prefix="/workspaces/{workspace_id_b64}/custom-data", tags=["Custom Data"]
)


@router.post("/", response_model=cd_schema.CustomDataRead)
def upsert_custom_data(
    workspace_id_b64: str,
    data: cd_schema.CustomDataCreate,
    db: Session = Depends(get_db),
):
    """Create a new custom data entry, or update it if it already exists."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    return custom_data_service.upsert(db=db, workspace_id=workspace_id, data=data)


@router.get("/{category}", response_model=List[cd_schema.CustomDataRead])
def read_custom_data_by_category(
    workspace_id_b64: str, category: str, db: Session = Depends(get_db)
):
    """Retrieve all custom data items for a specific category."""
    return custom_data_service.get_by_category(db, category=category)


@router.get("/{category}/{key}", response_model=cd_schema.CustomDataRead)
def read_custom_data_item(
    workspace_id_b64: str, category: str, key: str, db: Session = Depends(get_db)
):
    """Retrieve a single custom data item by its category and key."""
    db_data = custom_data_service.get(db, category=category, key=key)
    if db_data is None:
        raise HTTPException(status_code=404, detail="Custom data item not found")
    return db_data


@router.delete("/{category}/{key}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_data_item(
    workspace_id_b64: str, category: str, key: str, db: Session = Depends(get_db)
):
    """Delete a custom data item by its category and key."""
    workspace_id = decode_workspace_id(workspace_id_b64)
    deleted = custom_data_service.delete(
        db, workspace_id=workspace_id, category=category, key=key
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Custom data item not found")
    return
