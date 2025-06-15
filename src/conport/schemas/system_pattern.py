import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict
class SystemPatternBase(BaseModel):
    name: str = Field(..., min_length=1)
    description: Optional[str] = None
    tags: Optional[List[str]] = []
class SystemPatternCreate(SystemPatternBase): pass
class SystemPatternRead(SystemPatternBase):
    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)