import datetime
from typing import Any, Callable, Dict, List, Optional

from pydantic import ValidationError
from sqlalchemy.orm import Session

from ..schemas.custom_data import CustomDataCreate
from ..schemas.decision import DecisionCreate
from ..schemas.progress import ProgressEntryCreate
from ..schemas.system_pattern import SystemPatternCreate
from . import (
    custom_data_service,
    decision_service,
    progress_service,
    system_pattern_service,
)


def get_recent_activity(db: Session, limit: int = 5, since: Optional[datetime.datetime] = None) -> Dict[str, List[Any]]:
    return {
        "decisions": decision_service.get_multi(db, limit=limit, since=since),
        "progress": progress_service.get_multi(db, limit=limit, since=since),
        "system_patterns": system_pattern_service.get_multi(db, limit=limit, since=since)
    }

def batch_log_items(
    db: Session,
    workspace_id: str,
    item_type: str,
    items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    # Define the service function, the Pydantic schema, and the correct keyword argument name
    service_map = {
        "decision": (decision_service.create, DecisionCreate, "decision"),
        "progress": (progress_service.create, ProgressEntryCreate, "entry"),
        "system_pattern": (system_pattern_service.create, SystemPatternCreate, "pattern"),
        "custom_data": (custom_data_service.upsert, CustomDataCreate, "data")
    }

    if item_type not in service_map:
        raise ValueError(f"Invalid item_type for batch operation: {item_type}")

    service_func: Callable[..., Any]
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

            # Progress has a special signature that we must respect
            if item_type == "progress":
                kwargs['linked_item_type'] = None
                kwargs['linked_item_id'] = None
                kwargs['link_relationship_type'] = "relates_to_progress"

            service_func(**kwargs)

            success_count += 1
        except (ValidationError, TypeError) as e:
            errors.append({"item": item_data, "error": str(e)})

    return {"succeeded": success_count, "failed": len(errors), "details": errors}
