import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LinkBase(BaseModel):
    """Represent the base link data structure between items."""

    source_item_type: str
    source_item_id: str
    target_item_type: str
    target_item_id: str
    relationship_type: str = Field(..., min_length=1, description="The type of relationship between items")
    description: Optional[str] = None

class LinkCreate(LinkBase):
    """Represent link data for creation operations."""

    pass

class LinkRead(LinkBase):
    """Represent link data for read operations."""

    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
