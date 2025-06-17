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

# Create the FastAPI app for the tests
app = create_app()

# Use a fixed test-workspace for meta tests.
TEST_WORKSPACE_DIR = Path("./test_workspace_meta_extended")

def get_test_db_url():
    """Generates the URL for the test database."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"

# Setup a test-specific database engine
engine = create_engine(
    get_test_db_url(), connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Run the real Alembic migrations on the test database
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

@pytest.fixture
def db_session():
    """Create a database session for direct database operations."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

def b64_encode(s: str) -> str:
    """Helper to encode paths for test URLs."""
    return base64.urlsafe_b64encode(s.encode()).decode()

def create_test_data(db_session, test_suffix=""):
    """Helper function to create test data."""
    # Create test decisions
    decision1 = models.Decision(
        summary=f"Use Python for backend{test_suffix}",
        rationale="Python has excellent ecosystem",
        tags=["backend", "technology"]
    )
    decision2 = models.Decision(
        summary=f"Use PostgreSQL for database{test_suffix}",
        rationale="ACID compliance and performance",
        tags=["database", "technology"]
    )
    
    # Create test progress entries
    progress1 = models.ProgressEntry(
        status="IN_PROGRESS",
        description=f"Implement user authentication{test_suffix}"
    )
    progress2 = models.ProgressEntry(
        status="DONE",
        description=f"Setup project structure{test_suffix}"
    )
    
    # Create test system patterns with unique names
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
    """Test class for get_recent_activity function via meta endpoint."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()
    
    def test_get_recent_activity_endpoint(self, client: TestClient, db_session):
        """Test retrieving recent activity via the API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        # Create test data
        create_test_data(db_session, "_endpoint")
        
        # Test the API endpoint
        response = client.get(f"/workspaces/{workspace_b64}/meta/recent-activity")
        assert response.status_code == 200
        
        activity_data = response.json()
        assert isinstance(activity_data, dict)
        assert "decisions" in activity_data
        assert "progress" in activity_data
        assert "system_patterns" in activity_data
        
        # Check that we have data
        assert len(activity_data["decisions"]) > 0
        assert len(activity_data["progress"]) > 0
        assert len(activity_data["system_patterns"]) > 0
    
    def test_get_recent_activity_empty_database(self, client: TestClient):
        """Test recent activity with empty database."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)
        
        response = client.get(f"/workspaces/{workspace_b64}/meta/recent-activity")
        assert response.status_code == 200
        
        activity_data = response.json()
        # After setup_method the database should be empty
        assert activity_data["decisions"] == []
        assert activity_data["progress"] == []
        assert activity_data["system_patterns"] == []


class TestGetConportSchema:
    """Test class for get_conport_schema function."""
    
    def test_schema_function_exists(self):
        """Test that the get_conport_schema function exists and is importable."""
        from conport.main import get_conport_schema
        import inspect
        
        # Check that the function exists
        assert callable(get_conport_schema)
        
        # Check that it is an async function
        assert inspect.iscoroutinefunction(get_conport_schema)
        
        # Check the function signature
        sig = inspect.signature(get_conport_schema)
        assert "workspace_id" in sig.parameters
        
        # Check the docstring
        assert get_conport_schema.__doc__ is not None
        assert "schema" in get_conport_schema.__doc__.lower()
    
    def test_schema_function_structure(self):
        """Test the basic structure of the schema function without executing."""
        from conport.main import get_conport_schema
        
        # Test that the function has the correct annotations
        annotations = get_conport_schema.__annotations__
        assert "workspace_id" in annotations
        assert "return" in annotations
        
        # Check that the return annotation is a Dict
        return_annotation = str(annotations["return"])
        assert "Dict" in return_annotation or "dict" in return_annotation.lower()


class TestMetaServiceFunctions:
    """Test class for meta service functions directly."""
    
    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()
    
    def test_get_recent_activity_service(self, db_session):
        """Test the get_recent_activity service function directly."""
        from conport.services import meta_service
        
        # Create test data
        test_data = create_test_data(db_session, "_service")
        
        # Test the service function
        result = meta_service.get_recent_activity(db_session, limit=5)
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "progress" in result
        assert "system_patterns" in result
        
        # Check that we get the right amount of data
        assert len(result["decisions"]) == 2
        assert len(result["progress"]) == 2
        assert len(result["system_patterns"]) == 2
    
    def test_get_recent_activity_with_limit(self, db_session):
        """Test get_recent_activity with different limits."""
        from conport.services import meta_service
        
        # Create test data
        create_test_data(db_session, "_limit")
        
        # Test met limit=1
        result = meta_service.get_recent_activity(db_session, limit=1)
        
        assert len(result["decisions"]) <= 1
        assert len(result["progress"]) <= 1
        assert len(result["system_patterns"]) <= 1
    
    def test_batch_log_items_decisions(self, db_session):
        """Test batch_log_items for decisions."""
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
        """Test batch_log_items with invalid item type."""
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
        """Test batch_log_items with validation errors."""
        from conport.services import meta_service
        
        # Items with errors (missing required fields)
        items = [
            {"summary": "Valid decision"},  # Valid decision
            {"rationale": "Missing summary"},  # Invalid decision - no summary
            {}  # Completely empty item
        ]
        
        result = meta_service.batch_log_items(
            db=db_session,
            workspace_id="test_workspace",
            item_type="decision",
            items=items
        )
        
        assert result["succeeded"] == 1  # Only the first should succeed
        assert result["failed"] == 2    # The other two fail
        assert len(result["details"]) == 2  # Error details for the failed items
    
    def test_batch_log_items_progress(self, db_session):
        """Test batch_log_items for progress entries."""
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
        """Test get_recent_activity service with empty database."""
        from conport.services import meta_service
        
        # Test without data
        result = meta_service.get_recent_activity(db_session, limit=5)
        
        assert isinstance(result, dict)
        assert "decisions" in result
        assert "progress" in result
        assert "system_patterns" in result
        
        # Database is empty after setup_method
        assert len(result["decisions"]) == 0
        assert len(result["progress"]) == 0
        assert len(result["system_patterns"]) == 0