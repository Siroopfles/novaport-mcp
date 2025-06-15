from sqlalchemy.orm import Session
from sqlalchemy import text, or_
from typing import List, Optional
from . import vector_service
from ..db import models
from ..schemas import decision as decision_schema
def create(db: Session, decision: decision_schema.DecisionCreate) -> models.Decision:
    db_decision = models.Decision(**decision.model_dump())
    db.add(db_decision); db.commit(); db.refresh(db_decision)
    text = f"Decision: {db_decision.summary}\nRationale: {db_decision.rationale or ''}"
    tags = db_decision.tags
    tags_str = ", ".join(tags) if isinstance(tags, list) else ""
    metadata = {"item_type": "decision", "summary": db_decision.summary, "tags": tags_str}
    vector_service.upsert_embedding(f"decision_{db_decision.id}", text, metadata)
    return db_decision
def get(db: Session, decision_id: int) -> models.Decision | None:
    return db.query(models.Decision).filter(models.Decision.id == decision_id).first()
def get_multi(db: Session, skip: int = 0, limit: int = 100, tags_all: Optional[List[str]] = None, tags_any: Optional[List[str]] = None) -> List[models.Decision]:
    query = db.query(models.Decision)
    if tags_all:
        for tag in tags_all: query = query.filter(models.Decision.tags.like(f'%"{tag}"%'))
    if tags_any:
        filters = [models.Decision.tags.like(f'%"{tag}"%') for tag in tags_any]
        query = query.filter(or_(*filters))
    return query.order_by(models.Decision.timestamp.desc()).offset(skip).limit(limit).all()
def delete(db: Session, decision_id: int) -> models.Decision | None:
    db_decision = get(db, decision_id)
    if db_decision:
        vector_service.delete_embedding(f"decision_{decision_id}"); db.delete(db_decision); db.commit()
    return db_decision
def search_fts(db: Session, query: str, limit: int = 10) -> List[models.Decision]:
    stmt = text('SELECT d.* FROM decisions d JOIN decisions_fts fts ON d.id = fts.rowid WHERE fts.decisions_fts MATCH :query ORDER BY rank LIMIT :limit')
    result_proxy = db.execute(stmt, {"query": query, "limit": limit})
    return [models.Decision(**row._mapping) for row in result_proxy]