from typing import List, Dict, Any, Literal
from pydantic import BaseModel
ItemType = Literal["decision", "progress", "system_pattern", "custom_data"]
class BatchLogRequest(BaseModel):
    item_type: ItemType
    items: List[Dict[str, Any]]