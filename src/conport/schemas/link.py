import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
class LinkBase(BaseModel):
    source_item_type: str
    source_item_id: str
    target_item_type: str
    target_item_id: str
    relationship_type: str
    description: Optional[str] = None
class LinkCreate(LinkBase): pass
class LinkRead(LinkBase):
    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)