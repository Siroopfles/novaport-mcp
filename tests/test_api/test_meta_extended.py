import base64
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

# Gebruik een vaste test-workspace voor meta tests.
TEST_WORKSPACE_DIR = Path("./test_workspace_meta_extended")

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

def create_test_data(db_session, test_suffix=""):
    """Helper functie om test data aan te maken."""
    # Maak test decisions aan
    decision1 = models.Decision(
        summary=f"Use Python for backend{test_suffix}",
        rationale="Python heeft excellent ecosystem",
        tags=["backend", "technology"]
    )
    decision2 = models.Decision(
        summary=f"Use PostgreSQL for database{test_suffix}",
        rationale="ACID compliance en performance",
        tags=["database", "technology"]
    )
    
    # Maak test progress entries aan
    progress1 = models.ProgressEntry(
        status="IN_PROGRESS",
        description=f"Implement user authentication{test_suffix}"
    )
    progress2 = models.ProgressEntry(
        status="DONE",
        description=f"Setup project structure{test_suffix}"
    )
    
    # Maak test system patterns aan met unieke namen
    pattern1 = models.SystemPattern(
        name=f"Repository Pattern{test_suffix}",
        description="Data access abstraction pattern",
        tags=["architecture", "pattern"]
    )
    pattern2 = models.SystemPattern(
        name=f"MVC Pattern{test_suffix}",
        description="Model-View-Controller architectural pattern",
        tags=["architecture", "pattern"]
    )
    
    db_session.add_all([decision1, decision2, progress1, progress2, pattern1, pattern2])
    db_session.commit()
    
    return {
        "decisions": [decision1, decision2],
        "progress": [progress1, progress2],
        "patterns": [pattern1, pattern2]
    }


class TestGetRecentActivity:
    """Test class voor get_recent_activity functie via meta endpoint."""
    
    def setup_method(self):
        """Setup voor elke test method."""
        # Clean database voor elke test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()
    
    def test_get_recent_activity_endpoint(self, client: TestClient, db_session):
        """Test het ophalen van recent activity via de API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        # Maak test data aan
        create_test_data(db_session, "_endpoint")
        
        # Test de API endpoint
        response = client.get(f"/workspaces/{workspace_b64}/meta/recent-activity")
        assert response.status_code == 200
        
        activity_data = response.json()
        assert isinstance(activity_data, dict)
        assert "decisions" in activity_data
        assert "progress" in activity_data
        assert "system_patterns" in activity_data
        
        # Controleer dat we data hebben
        assert len(activity_data["decisions"]) > 0
        assert len(activity_data["progress"]) > 0
        assert len(activity_data["system_patterns"]) > 0
    
    def test_get_recent_activity_empty_database(self, client: TestClient):
        """Test recent activity met lege database."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        response = client.get(f"/workspaces/{workspace_b64}/meta/recent-activity")
        assert response.status_code == 200
        
        activity_data = response.json()
        # Na setup_method zou de database leeg moeten zijn
        assert activity_data["decisions"] == []
        assert activity_data["progress"] == []
        assert activity_data["system_patterns"] == []


class TestGetConportSchema:
    """Test class voor get_conport_schema functie."""
    
    def test_schema_function_exists(self):
        """Test dat de get_conport_schema functie bestaat en importeerbaar is."""
        from conport.main import get_conport_schema
        import inspect
        
        # Controleer dat de functie bestaat
        assert callable(get_conport_schema)
        
        # Controleer dat het een async functie is
        assert inspect.iscoroutinefunction(get_conport_schema)
        
        # Controleer de function signature
        sig = inspect.signature(get_conport_schema)
        assert "workspace_id" in sig.parameters
        
        # Controleer de docstring
        assert get_conport_schema.__doc__ is not None
        assert "schema" in get_conport_schema.__doc__.lower()
    
    def test_schema_function_structure(self):
        """Test de basis structuur van de schema functie zonder uit te voeren."""
        from conport.main import get_conport_schema
        
        # Test dat de functie de juiste annotations heeft
        annotations = get_conport_schema.__annotations__
        assert "workspace_id" in annotations
        assert "return" in annotations
        
        # Controleer dat de return annotation een Dict is
        return_annotation = str(annotations["return"])
        assert "Dict" in return_annotation or "dict" in return_annotation.lower()


class TestMetaServiceFunctions:
    """Test class voor meta service functies direct."""
    
    def setup_method(self):
        """Setup voor elke test method."""
        # Clean database voor elke test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()
    
    def test_get_recent_activity_service(self, db_session):
        """Test de get_recent_activity service functie direct."""
        from conport.services import meta_service
        
        # Maak test data aan
        test_data = create_test_data(db_session, "_service")
        
        # Test de service functie
        result = meta_service.get_recent_activity(db_session, limit=5)
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "progress" in result
        assert "system_patterns" in result
        
        # Controleer dat we de juiste hoeveelheid data krijgen
        assert len(result["decisions"]) == 2
        assert len(result["progress"]) == 2
        assert len(result["system_patterns"]) == 2
    
    def test_get_recent_activity_with_limit(self, db_session):
        """Test get_recent_activity met verschillende limits."""
        from conport.services import meta_service
        
        # Maak test data aan
        create_test_data(db_session, "_limit")
        
        # Test met limit=1
        result = meta_service.get_recent_activity(db_session, limit=1)
        
        assert len(result["decisions"]) <= 1
        assert len(result["progress"]) <= 1
        assert len(result["system_patterns"]) <= 1
    
    def test_batch_log_items_decisions(self, db_session):
        """Test batch_log_items voor decisions."""
        from conport.services import meta_service
        
        items = [
            {
                "summary": "Decision 1",
                "rationale": "Rationale 1",
                "tags": ["test"]
            },
            {
                "summary": "Decision 2", 
                "rationale": "Rationale 2"
            }
        ]
        
        result = meta_service.batch_log_items(
            db=db_session,
            workspace_id="test_workspace",
            item_type="decision",
            items=items
        )
        
        assert result["succeeded"] == 2
        assert result["failed"] == 0
        assert len(result["details"]) == 0
    
    def test_batch_log_items_invalid_type(self, db_session):
        """Test batch_log_items met ongeldige item type."""
        from conport.services import meta_service
        
        items = [{"test": "data"}]
        
        with pytest.raises(ValueError) as exc_info:
            meta_service.batch_log_items(
                db=db_session,
                workspace_id="test_workspace",
                item_type="invalid_type",
                items=items
            )
        
        assert "Invalid item_type for batch operation" in str(exc_info.value)
    
    def test_batch_log_items_validation_errors(self, db_session):
        """Test batch_log_items met validatie fouten."""
        from conport.services import meta_service
        
        # Items met fouten (ontbrekende required fields)
        items = [
            {"summary": "Valid decision"},  # Geldige decision
            {"rationale": "Missing summary"},  # Ongeldige decision - geen summary
            {}  # Volledig leeg item
        ]
        
        result = meta_service.batch_log_items(
            db=db_session,
            workspace_id="test_workspace",
            item_type="decision",
            items=items
        )
        
        assert result["succeeded"] == 1  # Alleen de eerste zou moeten slagen
        assert result["failed"] == 2    # De andere twee falen
        assert len(result["details"]) == 2  # Error details voor de gefaalde items
    
    def test_batch_log_items_progress(self, db_session):
        """Test batch_log_items voor progress entries."""
        from conport.services import meta_service
        
        items = [
            {
                "status": "TODO",
                "description": "Task 1"
            },
            {
                "status": "IN_PROGRESS",
                "description": "Task 2"
            }
        ]
        
        result = meta_service.batch_log_items(
            db=db_session,
            workspace_id="test_workspace", 
            item_type="progress",
            items=items
        )
        
        assert result["succeeded"] == 2
        assert result["failed"] == 0
    
    def test_get_recent_activity_empty_database(self, db_session):
        """Test get_recent_activity service met lege database."""
        from conport.services import meta_service
        
        # Test zonder data
        result = meta_service.get_recent_activity(db_session, limit=5)
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "progress" in result
        assert "system_patterns" in result
        
        # Database is leeg na setup_method
        assert len(result["decisions"]) == 0
        assert len(result["progress"]) == 0
        assert len(result["system_patterns"]) == 0