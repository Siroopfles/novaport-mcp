from sqlalchemy.orm import Session
from typing import Dict, Any, List
from . import decision_service, progress_service, system_pattern_service, custom_data_service
from ..schemas.decision import DecisionCreate
from ..schemas.progress import ProgressEntryCreate
from ..schemas.system_pattern import SystemPatternCreate
from ..schemas.custom_data import CustomDataCreate
def get_recent_activity(db: Session, limit: int = 5) -> Dict[str, List[Any]]:
    return {"decisions": decision_service.get_multi(db, limit=limit), "progress": progress_service.get_multi(db, limit=limit), "system_patterns": system_pattern_service.get_multi(db, limit=limit)}
def batch_log_items(db: Session, item_type: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    service_map = {"decision": (decision_service, DecisionCreate), "progress": (progress_service, ProgressEntryCreate), "system_pattern": (system_pattern_service, SystemPatternCreate), "custom_data": (custom_data_service, CustomDataCreate)}
    if item_type not in service_map: raise ValueError(f"Invalid item_type for batch operation: {item_type}")
    service, schema = service_map[item_type]
    success_count, errors = 0, []
    for item_data in items:
        try:
            validated_item = schema(**item_data)
            if item_type == "custom_data": service.upsert(db, validated_item)
            else: service.create(db, validated_item)
            success_count += 1
        except Exception as e: errors.append({"item": item_data, "error": str(e)})
    return {"succeeded": success_count, "failed": len(errors), "errors": errors}