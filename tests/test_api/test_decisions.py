import base64
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

# Use a fixed test-workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_decisions")


def get_test_db_url():
    """Generates the URL for the test database."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"


# Setup a test-specific database engine
engine = create_engine(get_test_db_url(), connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# IMPROVED SETUP: Run the real Alembic migrations on the test database.
# This ensures that the test schema (incl. FTS) is identical to production.
# We replace this with: Base.metadata.create_all(bind=engine)
db_path = Path(get_test_db_url().replace("sqlite:///", ""))
run_migrations_for_workspace(engine, db_path)


def override_get_db():
    """Override the 'get_db' dependency for the tests.
    This function ignores the workspace_id from the URL and always returns the test database.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


# Link the override to the 'get_db' dependency in the app.
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


def b64_encode(s: str) -> str:
    """Helper to encode paths for test URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()


def test_create_and_read_decision(client: TestClient):
    """Test creating, retrieving and deleting a decision."""
    # Use a dummy workspace path for the test. The override ensures
    # that the test database is used, but the URL must still be valid.
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)

    # 1. Create a decision
    response_create = client.post(
        f"/workspaces/{workspace_b64}/decisions/",
        json={
            "summary": "Use Pytest for testing",
            "rationale": "For structured and scalable tests.",
        },
    )
    assert response_create.status_code == 201, response_create.text
    create_data = response_create.json()
    assert create_data["summary"] == "Use Pytest for testing"
    assert "id" in create_data
    decision_id = create_data["id"]

    # 2. Retrieve the same decision
    response_read = client.get(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_read.status_code == 200, response_read.text
    read_data = response_read.json()
    assert read_data["id"] == decision_id
    assert read_data["summary"] == "Use Pytest for testing"

    # 3. Retrieve all decisions
    response_get_all = client.get(f"/workspaces/{workspace_b64}/decisions/")
    assert response_get_all.status_code == 200, response_get_all.text
    all_data = response_get_all.json()
    assert isinstance(all_data, list)
    assert len(all_data) >= 1
    assert any(d["id"] == decision_id for d in all_data)

    # 4. Delete the decision
    response_delete = client.delete(
        f"/workspaces/{workspace_b64}/decisions/{decision_id}"
    )
    assert response_delete.status_code == 204, response_delete.text

    # 5. Check if it was deleted
    response_read_after_delete = client.get(
        f"/workspaces/{workspace_b64}/decisions/{decision_id}"
    )
    assert (
        response_read_after_delete.status_code == 404
    ), response_read_after_delete.text
