import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ..db import models
from ..schemas import link as link_schema
from ..schemas import progress as progress_schema
from . import link_service, vector_service


def create(db: Session, workspace_id: str, entry: progress_schema.ProgressEntryCreate, linked_item_type: Optional[str], linked_item_id: Optional[str], link_relationship_type: str) -> models.ProgressEntry:
    db_entry = models.ProgressEntry(**entry.model_dump())
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)

    text = f"Progress {db_entry.status}: {db_entry.description}"
    metadata = {"item_type": "progress", "status": db_entry.status}
    vector_service.upsert_embedding(workspace_id, f"progress_{db_entry.id}", text, metadata)

    if linked_item_type and linked_item_id:
        link_data = link_schema.LinkCreate(source_item_type="progress_entry", source_item_id=str(db_entry.id), target_item_type=linked_item_type, target_item_id=str(linked_item_id), relationship_type=link_relationship_type)
        link_service.create(db, link_data)

    return db_entry

def get(db: Session, entry_id: int) -> models.ProgressEntry | None:
    return db.query(models.ProgressEntry).filter(models.ProgressEntry.id == entry_id).first()

def get_multi(db: Session, skip: int = 0, limit: int = 100, status: Optional[str] = None, parent_id: Optional[int] = None, since: Optional[datetime.datetime] = None) -> List[models.ProgressEntry]:
    query = db.query(models.ProgressEntry)
    if status:
        query = query.filter(models.ProgressEntry.status == status)
    if parent_id is not None:
        query = query.filter(models.ProgressEntry.parent_id == parent_id)
    if since:
        query = query.filter(models.ProgressEntry.timestamp >= since)
    return query.order_by(models.ProgressEntry.timestamp.desc()).offset(skip).limit(limit).all()

def update(db: Session, entry_id: int, update_data: progress_schema.ProgressEntryUpdate) -> models.ProgressEntry | None:
    db_entry = get(db, entry_id)
    if db_entry:
        update_dict = update_data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            setattr(db_entry, key, value)
        db.commit()
        db.refresh(db_entry)
    return db_entry

def delete(db: Session, workspace_id: str, entry_id: int) -> models.ProgressEntry | None:
    db_entry = get(db, entry_id)
    if db_entry:
        vector_service.delete_embedding(workspace_id, f"progress_{entry_id}")
        db.delete(db_entry)
        db.commit()
    return db_entry
