import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class SystemPatternBase(BaseModel):
    """Represent the base system pattern data structure."""

    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    tags: Optional[List[str]] = []

class SystemPatternCreate(SystemPatternBase):
    """Represent system pattern data for creation operations."""

    pass

class SystemPatternRead(SystemPatternBase):
    """Represent system pattern data for read operations."""

    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
