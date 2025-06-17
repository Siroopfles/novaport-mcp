from typing import Any, Optional

from pydantic import BaseModel


class MCPError(BaseModel):
    """Pydantic model for MCP errors."""

    error: str
    details: Optional[Any] = None
