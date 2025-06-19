import base64
import gc
import tempfile
import time
from pathlib import Path

import pytest
from conport.app_factory import create_app
from conport.db.database import get_db, run_migrations_for_workspace
from conport.services import vector_service
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .test_utils import robust_rmtree

# Create the FastAPI app for the tests
app = create_app()

# Use a fixed test workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_search")


def get_test_db_url():
    """Generates the URL for the test database."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"


# Set up a test-specific database engine
engine = create_engine(get_test_db_url(), connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_path = Path(get_test_db_url().replace("sqlite:///", ""))
run_migrations_for_workspace(engine, db_path)


def override_get_db():
    """Override the 'get_db' dependency for the tests."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client():
    """Create a TestClient that uses the overridden dependency."""
    client = TestClient(app)
    yield client

    # Cleanup database resources
    TestingSessionLocal.close_all()
    engine.dispose()

    # Clean up ChromaDB client for the test workspace
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    vector_service.cleanup_chroma_client(workspace_path)

    # Use robust rmtree for cleanup
    robust_rmtree(TEST_WORKSPACE_DIR)


@pytest.fixture(scope="function")
def temp_chroma_db():
    """Set up a temporary ChromaDB for the tests."""
    # Create a temporary directory for ChromaDB
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)

    # Override the vector db path function
    original_get_vector_db_path = (
        vector_service.core_config.get_vector_db_path_for_workspace
    )

    def mock_get_vector_db_path(workspace_id: str) -> str:
        # Use Path for correct Windows path handling
        return str(Path(temp_path) / f"chroma_{Path(workspace_id).name}")

    vector_service.core_config.get_vector_db_path_for_workspace = (
        mock_get_vector_db_path
    )

    yield temp_path

    # Cleanup ChromaDB client with the correct mocked path
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    mocked_db_path = mock_get_vector_db_path(workspace_path)
    if mocked_db_path in vector_service._chroma_clients:
        client_to_reset = vector_service._chroma_clients[mocked_db_path]
        # Reset the client
        try:
            client_to_reset.reset()
            collection_name = vector_service.core_config.CHROMA_DEFAULT_COLLECTION_NAME
            client_to_reset.delete_collection(name=collection_name)
        except Exception:
            pass  # Ignore errors during collection delete
        del vector_service._chroma_clients[mocked_db_path]

    # Wait for garbage collection
    time.sleep(vector_service.CHROMA_CLEANUP_DELAY)
    gc.collect()
    time.sleep(vector_service.CHROMA_GC_DELAY)

    # Restore the original function
    vector_service.core_config.get_vector_db_path_for_workspace = (
        original_get_vector_db_path
    )

    # Use robust rmtree for cleanup
    robust_rmtree(temp_dir)


def b64_encode(s: str) -> str:
    """Helper to encode paths for test URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_semantic_search_with_data(client: TestClient, temp_chroma_db):
    """Test semantic search functionality with test data."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)

    # Add some test data to the vector database
    test_items = [
        {
            "id": "test_item_1",
            "text": "This is about Python programming and machine learning algorithms",
            "metadata": {
                "type": "document",
                "category": "programming",
                "language": "python",
            },
        },
        {
            "id": "test_item_2",
            "text": "JavaScript frontend development with React and Vue frameworks",
            "metadata": {
                "type": "document",
                "category": "programming",
                "language": "javascript",
            },
        },
        {
            "id": "test_item_3",
            "text": "Database design patterns and SQL optimization techniques",
            "metadata": {"type": "document", "category": "database", "language": "sql"},
        },
    ]

    # Add embeddings to the vector database
    for item in test_items:
        vector_service.upsert_embedding(
            workspace_id=workspace_path,
            item_id=item["id"],
            text_to_embed=item["text"],
            metadata=item["metadata"],
        )

    # Test 1: Basic semantic search
    search_request = {"query_text": "Python machine learning", "top_k": 3}

    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", json=search_request
    )

    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0

    # The first result should be the most relevant (Python/ML)
    first_result = results[0]
    assert "id" in first_result
    assert "distance" in first_result
    assert "metadata" in first_result
    assert first_result["id"] == "test_item_1"

    # Test 2: Search with filters
    search_request_with_filter = {
        "query_text": "programming",
        "top_k": 2,
        "filters": {"category": "programming"},
    }

    response_filtered = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", json=search_request_with_filter
    )

    assert response_filtered.status_code == 200, response_filtered.text
    filtered_results = response_filtered.json()
    assert isinstance(filtered_results, list)
    assert len(filtered_results) == 2

    # All results should have the 'programming' category
    for result in filtered_results:
        assert result["metadata"]["category"] == "programming"


def test_semantic_search_empty_database(client: TestClient, temp_chroma_db):
    """Test semantic search on an empty database."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)

    search_request = {"query_text": "test query", "top_k": 5}

    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", json=search_request
    )

    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 0


def test_semantic_search_invalid_query(client: TestClient, temp_chroma_db):
    """Test semantic search with invalid query parameters."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)

    # Test with empty query_text
    invalid_request = {"query_text": "", "top_k": 5}

    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", json=invalid_request
    )

    assert response.status_code == 422  # Pydantic validation error

    # Test with too large top_k
    invalid_request_2 = {"query_text": "test query", "top_k": 100}  # Max is 25

    response_2 = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", json=invalid_request_2
    )

    assert response_2.status_code == 422  # Pydantic validation error
