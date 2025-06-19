"""Tests voor vector_service module voor volledige coverage."""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.novaport_mcp.services import vector_service


class TestVectorServiceEmbedding:
    """Test embedding gerelateerde functies."""

    def test_get_embedding_model_singleton(self):
        """Test dat get_embedding_model een singleton pattern gebruikt."""
        # Reset de global _model voor de test
        vector_service._model = None
        
        with patch('src.novaport_mcp.services.vector_service.SentenceTransformer') as mock_transformer:
            mock_model = Mock()
            mock_transformer.return_value = mock_model
            
            # Eerste aanroep
            result1 = vector_service.get_embedding_model()
            
            # Tweede aanroep
            result2 = vector_service.get_embedding_model()
            
            # Moet hetzelfde object zijn
            assert result1 is result2
            # SentenceTransformer moet maar één keer aangeroepen worden
            mock_transformer.assert_called_once()

    def test_generate_embedding(self):
        """Test generate_embedding functie."""
        with patch('src.novaport_mcp.services.vector_service.get_embedding_model') as mock_get_model:
            mock_model = Mock()
            mock_encoded = Mock()
            mock_encoded.tolist.return_value = [0.1, 0.2, 0.3]
            mock_model.encode.return_value = mock_encoded
            mock_get_model.return_value = mock_model
            
            result = vector_service.generate_embedding("test text")
            
            assert result == [0.1, 0.2, 0.3]
            mock_model.encode.assert_called_once_with("test text", convert_to_tensor=False)


class TestVectorServiceChromaClient:
    """Test ChromaDB client gerelateerde functies."""

    def setUp(self):
        """Setup voor elke test."""
        # Clear global caches
        vector_service._chroma_clients.clear()
        vector_service._collections.clear()

    def test_get_chroma_client_creates_new_client(self):
        """Test dat get_chroma_client een nieuwe client aanmaakt."""
        self.setUp()
        
        workspace_id = "test_workspace"
        
        with patch('src.novaport_mcp.services.vector_service.Path') as mock_path:
            with patch('src.novaport_mcp.services.vector_service.core_config.get_vector_db_path_for_workspace') as mock_get_path:
                with patch('src.novaport_mcp.services.vector_service.chromadb.PersistentClient') as mock_client:
                    mock_path_obj = Mock()
                    mock_path_obj.resolve.return_value = "/test/path"
                    mock_path.return_value = mock_path_obj
                    mock_get_path.return_value = "/test/path"
                    
                    mock_client_instance = Mock()
                    mock_client.return_value = mock_client_instance
                    
                    result = vector_service.get_chroma_client(workspace_id)
                    
                    assert result is mock_client_instance
                    mock_client.assert_called_once()

    def test_get_chroma_client_returns_cached_client(self):
        """Test dat get_chroma_client een cached client retourneert."""
        self.setUp()
        
        workspace_id = "test_workspace"
        mock_client = Mock()
        
        # Set up cache manually
        vector_service._chroma_clients["/test/path"] = mock_client
        
        with patch('src.novaport_mcp.services.vector_service.Path') as mock_path:
            with patch('src.novaport_mcp.services.vector_service.core_config.get_vector_db_path_for_workspace') as mock_get_path:
                mock_path_obj = Mock()
                mock_path_obj.resolve.return_value = "/test/path"
                mock_path.return_value = mock_path_obj
                mock_get_path.return_value = "/test/path"
                
                result = vector_service.get_chroma_client(workspace_id)
                
                assert result is mock_client

    def test_cleanup_chroma_client_success(self):
        """Test succesvolle cleanup van chroma client."""
        self.setUp()
        
        workspace_id = "test_workspace"
        db_path = "/test/path"
        
        # Setup mock client
        mock_client = Mock()
        mock_collection = Mock()
        mock_collection.name = "test_collection"
        mock_collection.count.return_value = 5
        mock_collection.get.return_value = {"ids": ["1", "2", "3"]}
        mock_client.list_collections.return_value = [mock_collection]
        
        vector_service._chroma_clients[db_path] = mock_client
        vector_service._collections["test_workspace_collection"] = mock_collection
        
        with patch('src.novaport_mcp.services.vector_service.Path') as mock_path:
            with patch('src.novaport_mcp.services.vector_service.core_config.get_vector_db_path_for_workspace') as mock_get_path:
                with patch('time.sleep'):  # Mock sleep to speed up test
                    with patch('gc.collect'):  # Mock garbage collection
                        mock_path_obj = Mock()
                        mock_path_obj.resolve.return_value = db_path
                        mock_path.return_value = mock_path_obj
                        mock_get_path.return_value = db_path
                        
                        vector_service.cleanup_chroma_client(workspace_id)
                        
                        # Verify cleanup happened
                        mock_collection.delete.assert_called_once_with(ids=["1", "2", "3"])
                        mock_client.delete_collection.assert_called_once_with(name="test_collection")
                        mock_client.reset.assert_called_once()
                        
                        # Verify client removed from cache
                        assert db_path not in vector_service._chroma_clients

    def test_cleanup_chroma_client_with_error(self):
        """Test cleanup met error."""
        self.setUp()
        
        workspace_id = "test_workspace"
        db_path = "/test/path"
        
        # Setup mock client that raises error
        mock_client = Mock()
        mock_client.list_collections.side_effect = Exception("Test error")
        
        vector_service._chroma_clients[db_path] = mock_client
        
        with patch('src.novaport_mcp.services.vector_service.Path') as mock_path:
            with patch('src.novaport_mcp.services.vector_service.core_config.get_vector_db_path_for_workspace') as mock_get_path:
                mock_path_obj = Mock()
                mock_path_obj.resolve.return_value = db_path
                mock_path.return_value = mock_path_obj
                mock_get_path.return_value = db_path
                
                with pytest.raises(Exception, match="Test error"):
                    vector_service.cleanup_chroma_client(workspace_id)


class TestVectorServiceCollection:
    """Test collection gerelateerde functies."""

    def setUp(self):
        """Setup voor elke test."""
        vector_service._chroma_clients.clear()
        vector_service._collections.clear()

    def test_get_collection_from_cache(self):
        """Test get_collection van cache."""
        self.setUp()
        
        workspace_id = "test_workspace"
        collection_name = "test_collection"
        cache_key = f"{workspace_id}_{collection_name}"
        
        mock_collection = Mock()
        mock_collection.count.return_value = 10  # Valid collection
        
        vector_service._collections[cache_key] = mock_collection
        
        result = vector_service.get_collection(workspace_id, collection_name)
        
        assert result is mock_collection
        mock_collection.count.assert_called_once()

    def test_get_collection_invalid_cache(self):
        """Test get_collection met invalide cache."""
        self.setUp()
        
        workspace_id = "test_workspace"
        collection_name = "test_collection"
        cache_key = f"{workspace_id}_{collection_name}"
        
        # Mock invalid collection in cache
        mock_invalid_collection = Mock()
        mock_invalid_collection.count.side_effect = Exception("Invalid collection")
        
        vector_service._collections[cache_key] = mock_invalid_collection
        
        with patch('src.novaport_mcp.services.vector_service.get_chroma_client') as mock_get_client:
            mock_client = Mock()
            mock_new_collection = Mock()
            mock_client.get_collection.return_value = mock_new_collection
            mock_get_client.return_value = mock_client
            
            result = vector_service.get_collection(workspace_id, collection_name)
            
            assert result is mock_new_collection
            # Should have removed invalid collection from cache
            assert cache_key in vector_service._collections
            assert vector_service._collections[cache_key] is mock_new_collection

    def test_get_collection_create_new(self):
        """Test get_collection maakt nieuwe collection aan."""
        self.setUp()
        
        workspace_id = "test_workspace"
        collection_name = "test_collection"
        
        with patch('src.novaport_mcp.services.vector_service.get_chroma_client') as mock_get_client:
            mock_client = Mock()
            mock_client.get_collection.side_effect = Exception("Collection not found")
            
            mock_new_collection = Mock()
            mock_client.create_collection.return_value = mock_new_collection
            mock_get_client.return_value = mock_client
            
            result = vector_service.get_collection(workspace_id, collection_name)
            
            assert result is mock_new_collection
            mock_client.get_collection.assert_called_once_with(name=collection_name)
            mock_client.create_collection.assert_called_once_with(name=collection_name)

    def test_get_collection_error_handling(self):
        """Test get_collection error handling."""
        self.setUp()
        
        workspace_id = "test_workspace"
        
        with patch('src.novaport_mcp.services.vector_service.get_chroma_client') as mock_get_client:
            mock_get_client.side_effect = Exception("Client error")
            
            with pytest.raises(Exception, match="Client error"):
                vector_service.get_collection(workspace_id)


class TestVectorServiceOperations:
    """Test vector operaties (upsert, delete, search)."""

    def test_upsert_embedding(self):
        """Test upsert_embedding functie."""
        workspace_id = "test_workspace"
        item_id = "test_item"
        text = "test text"
        metadata = {"type": "test", "valid": True, "invalid": None}
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            with patch('src.novaport_mcp.services.vector_service.generate_embedding') as mock_generate:
                mock_collection = Mock()
                mock_get_collection.return_value = mock_collection
                mock_generate.return_value = [0.1, 0.2, 0.3]
                
                vector_service.upsert_embedding(workspace_id, item_id, text, metadata)
                
                mock_get_collection.assert_called_once_with(workspace_id)
                mock_generate.assert_called_once_with(text)
                
                # Should filter out invalid metadata
                expected_metadata = {"type": "test", "valid": True}
                mock_collection.upsert.assert_called_once_with(
                    ids=[item_id],
                    embeddings=[[0.1, 0.2, 0.3]],
                    metadatas=[expected_metadata]
                )

    def test_delete_embedding_success(self):
        """Test delete_embedding success."""
        workspace_id = "test_workspace"
        item_id = "test_item"
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_get_collection.return_value = mock_collection
            
            vector_service.delete_embedding(workspace_id, item_id)
            
            mock_get_collection.assert_called_once_with(workspace_id)
            mock_collection.delete.assert_called_once_with(ids=[item_id])

    def test_delete_embedding_with_error(self):
        """Test delete_embedding met error (warning logged)."""
        workspace_id = "test_workspace"
        item_id = "test_item"
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            mock_collection = Mock()
            mock_collection.delete.side_effect = Exception("Delete error")
            mock_get_collection.return_value = mock_collection
            
            # Should not raise, but log warning
            vector_service.delete_embedding(workspace_id, item_id)
            
            mock_collection.delete.assert_called_once_with(ids=[item_id])

    def test_search_with_results(self):
        """Test search functie met resultaten."""
        workspace_id = "test_workspace"
        query_text = "test query"
        top_k = 5
        filters = {"type": "test"}
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            with patch('src.novaport_mcp.services.vector_service.generate_embedding') as mock_generate:
                mock_collection = Mock()
                mock_get_collection.return_value = mock_collection
                mock_generate.return_value = [0.1, 0.2, 0.3]
                
                # Mock search results
                mock_results = {
                    "ids": [["item1", "item2"]],
                    "distances": [[0.1, 0.2]],
                    "metadatas": [[{"type": "test1"}, {"type": "test2"}]]
                }
                mock_collection.query.return_value = mock_results
                
                result = vector_service.search(workspace_id, query_text, top_k, filters)
                
                mock_get_collection.assert_called_once_with(workspace_id)
                mock_generate.assert_called_once_with(query_text)
                mock_collection.query.assert_called_once_with(
                    query_embeddings=[[0.1, 0.2, 0.3]],
                    n_results=top_k,
                    where=filters
                )
                
                expected_result = [
                    {"id": "item1", "distance": 0.1, "metadata": {"type": "test1"}},
                    {"id": "item2", "distance": 0.2, "metadata": {"type": "test2"}}
                ]
                assert result == expected_result

    def test_search_no_results(self):
        """Test search zonder resultaten."""
        workspace_id = "test_workspace"
        query_text = "test query"
        top_k = 5
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            with patch('src.novaport_mcp.services.vector_service.generate_embedding') as mock_generate:
                mock_collection = Mock()
                mock_get_collection.return_value = mock_collection
                mock_generate.return_value = [0.1, 0.2, 0.3]
                
                # Mock empty results
                mock_results = {
                    "ids": [[]],
                    "distances": None,
                    "metadatas": None
                }
                mock_collection.query.return_value = mock_results
                
                result = vector_service.search(workspace_id, query_text, top_k)
                
                assert result == []

    def test_search_missing_data_fields(self):
        """Test search met ontbrekende data velden."""
        workspace_id = "test_workspace"
        query_text = "test query"
        top_k = 5
        
        with patch('src.novaport_mcp.services.vector_service.get_collection') as mock_get_collection:
            with patch('src.novaport_mcp.services.vector_service.generate_embedding') as mock_generate:
                mock_collection = Mock()
                mock_get_collection.return_value = mock_collection
                mock_generate.return_value = [0.1, 0.2, 0.3]
                
                # Mock results with missing distances or metadatas
                mock_results = {
                    "ids": [["item1", "item2"]],
                    "distances": None,  # Missing distances
                    "metadatas": [[{"type": "test1"}, {"type": "test2"}]]
                }
                mock_collection.query.return_value = mock_results
                
                result = vector_service.search(workspace_id, query_text, top_k)
                
                assert result == []


class TestVectorServiceConstants:
    """Test constanten en module-level variabelen."""

    def test_cleanup_delay_constants(self):
        """Test dat cleanup delay constanten gedefinieerd zijn."""
        assert vector_service.CHROMA_CLEANUP_DELAY == 2.0
        assert vector_service.CHROMA_GC_DELAY == 0.5

    def test_global_variables_initialization(self):
        """Test dat globale variabelen correct geïnitialiseerd zijn."""
        # Deze zijn dictionaries die tijdens runtime gevuld worden
        assert isinstance(vector_service._chroma_clients, dict)
        assert isinstance(vector_service._collections, dict)