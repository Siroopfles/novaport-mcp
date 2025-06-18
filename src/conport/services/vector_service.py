import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

import chromadb
from chromadb.api.client import Client
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from ..core import config as core_config

log = logging.getLogger(__name__)

_model: Optional[SentenceTransformer] = None
_chroma_clients: Dict[str, Client] = {}
_collections: Dict[str, chromadb.Collection] = {}

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(
            f"Loading sentence transformer model: {core_config.settings.EMBEDDING_MODEL_NAME}..."
        )
        _model = SentenceTransformer(core_config.settings.EMBEDDING_MODEL_NAME)
        log.info("Embedding model loaded.")
    return _model

# Constants for cleanup delays
CHROMA_CLEANUP_DELAY = 2.0
CHROMA_GC_DELAY = 0.5

def cleanup_chroma_client(workspace_id: str) -> None:
    """Closes the ChromaDB client for a specific workspace."""
    global _chroma_clients, _collections

    # Determine the db_path for the workspace
    db_path = str(
        Path(core_config.get_vector_db_path_for_workspace(workspace_id)).resolve()
    )
    log.info(
        f"Cleaning up ChromaDB client for workspace: {workspace_id} (db_path: {db_path})"
    )

    if db_path in _chroma_clients:
        try:
            client = _chroma_clients[db_path]

            # Reset all collections first
            for collection in client.list_collections():
                collection_name = collection.name
                log.info(
                    f"Cleaning up collection: {collection_name} (type: {type(collection_name)})"
                )

                # Delete all documents first
                if collection.count() > 0:
                    collection.delete(ids=collection.get()["ids"])
                # Then delete the collection itself
                client.delete_collection(name=collection_name)

            # Reset and close the client
            client.reset()

            # Selective cache clearing - only for the current workspace
            # This is crucial after a reset because all collections are invalid
            keys_to_remove = [
                key for key in _collections if key.startswith(workspace_id)
            ]
            for key in keys_to_remove:
                del _collections[key]
                log.debug(f"Removed collection from cache: {key}")
            log.info(
                f"Selectively removed {len(keys_to_remove)} collection(s) from cache for workspace: {workspace_id}"
            )

            import time
            time.sleep(CHROMA_CLEANUP_DELAY)  # Give Windows more time to release handles

            # Force garbage collection to free resources
            import gc
            gc.collect()
            time.sleep(CHROMA_GC_DELAY)  # Extra wait time after garbage collection

            del _chroma_clients[db_path]
            log.info(f"ChromaDB client successfully cleaned up for workspace: {workspace_id} (db_path: {db_path})")
        except Exception as e:
            log.error(f"Error cleaning up ChromaDB client for {workspace_id} (db_path: {db_path}): {e}")
            raise  # Propagate the error so tests fail on cleanup issues

def get_chroma_client(workspace_id: str) -> Client:
    """Initialize a ChromaDB client for a workspace with correctly formatted paths."""
    global _chroma_clients
    db_path = str(Path(core_config.get_vector_db_path_for_workspace(workspace_id)).resolve())

    if db_path not in _chroma_clients:
        log.info(f"Initializing ChromaDB client for workspace: {workspace_id} (db_path: {db_path})")

        client = cast(Client, chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        ))
        _chroma_clients[db_path] = client
        log.info(f"ChromaDB client initialized at {db_path}")
    return _chroma_clients[db_path]

def get_collection(
    workspace_id: str,
    collection_name: str = "conport_default"
) -> chromadb.Collection:
    """Retrieves a ChromaDB collection with robust error handling and cache management."""
    global _collections
    cache_key = f"{workspace_id}_{collection_name}"

    try:
        # Try from cache first
        if cache_key in _collections:
            try:
                # Test if the cached collection is still valid by calling the count() method
                _collections[cache_key].count()
                return _collections[cache_key]
            except Exception:
                # If the collection is invalid, remove from cache
                log.warning(
                    f"Invalid collection in cache for {cache_key}, will be recreated"
                )
                _collections.pop(cache_key, None)

        # If we get here, we need to create a new collection
        client = get_chroma_client(workspace_id)

        try:
            # Try to retrieve the collection directly first
            collection = client.get_collection(name=collection_name)
            log.info(f"Existing collection '{collection_name}' found for {workspace_id}")
        except Exception as e:
            # If the collection doesn't exist, create a new one
            log.info(f"Collection '{collection_name}' not found for {workspace_id}, creating: {str(e)}")
            collection = client.create_collection(name=collection_name)

        # Update the cache only if we have a working collection
        _collections[cache_key] = collection
        return collection

    except Exception as e:
        log.error(f"Error retrieving/creating collection for {workspace_id}: {str(e)}")
        raise

def generate_embedding(text: str) -> List[float]:
    model = get_embedding_model()
    return model.encode(text, convert_to_tensor=False).tolist()

def upsert_embedding(
    workspace_id: str,
    item_id: str,
    text_to_embed: str,
    metadata: Dict[str, Any]
) -> None:
    collection = get_collection(workspace_id)
    embedding = generate_embedding(text_to_embed)
    safe_metadata = {k: v for k, v in metadata.items() if isinstance(v, (str, int, float, bool))}
    collection.upsert(ids=[item_id], embeddings=[embedding], metadatas=[safe_metadata])  # type: ignore
    log.info(f"Upserted embedding for item {item_id} in workspace {workspace_id}")

def delete_embedding(workspace_id: str, item_id: str) -> None:
    collection = get_collection(workspace_id)
    try:
        collection.delete(ids=[item_id])
        log.info(f"Deleted embedding for item {item_id} in workspace {workspace_id}")
    except Exception as e:
        log.warning(f"Could not delete embedding for {item_id} in workspace {workspace_id} (may not have existed): {e}")

def search(
    workspace_id: str,
    query_text: str,
    top_k: int,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    collection = get_collection(workspace_id)
    query_embedding = generate_embedding(query_text)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k, where=filters)  # type: ignore

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
