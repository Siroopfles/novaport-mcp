import logging
from typing import List, Dict, Any, Optional, cast
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.api.client import Client

from ..core import config as core_config

log = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None
_chroma_clients: Dict[str, Client] = {}
_collections: Dict[str, chromadb.Collection] = {}

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(f"Laden van sentence transformer model: {core_config.settings.EMBEDDING_MODEL_NAME}...")
        _model = SentenceTransformer(core_config.settings.EMBEDDING_MODEL_NAME)
        log.info("Embedding model geladen.")
    return _model

def get_chroma_client(workspace_id: str) -> Client:
    global _chroma_clients
    if workspace_id not in _chroma_clients:
        log.info(f"Initialiseren van ChromaDB client voor workspace: {workspace_id}")
        db_path = core_config.get_vector_db_path_for_workspace(workspace_id)
        
        client = cast(Client, chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(anonymized_telemetry=False)
        ))
        _chroma_clients[workspace_id] = client
        log.info(f"ChromaDB client geïnitialiseerd op {db_path}")
    return _chroma_clients[workspace_id]

def get_collection(workspace_id: str, collection_name: str = "conport_default") -> chromadb.Collection:
    global _collections
    cache_key = f"{workspace_id}_{collection_name}"

    if cache_key not in _collections:
        client = get_chroma_client(workspace_id)
        collection = client.get_or_create_collection(name=collection_name)
        _collections[cache_key] = collection
        
    return _collections[cache_key]

def generate_embedding(text: str) -> List[float]:
    model = get_embedding_model()
    return model.encode(text, convert_to_tensor=False).tolist()

def upsert_embedding(workspace_id: str, item_id: str, text_to_embed: str, metadata: Dict[str, Any]):
    collection = get_collection(workspace_id)
    embedding = generate_embedding(text_to_embed)
    safe_metadata = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
    collection.upsert(ids=[item_id], embeddings=[embedding], metadatas=[safe_metadata])
    log.info(f"Upserted embedding voor item {item_id} in workspace {workspace_id}")

def delete_embedding(workspace_id: str, item_id: str):
    collection = get_collection(workspace_id)
    try:
        collection.delete(ids=[item_id])
        log.info(f"Deleted embedding voor item {item_id} in workspace {workspace_id}")
    except Exception as e:
        log.warning(f"Kon embedding voor {item_id} niet verwijderen in workspace {workspace_id} (bestond mogelijk niet): {e}")

def search(workspace_id: str, query_text: str, top_k: int, filters: Optional[Dict] = None) -> List[Dict[str, Any]]:
    collection = get_collection(workspace_id)
    query_embedding = generate_embedding(query_text)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=filters)
    
    output = []
    if not results or not results.get('ids') or not results['ids'][0]:
        return []
        
    ids, distances, metadatas = results['ids'][0], results.get('distances'), results.get('metadatas')
    if distances is None or metadatas is None:
        return []
        
    dist_list, meta_list = distances[0], metadatas[0]
    for i in range(len(ids)):
        output.append({"id": ids[i], "distance": dist_list[i], "metadata": meta_list[i]})
    return output