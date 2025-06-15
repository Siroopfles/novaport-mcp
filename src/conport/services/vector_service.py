import logging
from typing import List, Dict, Any, Optional, cast
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.client import Client 
from pathlib import Path
from ..core.config import settings
log = logging.getLogger(__name__)
_model: Optional[SentenceTransformer] = None
_chroma_client: Optional[Client] = None
def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(f"Loading sentence transformer model: {settings.EMBEDDING_MODEL_NAME}...")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        log.info("Embedding model loaded.")
    return _model
def get_chroma_client() -> Client:
    global _chroma_client
    if _chroma_client is None:
        log.info("Initializing ChromaDB client...")
        db_path = Path(settings.VECTOR_DB_PATH)
        db_path.mkdir(parents=True, exist_ok=True)
        _chroma_client = cast(Client, chromadb.PersistentClient(path=str(db_path), settings=ChromaSettings(anonymized_telemetry=False)))
        log.info(f"ChromaDB client initialized at {db_path}")
    return _chroma_client
def get_collection(collection_name: str = "conport_default"):
    client = get_chroma_client()
    return client.get_or_create_collection(name=collection_name)
def generate_embedding(text: str) -> List[float]:
    model = get_embedding_model()
    return model.encode(text, convert_to_tensor=False).tolist()
def upsert_embedding(item_id: str, text_to_embed: str, metadata: Dict[str, Any]):
    collection = get_collection()
    embedding = generate_embedding(text_to_embed)
    safe_metadata = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
    collection.upsert(ids=[item_id], embeddings=[embedding], metadatas=[safe_metadata])
    log.info(f"Upserted embedding for item {item_id}")
def delete_embedding(item_id: str):
    collection = get_collection()
    try: collection.delete(ids=[item_id]); log.info(f"Deleted embedding for item {item_id}")
    except Exception as e: log.warning(f"Could not delete embedding for {item_id} (may not exist): {e}")
def search(query_text: str, top_k: int, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
    collection = get_collection()
    query_embedding = generate_embedding(query_text)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=filters)
    output = []
    if not results or not results.get('ids') or not results['ids'][0]: return []
    ids, distances, metadatas = results['ids'][0], results.get('distances'), results.get('metadatas')
    if distances is None or metadatas is None: return []
    dist_list, meta_list = distances[0], metadatas[0]
    for i in range(len(ids)):
        output.append({"id": ids[i], "distance": dist_list[i], "metadata": meta_list[i]})
    return output