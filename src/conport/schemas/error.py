from typing import Any, Optional
from pydantic import BaseModel


class MCPError(BaseModel):
    """Pydantic model voor MCP fouten."""
    error: str
    details: Optional[Any] = None