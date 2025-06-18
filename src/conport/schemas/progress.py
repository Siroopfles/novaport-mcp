import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ProgressEntryBase(BaseModel):
    """Represent the base progress entry data structure."""

    status: str
    description: str
    parent_id: Optional[int] = None

class ProgressEntryCreate(ProgressEntryBase):
    """Represent progress entry data for creation operations."""

    pass

class ProgressEntryUpdate(BaseModel):
    """Represent progress entry data for update operations."""

    status: Optional[str] = None
    description: Optional[str] = None
    parent_id: Optional[int] = None

class ProgressEntryRead(ProgressEntryBase):
    """Represent progress entry data for read operations."""

    id: int
    timestamp: datetime.datetime
    children: List['ProgressEntryRead'] = []
    model_config = ConfigDict(from_attributes=True)
