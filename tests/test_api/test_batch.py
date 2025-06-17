import base64
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from conport.app_factory import create_app
from conport.db.database import get_db, run_migrations_for_workspace
from conport.services import vector_service
from .test_utils import robust_rmtree
from conport.db.models import SystemPattern, Decision, ProgressEntry, CustomData
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create the FastAPI app for the tests
app = create_app()

# Use a fixed test workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_batch")

def get_test_db_url():
    """Generates the URL for the test database."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"

# Set up a test-specific database engine
engine = create_engine(
    get_test_db_url(), connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

db_path = Path(get_test_db_url().replace("sqlite:///", ""))
run_migrations_for_workspace(engine, db_path)


def override_get_db():
    """
    Override the 'get_db' dependency for the tests.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def clean_db_session():
    """Create a clean database session for each test."""
    db = TestingSessionLocal()
    try:
        # Delete all rows from the tables
        db.query(SystemPattern).delete()
        db.query(Decision).delete()
        db.query(ProgressEntry).delete()
        db.query(CustomData).delete()
        db.commit()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="module")
def client():
    """Create a TestClient that uses the overridden dependency."""
    client = TestClient(app)
    yield client
    
    # Clean up ChromaDB client for the test workspace
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    vector_service.cleanup_chroma_client(workspace_path)
    
    # Use robust rmtree for cleanup
    robust_rmtree(TEST_WORKSPACE_DIR)

def b64_encode(s: str) -> str:
    """Helper to encode paths for test URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def test_batch_log_items_mixed_validity(client: TestClient):
    """Test batch logging with a mix of valid and invalid items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # Mix of valid and invalid decisions
    batch_request = {
        "item_type": "decision",
        "items": [
            # Valid item 1
            {
                "summary": "Use TypeScript for frontend development",
                "rationale": "Better type safety and developer experience",
                "tags": ["frontend", "typescript"]
            },
            # Valid item 2
            {
                "summary": "Implement API versioning strategy",
                "rationale": "To maintain backward compatibility",
                "implementation_details": "Use URL path versioning like /api/v1/",
                "tags": ["api", "versioning"]
            },
            # Invalid item 1 - missing summary
            {
                "rationale": "This decision has no summary",
                "tags": ["invalid"]
            },
            # Valid item 3
            {
                "summary": "Choose PostgreSQL as primary database",
                "rationale": "Proven reliability and feature set",
                "tags": ["database", "postgresql"]
            },
            # Invalid item 2 - summary is None
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
    
    # Verify the response structure
    assert "succeeded" in result
    assert "failed" in result
    assert "details" in result
    
    # Verify the counts
    assert result["succeeded"] == 3  # 3 valid items
    assert result["failed"] == 2     # 2 invalid items
    
    # Verify that the total count is correct
    total_items = len(batch_request["items"])
    assert result["succeeded"] + result["failed"] == total_items

def test_batch_log_items_all_valid(client: TestClient):
    """Test batch logging with only valid items."""
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
    
    # All items should be successful
    assert result["succeeded"] == 3
    assert result["failed"] == 0

def test_batch_log_items_all_invalid(client: TestClient):
    """Test batch logging with only invalid items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "decision",
        "items": [
            # Missing summary
            {
                "rationale": "No summary provided"
            },
            # Empty summary
            {
                "summary": "",
                "rationale": "Empty summary"
            },
            # Only tags, no summary
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
    
    # All items should fail
    assert result["succeeded"] == 0
    assert result["failed"] == 3

def test_batch_log_items_custom_data(client: TestClient):
    """Test batch logging for custom_data items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "custom_data",
        "items": [
            # Valid custom_data item
            {
                "category": "ProjectGlossary",
                "key": "API",
                "value": "Application Programming Interface"
            },
            # Valid custom_data item
            {
                "category": "ProjectGlossary",
                "key": "CI/CD",
                "value": "Continuous Integration/Continuous Deployment"
            },
            # Invalid - missing category
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
    
    # 2 valid items, 1 invalid
    assert result["succeeded"] == 2
    assert result["failed"] == 1

def test_batch_log_items_system_patterns(client: TestClient, clean_db_session):
    """Test batch logging for system_pattern items."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    batch_request = {
        "item_type": "system_pattern",
        "items": [
            # Valid system_pattern
            {
                "name": "Repository Pattern",
                "description": "Data access abstraction pattern",
                "tags": ["architecture", "data-access"]
            },
            # Valid system_pattern - minimal
            {
                "name": "Singleton Pattern"
            },
            # Invalid - missing name
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
    
    # 2 valid items, 1 invalid
    assert result["succeeded"] == 2
    assert result["failed"] == 1

def test_batch_log_items_invalid_item_type(client: TestClient):
    """Test batch logging with invalid item_type."""
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
    
    # This should give a validation error
    assert response.status_code == 422

def test_batch_log_items_empty_list(client: TestClient):
    """Test batch logging with empty items list."""
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
    
    # No items means 0 succeeded and 0 failed
    assert result["succeeded"] == 0
    assert result["failed"] == 0