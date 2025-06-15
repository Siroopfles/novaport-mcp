from typing import Dict, Any, Optional
from pydantic import BaseModel, Field, model_validator
class ContextBase(BaseModel):
    content: Dict[str, Any]
class ContextRead(ContextBase): pass
class ContextUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = Field(None, description="The full new context content. Overwrites existing.")
    patch_content: Optional[Dict[str, Any]] = Field(None, description="A dictionary of changes to apply. Use `__DELETE__` as value to remove a key.")
    @model_validator(mode='before')
    @classmethod
    def check_content_or_patch(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if values.get('content') is None and values.get('patch_content') is None:
            raise ValueError("Either 'content' or 'patch_content' must be provided.")
        if values.get('content') is not None and values.get('patch_content') is not None:
            raise ValueError("Provide either 'content' or 'patch_content', not both.")
        return values