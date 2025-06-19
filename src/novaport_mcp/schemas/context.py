from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ContextBase(BaseModel):
    """Represent the base context data structure."""

    content: Dict[str, Any]


class ContextRead(ContextBase):
    """Represent context data for read operations."""

    pass


class ContextUpdate(BaseModel):
    """Represent context data for update operations."""

    content: Optional[Dict[str, Any]] = Field(
        None, description="The full new context content. Overwrites existing."
    )
    patch_content: Optional[Dict[str, Any]] = Field(
        None,
        description="A dictionary of changes to apply. Use `__DELETE__` as value to remove a key.",
    )
