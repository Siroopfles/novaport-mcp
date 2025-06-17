from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..db.database import get_db
from ..schemas import link as link_schema
from ..services import link_service

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/links", tags=["Links"])

@router.post("/", response_model=link_schema.LinkRead, status_code=status.HTTP_201_CREATED)
def create_link(workspace_id_b64: str, link: link_schema.LinkCreate, db: Session = Depends(get_db)):
    """Create a new link between two ConPort items."""
    return link_service.create(db=db, link=link)

@router.get("/{item_type}/{item_id}", response_model=List[link_schema.LinkRead])
def read_links_for_item(workspace_id_b64: str, item_type: str, item_id: str, db: Session = Depends(get_db)):
    """Retrieve all links connected to a specific ConPort item."""
    return link_service.get_for_item(db, item_type=item_type, item_id=item_id)
