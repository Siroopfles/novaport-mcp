from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import shutil
import base64
import tempfile

from conport.app_factory import create_app
from conport.db.database import get_db, run_migrations_for_workspace
from conport.services import vector_service
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Maak de FastAPI app aan voor de tests
app = create_app()

# Gebruik een vaste test-workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_search")

def get_test_db_url():
    """Genereert de URL voor de testdatabase."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"

# Setup een test-specifieke database engine
engine = create_engine(
    get_test_db_url(), connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_path = Path(get_test_db_url().replace("sqlite:///", ""))
run_migrations_for_workspace(engine, db_path)


def override_get_db():
    """
    Override de 'get_db' dependency voor de tests.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    """Create een TestClient die de overriden dependency gebruikt."""
    client = TestClient(app)
    yield client
    
    # Cleanup database resources
    TestingSessionLocal.close_all()
    engine.dispose()
    
    # Clean up ChromaDB client voor de test workspace
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    vector_service.cleanup_chroma_client(workspace_path)
    
    # Verwijder test directories
    if TEST_WORKSPACE_DIR.exists():
        try:
            shutil.rmtree(TEST_WORKSPACE_DIR)
        except PermissionError:
            import time
            time.sleep(1)  # Geef Windows tijd om handles vrij te geven
            shutil.rmtree(TEST_WORKSPACE_DIR)

@pytest.fixture(scope="module")
def temp_chroma_db():
    """Setup een tijdelijke ChromaDB voor de tests."""
    # Maak een tijdelijke directory voor ChromaDB
    temp_dir = tempfile.mkdtemp()
    temp_path = Path(temp_dir)
    
    # Override de vector db path functie
    original_get_vector_db_path = vector_service.core_config.get_vector_db_path_for_workspace
    
    def mock_get_vector_db_path(workspace_id: str) -> str:
        # Gebruik Path voor correcte Windows pad handling
        return str(Path(temp_path) / f"chroma_{Path(workspace_id).name}")
    
    vector_service.core_config.get_vector_db_path_for_workspace = mock_get_vector_db_path
    
    yield temp_path
    
    # Cleanup en wacht even voor Windows bestandshandles
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    vector_service.cleanup_chroma_client(workspace_path)
    
    # Herstel de originele functie
    vector_service.core_config.get_vector_db_path_for_workspace = original_get_vector_db_path
    
    # Ruim de tijdelijke directory op met retry
    try:
        shutil.rmtree(temp_dir, ignore_errors=True)
    except PermissionError:
        import time
        time.sleep(1)  # Geef Windows tijd om handles vrij te geven
        shutil.rmtree(temp_dir, ignore_errors=True)

def b64_encode(s: str) -> str:
    """Helper om paden te encoderen voor test-URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def test_semantic_search_with_data(client: TestClient, temp_chroma_db):
    """Test semantic search functionaliteit met test data."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # Voeg wat test data toe aan de vector database
    test_items = [
        {
            "id": "test_item_1",
            "text": "This is about Python programming and machine learning algorithms",
            "metadata": {"type": "document", "category": "programming", "language": "python"}
        },
        {
            "id": "test_item_2", 
            "text": "JavaScript frontend development with React and Vue frameworks",
            "metadata": {"type": "document", "category": "programming", "language": "javascript"}
        },
        {
            "id": "test_item_3",
            "text": "Database design patterns and SQL optimization techniques", 
            "metadata": {"type": "document", "category": "database", "language": "sql"}
        }
    ]
    
    # Voeg embeddings toe aan de vector database
    for item in test_items:
        vector_service.upsert_embedding(
            workspace_id=workspace_path,
            item_id=item["id"],
            text_to_embed=item["text"],
            metadata=item["metadata"]
        )
    
    # Test 1: Basis semantic search
    search_request = {
        "query_text": "Python machine learning",
        "top_k": 3
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic",
        json=search_request
    )
    
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert len(results) > 0
    
    # Het eerste resultaat zou het meest relevant moeten zijn (Python/ML)
    first_result = results[0]
    assert "id" in first_result
    assert "distance" in first_result
    assert "metadata" in first_result
    assert first_result["id"] == "test_item_1"
    
    # Test 2: Search met filters
    search_request_with_filter = {
        "query_text": "programming",
        "top_k": 2,
        "filters": {"category": "programming"}
    }
    
    response_filtered = client.post(
        f"/workspaces/{workspace_b64}/search/semantic",
        json=search_request_with_filter
    )
    
    assert response_filtered.status_code == 200, response_filtered.text
    filtered_results = response_filtered.json()
    assert isinstance(filtered_results, list)
    assert len(filtered_results) == 2
    
    # Alle resultaten zouden de 'programming' category moeten hebben
    for result in filtered_results:
        assert result["metadata"]["category"] == "programming"

def test_semantic_search_empty_database(client: TestClient, temp_chroma_db):
    """Test semantic search op een lege database."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    search_request = {
        "query_text": "test query",
        "top_k": 5
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic", 
        json=search_request
    )
    
    assert response.status_code == 200, response.text
    results = response.json()
    assert isinstance(results, list)
    assert len(results) == 0

def test_semantic_search_invalid_query(client: TestClient, temp_chroma_db):
    """Test semantic search met ongeldige query parameters."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # Test met lege query_text
    invalid_request = {
        "query_text": "",
        "top_k": 5
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/search/semantic",
        json=invalid_request
    )
    
    assert response.status_code == 422  # Pydantic validation error
    
    # Test met te grote top_k
    invalid_request_2 = {
        "query_text": "test query",
        "top_k": 100  # Max is 25
    }
    
    response_2 = client.post(
        f"/workspaces/{workspace_b64}/search/semantic",
        json=invalid_request_2
    )
    
    assert response_2.status_code == 422  # Pydantic validation error