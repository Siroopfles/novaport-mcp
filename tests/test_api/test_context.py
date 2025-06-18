import base64
import shutil
from pathlib import Path

import pytest
from conport.app_factory import create_app
from conport.db import models
from conport.db.database import get_db, run_migrations_for_workspace
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create the FastAPI app for the tests
app = create_app()

# Use a fixed test workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_context")

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
    # Reset the database for the tests
    db = TestingSessionLocal()
    try:
        db.query(models.ProductContext).delete()
        db.query(models.ActiveContext).delete()
        db.commit()
    finally:
        db.close()

    client = TestClient(app)
    yield client

    # Cleanup after the tests
    TestingSessionLocal.close_all()
    engine.dispose()

    if TEST_WORKSPACE_DIR.exists():
        try:
            shutil.rmtree(TEST_WORKSPACE_DIR)
        except PermissionError:
            import time
            time.sleep(1)  # Give Windows time to release handles
            shutil.rmtree(TEST_WORKSPACE_DIR)

def b64_encode(s: str) -> str:
    """Helper to encode paths for test URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def test_update_product_context(client: TestClient):
    """Test updating product context via full overwrite and patch."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)

    # 1. Start with empty context
    response_get_initial = client.get(f"/workspaces/{workspace_b64}/context/product")
    assert response_get_initial.status_code == 200
    assert response_get_initial.json()["content"] == {}

    # 2. Full overwrite with `content`
    new_content = {"project": "Nova", "version": 1}
    response_put = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"content": new_content}
    )
    assert response_put.status_code == 200
    assert response_put.json()["content"] == new_content

    # 3. Patch the content: update a key and add a new one
    patch_data = {"version": 2, "status": "alpha"}
    response_patch = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"patch_content": patch_data}
    )
    assert response_patch.status_code == 200
    expected_after_patch = {"project": "Nova", "version": 2, "status": "alpha"}
    assert response_patch.json()["content"] == expected_after_patch

    # 4. Patch the content to remove a key
    delete_patch = {"status": "__DELETE__"}
    response_delete_patch = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"patch_content": delete_patch}
    )
    assert response_delete_patch.status_code == 200
    expected_after_delete = {"project": "Nova", "version": 2}
    assert response_delete_patch.json()["content"] == expected_after_delete
