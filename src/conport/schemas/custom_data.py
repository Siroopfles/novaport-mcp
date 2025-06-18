import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class CustomDataBase(BaseModel):
    """Represent the base custom data structure."""

    category: str
    key: str
    value: Any

class CustomDataCreate(CustomDataBase):
    """Represent custom data for creation operations."""

    pass

class CustomDataRead(CustomDataBase):
    """Represent custom data for read operations."""

    id: int
    timestamp: datetime.datetime
    model_config = ConfigDict(from_attributes=True)
