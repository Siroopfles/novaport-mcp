import datetime
from typing import List, Optional

from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from ..db import models
from ..schemas import decision as decision_schema
from . import vector_service


# The create function now takes a workspace_id parameter
def create(db: Session, workspace_id: str, decision: decision_schema.DecisionCreate) -> models.Decision:
    db_decision = models.Decision(**decision.model_dump())
    db.add(db_decision)
    db.commit()
    db.refresh(db_decision)

    # Prepare text and metadata for vector embedding
    text = f"Decision: {db_decision.summary}\nRationale: {db_decision.rationale or ''}"
    db_tags = db_decision.tags
    tags_list = db_tags if isinstance(db_tags, list) else []
    metadata = {"item_type": "decision", "summary": db_decision.summary, "tags": tags_list}
    vector_service.upsert_embedding(workspace_id, f"decision_{db_decision.id}", text, metadata)
    return db_decision

def get(db: Session, decision_id: int) -> Optional[models.Decision]:
    return db.query(models.Decision).filter(models.Decision.id == decision_id).first()

def get_multi(db: Session, skip: int = 0, limit: int = 100, tags_all: Optional[List[str]] = None, tags_any: Optional[List[str]] = None, since: Optional[datetime.datetime] = None) -> List[models.Decision]:
    query = db.query(models.Decision)
    if tags_all:
        for tag in tags_all:
            query = query.filter(models.Decision.tags.like(f'%"{tag}"%'))
    if tags_any:
        filters = [models.Decision.tags.like(f'%"{tag}"%') for tag in tags_any]
        query = query.filter(or_(*filters))
    if since:
        query = query.filter(models.Decision.timestamp >= since)
    return query.order_by(models.Decision.timestamp.desc()).offset(skip).limit(limit).all()

def delete(db: Session, workspace_id: str, decision_id: int) -> Optional[models.Decision]:
    db_decision = get(db, decision_id)
    if db_decision:
        vector_service.delete_embedding(workspace_id, f"decision_{decision_id}")
        db.delete(db_decision)
        db.commit()
    return db_decision

def search_fts(db: Session, query: str, limit: int = 10) -> List[models.Decision]:
    # This part depends on whether you have FTS tables in your migrations.
    # If this gives an error, the FTS setup in Alembic needs to be checked.
    # For now we assume that the 'decisions_fts' table exists.
    try:
        stmt = text('SELECT d.* FROM decisions d JOIN decisions_fts fts ON d.id = fts.rowid WHERE fts.decisions_fts MATCH :query ORDER BY rank LIMIT :limit')
        result_proxy = db.execute(stmt, {"query": query, "limit": limit})
        return [models.Decision(**row._mapping) for row in result_proxy]
    except Exception:
        # Fallback if FTS is not set up
        return db.query(models.Decision).filter(models.Decision.summary.contains(query)).limit(limit).all()
