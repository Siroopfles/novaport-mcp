import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DecisionBase(BaseModel):
    summary: str = Field(..., min_length=1)
    rationale: Optional[str] = None
    implementation_details: Optional[str] = None
    tags: Optional[List[str]] = []
class DecisionCreate(DecisionBase): pass
class DecisionRead(DecisionBase):
    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
