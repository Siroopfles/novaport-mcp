from typing import List, Optional

from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..db import models
from ..schemas import system_pattern as sp_schema
from . import vector_service


def create(db: Session, workspace_id: str, pattern: sp_schema.SystemPatternCreate) -> models.SystemPattern:
    """Creates a new system pattern and its vector embedding."""
    db_pattern = models.SystemPattern(**pattern.model_dump())
    db.add(db_pattern)
    db.commit()
    db.refresh(db_pattern)

    text_to_embed = f"System Pattern: {db_pattern.name}\nDescription: {db_pattern.description or ''}"
    tags_list = db_pattern.tags
    tags_str = ", ".join(tags_list) if isinstance(tags_list, list) else ""
    metadata = {"item_type": "system_pattern", "name": db_pattern.name, "tags": tags_str}
    vector_service.upsert_embedding(workspace_id, f"system_pattern_{db_pattern.id}", text_to_embed, metadata)

    return db_pattern

def get(db: Session, pattern_id: int) -> models.SystemPattern | None:
    """Retrieves a single system pattern by its ID."""
    return db.query(models.SystemPattern).filter(models.SystemPattern.id == pattern_id).first()

def get_multi(db: Session, skip: int = 0, limit: int = 100,
              tags_all: Optional[List[str]] = None,
              tags_any: Optional[List[str]] = None) -> List[models.SystemPattern]:
    """Retrieves a list of system patterns, with optional tag filtering."""
    query = db.query(models.SystemPattern)

    if tags_all:
        for tag in tags_all:
            query = query.filter(models.SystemPattern.tags.like(f'%"{tag}"%'))
    if tags_any:
        filters = [models.SystemPattern.tags.like(f'%"{tag}"%') for tag in tags_any]
        query = query.filter(or_(*filters))

    return query.order_by(models.SystemPattern.name).offset(skip).limit(limit).all()

def delete(db: Session, workspace_id: str, pattern_id: int) -> models.SystemPattern | None:
    """Deletes a system pattern and its vector embedding by its ID."""
    db_pattern = get(db, pattern_id)
    if db_pattern:
        vector_service.delete_embedding(workspace_id, f"system_pattern_{pattern_id}")
        db.delete(db_pattern)
        db.commit()
    return db_pattern
