import logging
from pathlib import Path
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

# Constanten voor cleanup delays
CHROMA_CLEANUP_DELAY = 2.0
CHROMA_GC_DELAY = 0.5

def cleanup_chroma_client(workspace_id: str):
    """Sluit de ChromaDB client voor een specifieke workspace."""
    global _chroma_clients, _collections
    
    # Bepaal het db_path voor de workspace
    db_path = str(Path(core_config.get_vector_db_path_for_workspace(workspace_id)).resolve())
    log.info(f"Cleaning up ChromaDB client voor workspace: {workspace_id} (db_path: {db_path})")
    
    if db_path in _chroma_clients:
        try:
            client = _chroma_clients[db_path]
            
            # Reset eerst alle collections
            for collection in client.list_collections():
                collection_name = collection.name
                log.info(f"Cleaning up collection: {collection_name} (type: {type(collection_name)})")
                
                # Verwijder eerst alle documenten
                if collection.count() > 0:
                    collection.delete(ids=collection.get()["ids"])
                # Verwijder dan de collectie zelf
                client.delete_collection(name=collection_name)
            
            # Reset en sluit de client
            client.reset()
            
            # Verwijder ALLE collection caches voor deze workspace
            # Dit is cruciaal na een reset omdat alle collections ongeldig zijn
            _collections.clear()  # Verwijder alle collection caches
            
            import time
            time.sleep(CHROMA_CLEANUP_DELAY)  # Geef Windows meer tijd om handles vrij te geven
            
            # Forceer garbage collection om resources vrij te geven
            import gc
            gc.collect()
            time.sleep(CHROMA_GC_DELAY)  # Extra wachttijd na garbage collection
            
            del _chroma_clients[db_path]
            log.info(f"ChromaDB client succesvol opgeruimd voor workspace: {workspace_id} (db_path: {db_path})")
        except Exception as e:
            log.error(f"Fout bij opruimen ChromaDB client voor {workspace_id} (db_path: {db_path}): {e}")
            raise  # Propagate de error zodat tests falen bij cleanup problemen

def get_chroma_client(workspace_id: str) -> Client:
    """Initialize een ChromaDB client voor een workspace met correct geformatteerde paden."""
    global _chroma_clients
    db_path = str(Path(core_config.get_vector_db_path_for_workspace(workspace_id)).resolve())
    
    if db_path not in _chroma_clients:
        log.info(f"Initialiseren van ChromaDB client voor workspace: {workspace_id} (db_path: {db_path})")
        
        client = cast(Client, chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        ))
        _chroma_clients[db_path] = client
        log.info(f"ChromaDB client geïnitialiseerd op {db_path}")
    return _chroma_clients[db_path]

def get_collection(workspace_id: str, collection_name: str = "conport_default") -> chromadb.Collection:
    """Haalt een ChromaDB collection op, met robuuste error handling en cache management."""
    global _collections
    cache_key = f"{workspace_id}_{collection_name}"

    try:
        # Probeer eerst uit de cache
        if cache_key in _collections:
            try:
                # Test of de cached collection nog geldig is
                _ = _collections[cache_key].count()
                return _collections[cache_key]
            except Exception:
                # Als de collection ongeldig is, verwijder uit cache
                log.warning(f"Ongeldige collection in cache voor {cache_key}, wordt opnieuw aangemaakt")
                _collections.pop(cache_key, None)

        # Als we hier komen, moeten we een nieuwe collection maken
        client = get_chroma_client(workspace_id)
        
        try:
            # Probeer eerst de collection direct op te halen
            collection = client.get_collection(name=collection_name)
            log.info(f"Bestaande collection '{collection_name}' gevonden voor {workspace_id}")
        except Exception as e:
            # Als de collection niet bestaat, maak een nieuwe aan
            log.info(f"Collection '{collection_name}' niet gevonden voor {workspace_id}, wordt aangemaakt: {str(e)}")
            collection = client.create_collection(name=collection_name)
        
        # Update de cache alleen als we een werkende collection hebben
        _collections[cache_key] = collection
        return collection
        
    except Exception as e:
        log.error(f"Fout bij ophalen/aanmaken collection voor {workspace_id}: {str(e)}")
        raise

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