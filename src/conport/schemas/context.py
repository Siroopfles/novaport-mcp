from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator

class ContextBase(BaseModel):
    content: Dict[str, Any]

class ContextRead(ContextBase): pass

class ContextUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = Field(None, description="The full new context content. Overwrites existing.")
    patch_content: Optional[Dict[str, Any]] = Field(None, description="A dictionary of changes to apply. Use `__DELETE__` as value to remove a key.")