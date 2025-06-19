from typing import Any, Dict, List, Literal

from pydantic import BaseModel

ItemType = Literal["decision", "progress", "system_pattern", "custom_data"]


class BatchLogRequest(BaseModel):
    """Represent a batch logging request for multiple items."""

    item_type: ItemType
    items: List[Dict[str, Any]]
