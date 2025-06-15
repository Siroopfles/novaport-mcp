from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List
from ..db import models
from ..schemas import link as link_schema
def create(db: Session, link: link_schema.LinkCreate) -> models.ContextLink:
    db_link = models.ContextLink(**link.model_dump())
    db.add(db_link); db.commit(); db.refresh(db_link)
    return db_link
def get_for_item(db: Session, item_type: str, item_id: str) -> List[models.ContextLink]:
    item_id_str = str(item_id)
    return db.query(models.ContextLink).filter(or_((models.ContextLink.source_item_type == item_type) & (models.ContextLink.source_item_id == item_id_str),(models.ContextLink.target_item_type == item_type) & (models.ContextLink.target_item_id == item_id_str))).all()