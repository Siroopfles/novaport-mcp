import base64
import datetime
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from conport.app_factory import create_app
from conport.db.database import get_db, run_migrations_for_workspace
from conport.db import models
from conport.services import vector_service
from .test_utils import robust_rmtree

# Maak de FastAPI app aan voor de tests
app = create_app()

# Gebruik een vaste test-workspace voor history tests.
TEST_WORKSPACE_DIR = Path("./test_workspace_history_extended")

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

# Voer de echte Alembic migraties uit op de testdatabase
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
    
    # Gebruik robuuste rmtree voor cleanup
    robust_rmtree(TEST_WORKSPACE_DIR)

@pytest.fixture
def db_session():
    """Create een database sessie voor directe database operaties."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def b64_encode(s: str) -> str:
    """Helper om paden te encoderen voor test-URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def create_test_history_records(db_session, item_type="product_context", count=3):
    """Helper functie om test history records aan te maken."""
    if item_type == "product_context":
        history_model = models.ProductContextHistory
    else:
        history_model = models.ActiveContextHistory
    
    records = []
    for i in range(1, count + 1):
        record = history_model(
            version=i,
            content={"test_key": f"test_value_{i}", "version": i},
            change_source=f"Test Change {i}"
        )
        db_session.add(record)
        records.append(record)
    
    db_session.commit()
    return records

class TestGetItemHistory:
    """Test class voor get_item_history functie."""
    
    def setup_method(self):
        """Setup voor elke test method."""
        # Clean database voor elke test
        db = TestingSessionLocal()
        try:
            db.query(models.ProductContextHistory).delete()
            db.query(models.ActiveContextHistory).delete()
            db.commit()
        finally:
            db.close()
    
    def test_get_item_history_happy_path(self, client: TestClient, db_session):
        """Test het ophalen van item history met geldige parameters."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        # Maak test history records aan
        create_test_history_records(db_session, "product_context", 3)
        
        # Test het ophalen van product context history
        response = client.get(f"/workspaces/{workspace_b64}/history/product_context")
        assert response.status_code == 200
        
        history_data = response.json()
        assert isinstance(history_data, list)
        assert len(history_data) == 3
        
        # Controleer dat de records gesorteerd zijn op versie (descending)
        assert history_data[0]["version"] == 3
        assert history_data[1]["version"] == 2
        assert history_data[2]["version"] == 1
        
        # Controleer de structuur van elk record
        for record in history_data:
            assert "id" in record
            assert "timestamp" in record
            assert "version" in record
            assert "content" in record
            assert "change_source" in record
    
    def test_get_item_history_active_context(self, client: TestClient, db_session):
        """Test het ophalen van active context history."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        # Maak test history records aan voor active context
        create_test_history_records(db_session, "active_context", 2)
        
        response = client.get(f"/workspaces/{workspace_b64}/history/active_context")
        assert response.status_code == 200
        
        history_data = response.json()
        assert len(history_data) == 2
        assert history_data[0]["version"] == 2
        assert history_data[1]["version"] == 1
    
    def test_get_item_history_with_limit(self, client: TestClient, db_session):
        """Test het ophalen van history met limit parameter."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        # Maak meer test records aan
        create_test_history_records(db_session, "product_context", 5)
        
        # Test met limit=2
        response = client.get(f"/workspaces/{workspace_b64}/history/product_context?limit=2")
        assert response.status_code == 200
        
        history_data = response.json()
        assert len(history_data) == 2
        assert history_data[0]["version"] == 5  # Meest recente eerst
        assert history_data[1]["version"] == 4
    
    def test_get_item_history_invalid_item_type(self, client: TestClient):
        """Test het ophalen van history met ongeldige item_type."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        response = client.get(f"/workspaces/{workspace_b64}/history/invalid_type")
        assert response.status_code == 400
        assert "Invalid item_type" in response.json()["detail"]
    
    def test_get_item_history_empty_results(self, client: TestClient):
        """Test het ophalen van history wanneer er geen records zijn."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        response = client.get(f"/workspaces/{workspace_b64}/history/product_context")
        assert response.status_code == 200
        
        history_data = response.json()
        assert isinstance(history_data, list)
        # De database is opgeruimd in setup_method, dus verwachten we 0 records
        assert len(history_data) == 0


class TestDiffContextVersions:
    """Test class voor diff_context_versions functie."""
    
    def setup_method(self):
        """Setup voor elke test method."""
        # Clean database voor elke test
        db = TestingSessionLocal()
        try:
            db.query(models.ProductContextHistory).delete()
            db.query(models.ActiveContextHistory).delete()
            db.commit()
        finally:
            db.close()
    
    def test_diff_context_versions_function_exists(self):
        """Test dat de diff_context_versions functie bestaat en importeerbaar is."""
        from conport.main import diff_context_versions
        import inspect
        
        # Controleer dat de functie bestaat
        assert callable(diff_context_versions)
        
        # Controleer dat het een async functie is
        assert inspect.iscoroutinefunction(diff_context_versions)
        
        # Controleer de function signature
        sig = inspect.signature(diff_context_versions)
        expected_params = ["workspace_id", "item_type", "version_a", "version_b"]
        for param in expected_params:
            assert param in sig.parameters
        
        # Controleer de docstring
        assert diff_context_versions.__doc__ is not None
        assert "diff" in diff_context_versions.__doc__.lower()
    
    def test_diff_context_versions_invalid_item_type(self, db_session):
        """Test diff met ongeldige item_type."""
        from conport.main import diff_context_versions
        import asyncio
        
        result = asyncio.run(diff_context_versions(
            workspace_id="test",
            item_type="invalid_type",
            version_a=1,
            version_b=2,
            db=db_session
        ))
        
        # Verwacht een MCPError
        assert hasattr(result, 'error')
        assert "Invalid item_type" in result.error
        assert "invalid_type" in result.details["item_type"]
    
    def test_diff_context_versions_nonexistent_versions(self, db_session):
        """Test diff met niet-bestaande versies."""
        from conport.main import diff_context_versions
        import asyncio
        
        # Test met beide versies die niet bestaan
        result = asyncio.run(diff_context_versions(
            workspace_id="test",
            item_type="product_context",
            version_a=999,  # Bestaat niet
            version_b=1000,  # Bestaat ook niet
            db=db_session
        ))
        
        # Verwacht een MCPError voor de eerste versie die niet gevonden wordt
        assert hasattr(result, 'error')
        assert "Version 999 not found" in result.error
    
    def test_diff_context_versions_dictdiffer_import(self):
        """Test dat dictdiffer correct geïmporteerd wordt."""
        try:
            import dictdiffer
            # Test dat de diff functie bestaat
            assert hasattr(dictdiffer, 'diff')
            
            # Test een simpele diff om te controleren dat het werkt
            dict1 = {"a": 1, "b": 2}
            dict2 = {"a": 1, "b": 3, "c": 4}
            
            diff_result = list(dictdiffer.diff(dict1, dict2))
            assert len(diff_result) > 0
            
        except ImportError:
            pytest.fail("dictdiffer module is niet beschikbaar - nodig voor diff_context_versions")
    
    def test_diff_context_versions_database_model_structure(self):
        """Test dat de history models de juiste structuur hebben."""
        # Test ProductContextHistory model
        product_history = models.ProductContextHistory(
            version=1,
            content={"test": "data"},
            change_source="Test"
        )
        
        # Controleer de vereiste attributen
        assert hasattr(product_history, 'version')
        assert hasattr(product_history, 'content')
        assert hasattr(product_history, 'change_source')
        
        # Test ActiveContextHistory model
        active_history = models.ActiveContextHistory(
            version=1,
            content={"test": "data"},
            change_source="Test"
        )
        
        # Controleer de vereiste attributen
        assert hasattr(active_history, 'version')
        assert hasattr(active_history, 'content')
        assert hasattr(active_history, 'change_source')