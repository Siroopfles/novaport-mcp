from sqlalchemy.orm import Session
from typing import Dict, Any, List
from pydantic import ValidationError
from . import decision_service, progress_service, system_pattern_service, custom_data_service
from ..schemas.decision import DecisionCreate
from ..schemas.progress import ProgressEntryCreate
from ..schemas.system_pattern import SystemPatternCreate
from ..schemas.custom_data import CustomDataCreate

def get_recent_activity(db: Session, limit: int = 5) -> Dict[str, List[Any]]:
    return {
        "decisions": decision_service.get_multi(db, limit=limit),
        "progress": progress_service.get_multi(db, limit=limit),
        "system_patterns": system_pattern_service.get_multi(db, limit=limit)
    }

def batch_log_items(
    db: Session,
    workspace_id: str,
    item_type: str,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # Definieer de service functie, het Pydantic schema, en de correcte keyword argument naam
    service_map = {
        "decision": (decision_service.create, DecisionCreate, "decision"),
        "progress": (progress_service.create, ProgressEntryCreate, "entry"),
        "system_pattern": (system_pattern_service.create, SystemPatternCreate, "pattern"),
        "custom_data": (custom_data_service.upsert, CustomDataCreate, "data")
    }
    
    if item_type not in service_map:
        raise ValueError(f"Invalid item_type for batch operation: {item_type}")
        
    service_func, schema, param_name = service_map[item_type]
    success_count, errors = 0, []
    
    for item_data in items:
        try:
            validated_item = schema(**item_data)
            
            kwargs = {
                'db': db,
                'workspace_id': workspace_id,
                param_name: validated_item
            }
            
            # Progress heeft een speciale signatuur die we moeten respecteren
            if item_type == "progress":
                kwargs['linked_item_type'] = None
                kwargs['linked_item_id'] = None
                kwargs['link_relationship_type'] = "relates_to_progress"
            
            service_func(**kwargs)

            success_count += 1
        except (ValidationError, TypeError) as e:
            errors.append({"item": item_data, "error": str(e)})
            
    return {"succeeded": success_count, "failed": len(errors), "details": errors}