from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from ..schemas import search as search_schema
from ..services import vector_service
from ..core.config import decode_workspace_id

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/search", tags=["Search"])

@router.post("/semantic", response_model=List[search_schema.SemanticSearchResult])
def semantic_search(workspace_id_b64: str, query: search_schema.SemanticSearchQuery):
    """
    Perform a semantic search across the vector store for a specific workspace.
    The 'filters' field should be a ChromaDB compatible 'where' dictionary.
    """
    try:
        workspace_id = decode_workspace_id(workspace_id_b64)
        return vector_service.search(
            workspace_id=workspace_id,
            query_text=query.query_text,
            top_k=query.top_k,
            filters=query.filters
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))