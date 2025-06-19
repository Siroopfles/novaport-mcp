from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class SemanticSearchQuery(BaseModel):
    """Represent a semantic search query with parameters."""

    query_text: str = Field(..., min_length=1)
    top_k: int = Field(5, ge=1, le=25)
    filters: Optional[Dict[str, Any]] = Field(
        None, description="ChromaDB 'where' clause"
    )


class SemanticSearchResult(BaseModel):
    """Represent a semantic search result item."""

    id: str
    distance: float
    metadata: Dict[str, Any]
