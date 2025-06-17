import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CustomDataBase(BaseModel):
    category: str
    key: str
    value: Any
class CustomDataCreate(CustomDataBase): pass
class CustomDataRead(CustomDataBase):
    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
