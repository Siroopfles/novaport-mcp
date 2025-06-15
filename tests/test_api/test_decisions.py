from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from conport.main import app
from conport.db.database import Base, get_db

# Gebruik een in-memory SQLite database voor tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Override de 'get_db' dependency voor de tests
def override_get_db():
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="module")
def client():
    # Maak de tabellen aan in de in-memory database
    Base.metadata.create_all(bind=engine)
    yield TestClient(app)
    # Ruim de tabellen op na de tests
    Base.metadata.drop_all(bind=engine)

def test_create_decision(client: TestClient):
    """Test het aanmaken van een nieuwe beslissing."""
    response = client.post(
        "/decisions/",
        json={"summary": "Use SQLAlchemy ORM", "rationale": "For robustness and type safety."}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["summary"] == "Use SQLAlchemy ORM"
    assert "id" in data

def test_read_decision(client: TestClient):
    """Test het ophalen van een specifieke beslissing."""
    # Eerst een beslissing aanmaken
    response = client.post(
        "/decisions/",
        json={"summary": "Test Read Decision", "tags": ["testing"]}
    )
    assert response.status_code == 201
    decision_id = response.json()["id"]

    # Nu ophalen
    response = client.get(f"/decisions/{decision_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == decision_id
    assert data["summary"] == "Test Read Decision"