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

def batch_log_items(db: Session, workspace_id: str, item_type: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    service_map = {
        "decision": (decision_service.create, DecisionCreate),
        "progress": (progress_service.create, ProgressEntryCreate),
        "system_pattern": (system_pattern_service.create, SystemPatternCreate),
        "custom_data": (custom_data_service.upsert, CustomDataCreate)
    }
    
    if item_type not in service_map:
        raise ValueError(f"Invalid item_type for batch operation: {item_type}")
        
    service_func, schema = service_map[item_type]
    success_count, errors = 0, []
    
    for item_data in items:
        try:
            validated_item = schema(**item_data)
            
            # Een meer generieke manier om de service aan te roepen
            if item_type == "progress":
                 service_func(db, workspace_id, validated_item, None, None, "relates_to_progress")
            elif item_type == "custom_data":
                 service_func(db=db, workspace_id=workspace_id, data=validated_item)
            elif item_type == "decision":
                 service_func(db=db, workspace_id=workspace_id, decision=validated_item)
            elif item_type == "system_pattern":
                 service_func(db=db, workspace_id=workspace_id, pattern=validated_item)

            success_count += 1
        except (ValidationError, TypeError) as e:
            errors.append({"item": item_data, "error": str(e)})
            
    return {"succeeded": success_count, "failed": len(errors), "errors": errors}