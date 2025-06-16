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
TEST_WORKSPACE_DIR = Path("./test_workspace_context")

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

def test_update_product_context(client: TestClient):
    """Test het updaten van product context via full overwrite en patch."""
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # 1. Start met een leeg context
    response_get_initial = client.get(f"/workspaces/{workspace_b64}/context/product")
    assert response_get_initial.status_code == 200
    assert response_get_initial.json()["content"] == {}

    # 2. Volledige overwrite met `content`
    new_content = {"project": "Nova", "version": 1}
    response_put = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"content": new_content}
    )
    assert response_put.status_code == 200
    assert response_put.json()["content"] == new_content

    # 3. Patch de content: update een key en voeg een nieuwe toe
    patch_data = {"version": 2, "status": "alpha"}
    response_patch = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"patch_content": patch_data}
    )
    assert response_patch.status_code == 200
    expected_after_patch = {"project": "Nova", "version": 2, "status": "alpha"}
    assert response_patch.json()["content"] == expected_after_patch

    # 4. Patch de content om een key te verwijderen
    delete_patch = {"status": "__DELETE__"}
    response_delete_patch = client.put(
        f"/workspaces/{workspace_b64}/context/product",
        json={"patch_content": delete_patch}
    )
    assert response_delete_patch.status_code == 200
    expected_after_delete = {"project": "Nova", "version": 2}
    assert response_delete_patch.json()["content"] == expected_after_delete