import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict


class HistoryRead(BaseModel):
    """Represent history data for read operations."""

    id: int
    timestamp: datetime.datetime
    version: int
    content: Dict[str, Any]
    change_source: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
