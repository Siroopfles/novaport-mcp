from typing import List
from fastapi import APIRouter
from ..schemas import search as search_schema
from ..services import vector_service

router = APIRouter(prefix="/search", tags=["Search"])

@router.post("/semantic", response_model=List[search_schema.SemanticSearchResult])
def semantic_search(query: search_schema.SemanticSearchQuery):
    """
    Perform a semantic search across the vector store.
    The 'filters' field should be a ChromaDB compatible 'where' dictionary.
    Example: `{"item_type": "decision"}` or `{"$and": [{"tags": {"$contains": "db"}}, {"item_type": "decision"}]}`
    """
    return vector_service.search(
        query_text=query.query_text,
        top_k=query.top_k,
        filters=query.filters
    )