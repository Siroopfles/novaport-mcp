from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import shutil
import base64

from conport.app_factory import create_app
from conport.db.database import get_db, run_migrations_for_workspace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Maak de FastAPI app aan voor de tests
app = create_app()

# Gebruik een vaste test-workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_batch")

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
    yield TestClient(app)
    if TEST_WORKSPACE_DIR.exists():
        shutil.rmtree(TEST_WORKSPACE_DIR)

def b64_encode(s: str) -> str:
    """Helper om paden te encoderen voor test-URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def test_batch_log_items_mixed_validity(client: TestClient):
    """Test batch logging met een mix van geldige en ongeldige items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # Mix van geldige en ongeldige beslissingen
    batch_request = {
        "item_type": "decision",
        "items": [
            # Geldig item 1
            {
                "summary": "Use TypeScript for frontend development",
                "rationale": "Better type safety and developer experience",
                "tags": ["frontend", "typescript"]
            },
            # Geldig item 2  
            {
                "summary": "Implement API versioning strategy",
                "rationale": "To maintain backward compatibility",
                "implementation_details": "Use URL path versioning like /api/v1/",
                "tags": ["api", "versioning"]
            },
            # Ongeldig item 1 - ontbrekende summary
            {
                "rationale": "This decision has no summary",
                "tags": ["invalid"]
            },
            # Geldig item 3
            {
                "summary": "Choose PostgreSQL as primary database",
                "rationale": "Proven reliability and feature set",
                "tags": ["database", "postgresql"]
            },
            # Ongeldig item 2 - summary is None
            {
                "summary": None,
                "rationale": "Summary is None",
                "tags": ["invalid"]
            }
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # Verifieer de response structuur
    assert "succeeded" in result
    assert "failed" in result
    assert "details" in result
    
    # Verifieer de counts
    assert result["succeeded"] == 3  # 3 geldige items
    assert result["failed"] == 2     # 2 ongeldige items
    
    # Verifieer dat de totale count klopt
    total_items = len(batch_request["items"])
    assert result["succeeded"] + result["failed"] == total_items

def test_batch_log_items_all_valid(client: TestClient):
    """Test batch logging met alleen geldige items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "progress", 
        "items": [
            {
                "status": "TODO",
                "description": "Implement user authentication"
            },
            {
                "status": "IN_PROGRESS", 
                "description": "Setup CI/CD pipeline"
            },
            {
                "status": "DONE",
                "description": "Project initialization"
            }
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # Alle items zouden succesvol moeten zijn
    assert result["succeeded"] == 3
    assert result["failed"] == 0

def test_batch_log_items_all_invalid(client: TestClient):
    """Test batch logging met alleen ongeldige items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "decision",
        "items": [
            # Ontbrekende summary
            {
                "rationale": "No summary provided"
            },
            # Lege summary  
            {
                "summary": "",
                "rationale": "Empty summary"
            },
            # Alleen tags, geen summary
            {
                "tags": ["test"]
            }
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # Alle items zouden moeten falen
    assert result["succeeded"] == 0
    assert result["failed"] == 3

def test_batch_log_items_custom_data(client: TestClient):
    """Test batch logging voor custom_data items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "custom_data",
        "items": [
            # Geldig custom_data item
            {
                "category": "ProjectGlossary",
                "key": "API",
                "value": "Application Programming Interface"
            },
            # Geldig custom_data item
            {
                "category": "ProjectGlossary", 
                "key": "CI/CD",
                "value": "Continuous Integration/Continuous Deployment"
            },
            # Ongeldig - ontbrekende category
            {
                "key": "InvalidItem",
                "value": "This item has no category"
            }
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # 2 geldige items, 1 ongeldig
    assert result["succeeded"] == 2
    assert result["failed"] == 1

def test_batch_log_items_system_patterns(client: TestClient):
    """Test batch logging voor system_pattern items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "system_pattern",
        "items": [
            # Geldig system_pattern
            {
                "name": "Repository Pattern",
                "description": "Data access abstraction pattern",
                "tags": ["architecture", "data-access"]
            },
            # Geldig system_pattern - minimaal
            {
                "name": "Singleton Pattern"
            },
            # Ongeldig - ontbrekende name
            {
                "description": "Pattern without a name",
                "tags": ["invalid"]
            }
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # 2 geldige items, 1 ongeldig
    assert result["succeeded"] == 2
    assert result["failed"] == 1

def test_batch_log_items_invalid_item_type(client: TestClient):
    """Test batch logging met ongeldig item_type."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "invalid_type",
        "items": [
            {"some": "data"}
        ]
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    # Dit zou een validation error moeten geven
    assert response.status_code == 422

def test_batch_log_items_empty_list(client: TestClient):
    """Test batch logging met lege items lijst."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "decision",
        "items": []
    }
    
    response = client.post(
        f"/workspaces/{workspace_b64}/batch/log-items",
        json=batch_request
    )
    
    assert response.status_code == 200, response.text
    result = response.json()
    
    # Geen items betekent 0 succeeded en 0 failed
    assert result["succeeded"] == 0
    assert result["failed"] == 0