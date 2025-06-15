import json, logging
from sqlalchemy.orm import Session, exc
from sqlalchemy import text
from typing import List
from . import vector_service
from ..db import models
from ..schemas import custom_data as cd_schema
log = logging.getLogger(__name__)
def upsert(db: Session, data: cd_schema.CustomDataCreate) -> models.CustomData:
    try:
        db_data = db.query(models.CustomData).filter_by(category=data.category, key=data.key).one()
        db_data.value = data.value
    except exc.NoResultFound:
        db_data = models.CustomData(**data.model_dump())
        db.add(db_data)
    db.commit(); db.refresh(db_data)
    try:
        text_value = json.dumps(db_data.value) if not isinstance(db_data.value, str) else db_data.value
        text = f"Custom Data in category '{db_data.category}' key '{db_data.key}': {text_value}"
        metadata = {"item_type": "custom_data", "category": db_data.category, "key": db_data.key}
        vector_service.upsert_embedding(f"custom_data_{db_data.id}", text, metadata)
    except (TypeError, OverflowError): log.warning(f"Could not serialize value for custom_data {db_data.id} for embedding.")
    return db_data
def get(db: Session, category: str, key: str) -> models.CustomData | None:
    return db.query(models.CustomData).filter_by(category=category, key=key).first()
def get_by_category(db: Session, category: str) -> List[models.CustomData]:
    return db.query(models.CustomData).filter_by(category=category).all()
def delete(db: Session, category: str, key: str) -> models.CustomData | None:
    db_data = get(db, category, key)
    if db_data:
        vector_service.delete_embedding(f"custom_data_{db_data.id}"); db.delete(db_data); db.commit()
    return db_data
def search_fts(db: Session, query: str, category: str | None = None, limit: int = 10) -> List[models.CustomData]:
    where_clauses, params = ["fts.custom_data_fts MATCH :query"], {"query": query, "limit": limit}
    if category: where_clauses.append("fts.category = :category"); params["category"] = category
    stmt = text(f'SELECT cd.* FROM custom_data cd JOIN custom_data_fts fts ON cd.id = fts.rowid WHERE {" AND ".join(where_clauses)} ORDER BY rank LIMIT :limit')
    result_proxy = db.execute(stmt, params)
    return [models.CustomData(**row._mapping) for row in result_proxy]