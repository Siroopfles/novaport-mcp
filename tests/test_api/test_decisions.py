from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import shutil
import base64

# Corrigeer de import
from conport.app_factory import create_app
from conport.db.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Maak de FastAPI app aan voor de tests
app = create_app()

# Gebruik een in-memory SQLite database voor tests, maar we moeten de engine per workspace beheren
# Voor testen is het makkelijker om een vaste test-workspace te gebruiken.
TEST_WORKSPACE_DIR = Path("./test_workspace_decisions")

def get_test_db_url():
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{data_dir.resolve()}/conport.db"

# Setup een test-specifieke database engine
engine = create_engine(
    get_test_db_url(), connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Maak de tabellen aan voor de testsessie
Base.metadata.create_all(bind=engine)

def override_get_db(workspace_id_b64: str):
    """Override de 'get_db' dependency voor de tests."""
    # We negeren de workspace_id_b64 en gebruiken altijd de testdatabase.
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
    # Ruim de test-workspace op na alle tests in deze module.
    if TEST_WORKSPACE_DIR.exists():
        shutil.rmtree(TEST_WORKSPACE_DIR)

def b64_encode(s: str) -> str:
    """Helper om paden te encoderen voor test-URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def test_create_and_read_decision(client: TestClient):
    """Test het aanmaken en ophalen van een beslissing in een specifieke workspace."""
    # Gebruik een dummy workspace pad voor de test
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # 1. Maak een beslissing aan
    response_create = client.post(
        f"/workspaces/{workspace_b64}/decisions/",
        json={"summary": "Use Pytest for testing", "rationale": "For structured and scalable tests."}
    )
    assert response_create.status_code == 201
    create_data = response_create.json()
    assert create_data["summary"] == "Use Pytest for testing"
    assert "id" in create_data
    decision_id = create_data["id"]

    # 2. Haal dezelfde beslissing op
    response_read = client.get(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_read.status_code == 200
    read_data = response_read.json()
    assert read_data["id"] == decision_id
    assert read_data["summary"] == "Use Pytest for testing"

    # 3. Haal alle beslissingen op
    response_get_all = client.get(f"/workspaces/{workspace_b64}/decisions/")
    assert response_get_all.status_code == 200
    all_data = response_get_all.json()
    assert isinstance(all_data, list)
    assert len(all_data) >= 1  # Kan meer zijn als andere tests ook hebben geschreven
    assert any(d["id"] == decision_id for d in all_data)

    # 4. Verwijder de beslissing
    response_delete = client.delete(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_delete.status_code == 204
    
    # 5. Controleer of het verwijderd is
    response_read_after_delete = client.get(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_read_after_delete.status_code == 404