from sqlalchemy.orm import Session
from ..db import models
from ..schemas import context as context_schema

def _get_or_create(db: Session, model):
    """Helper functie om een context record op te halen of aan te maken met standaard content."""
    instance = db.query(model).filter_by(id=1).first()
    if not instance:
        instance = model(id=1, content={})
        db.add(instance)
        db.commit()
        db.refresh(instance)
    return instance

def get_product_context(db: Session):
    """Haalt de product context op, maakt deze aan als deze nog niet bestaat."""
    return _get_or_create(db, models.ProductContext)

def get_active_context(db: Session):
    """Haalt de actieve context op, maakt deze aan als deze nog niet bestaat."""
    return _get_or_create(db, models.ActiveContext)

def update_context(db: Session, instance, update_data: context_schema.ContextUpdate):
    """Werkt context bij met volledige content of patch-gebaseerde updates."""
    current_content = dict(instance.content)
    new_content = current_content.copy()

    if update_data.content is not None:
        new_content = update_data.content
    elif update_data.patch_content is not None:
        for key, value in update_data.patch_content.items():
            if value == "__DELETE__":
                new_content.pop(key, None)
            else:
                new_content[key] = value

    if new_content != current_content:
        instance.content = new_content
        db.add(instance)
        db.commit()
        db.refresh(instance)
        
    return instance