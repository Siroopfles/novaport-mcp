from fastapi.testclient import TestClient
import pytest
from pathlib import Path
import shutil
import base64

from conport.app_factory import create_app
# Importeer run_migrations_for_workspace en get_db. We hebben Base hier niet meer nodig.
from conport.db.database import get_db, run_migrations_for_workspace
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Maak de FastAPI app aan voor de tests
app = create_app()

# Gebruik een vaste test-workspace.
TEST_WORKSPACE_DIR = Path("./test_workspace_decisions")

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

# VERBETERDE SETUP: Voer de echte Alembic migraties uit op de testdatabase.
# Dit zorgt ervoor dat het testschema (incl. FTS) identiek is aan productie.
# We vervangen hiermee: Base.metadata.create_all(bind=engine)
db_path = Path(get_test_db_url().replace("sqlite:///", ""))
run_migrations_for_workspace(engine, db_path)


def override_get_db():
    """
    Override de 'get_db' dependency voor de tests.
    Deze functie negeert de workspace_id uit de URL en geeft altijd de testdatabase terug.
    """
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Koppel de override aan de 'get_db' dependency in de app.
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
    """Test het aanmaken, ophalen en verwijderen van een beslissing."""
    # Gebruik een dummy workspace pad voor de test. De override zorgt ervoor
    # dat de testdatabase wordt gebruikt, maar de URL moet nog steeds geldig zijn.
    workspace_path = str(TEST_WORKSPACE_DIR.resolve())
    workspace_b64 = b64_encode(workspace_path)
    
    # 1. Maak een beslissing aan
    response_create = client.post(
        f"/workspaces/{workspace_b64}/decisions/",
        json={"summary": "Use Pytest for testing", "rationale": "For structured and scalable tests."}
    )
    assert response_create.status_code == 201, response_create.text
    create_data = response_create.json()
    assert create_data["summary"] == "Use Pytest for testing"
    assert "id" in create_data
    decision_id = create_data["id"]

    # 2. Haal dezelfde beslissing op
    response_read = client.get(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_read.status_code == 200, response_read.text
    read_data = response_read.json()
    assert read_data["id"] == decision_id
    assert read_data["summary"] == "Use Pytest for testing"

    # 3. Haal alle beslissingen op
    response_get_all = client.get(f"/workspaces/{workspace_b64}/decisions/")
    assert response_get_all.status_code == 200, response_get_all.text
    all_data = response_get_all.json()
    assert isinstance(all_data, list)
    assert len(all_data) >= 1
    assert any(d["id"] == decision_id for d in all_data)

    # 4. Verwijder de beslissing
    response_delete = client.delete(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_delete.status_code == 204, response_delete.text
    
    # 5. Controleer of het verwijderd is
    response_read_after_delete = client.get(f"/workspaces/{workspace_b64}/decisions/{decision_id}")
    assert response_read_after_delete.status_code == 404, response_read_after_delete.text