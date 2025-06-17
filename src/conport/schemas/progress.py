import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProgressEntryBase(BaseModel):
    status: str
    description: str
    parent_id: Optional[int] = None
class ProgressEntryCreate(ProgressEntryBase): pass
class ProgressEntryUpdate(BaseModel):
    status: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None
class ProgressEntryRead(ProgressEntryBase):
    id: int
    timestamp: datetime.datetime
    children: List['ProgressEntryRead'] = []
    model_config = ConfigDict(from_attributes=True)
