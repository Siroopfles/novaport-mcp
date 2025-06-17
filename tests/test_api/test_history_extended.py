import base64
from pathlib import Path

import pytest
from conport.app_factory import create_app
from conport.db import models
from conport.db.database import get_db, run_migrations_for_workspace
from conport.services import vector_service
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .test_utils import robust_rmtree

# Create the FastAPI app for the tests
app = create_app()

# Use a fixed test-workspace for history tests.
TEST_WORKSPACE_DIR = Path("./test_workspace_history_extended")

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
    """Override the 'get_db' dependency for the tests.
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

def create_test_history_records(db_session, item_type="product_context", count=3):
    """Helper function to create test history records."""
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
    """Test class for get_item_history function."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.ProductContextHistory).delete()
            db.query(models.ActiveContextHistory).delete()
            db.commit()
        finally:
            db.close()

    def test_get_item_history_happy_path(self, client: TestClient, db_session):
        """Test retrieving item history with valid parameters."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test history records
        create_test_history_records(db_session, "product_context", 3)

        # Test retrieving product context history
        response = client.get(f"/workspaces/{workspace_b64}/history/product_context")
        assert response.status_code == 200

        history_data = response.json()
        assert isinstance(history_data, list)
        assert len(history_data) == 3

        # Check that records are sorted by version (descending)
        assert history_data[0]["version"] == 3
        assert history_data[1]["version"] == 2
        assert history_data[2]["version"] == 1

        # Check the structure of each record
        for record in history_data:
            assert "id" in record
            assert "timestamp" in record
            assert "version" in record
            assert "content" in record
            assert "change_source" in record

    def test_get_item_history_active_context(self, client: TestClient, db_session):
        """Test retrieving active context history."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test history records for active context
        create_test_history_records(db_session, "active_context", 2)

        response = client.get(f"/workspaces/{workspace_b64}/history/active_context")
        assert response.status_code == 200

        history_data = response.json()
        assert len(history_data) == 2
        assert history_data[0]["version"] == 2
        assert history_data[1]["version"] == 1

    def test_get_item_history_with_limit(self, client: TestClient, db_session):
        """Test retrieving history with limit parameter."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create more test records
        create_test_history_records(db_session, "product_context", 5)

        # Test met limit=2
        response = client.get(f"/workspaces/{workspace_b64}/history/product_context?limit=2")
        assert response.status_code == 200

        history_data = response.json()
        assert len(history_data) == 2
        assert history_data[0]["version"] == 5  # Most recent first
        assert history_data[1]["version"] == 4

    def test_get_item_history_invalid_item_type(self, client: TestClient):
        """Test retrieving history with invalid item_type."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        response = client.get(f"/workspaces/{workspace_b64}/history/invalid_type")
        assert response.status_code == 400
        assert "Invalid item_type" in response.json()["detail"]

    def test_get_item_history_empty_results(self, client: TestClient):
        """Test retrieving history when there are no records."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        response = client.get(f"/workspaces/{workspace_b64}/history/product_context")
        assert response.status_code == 200

        history_data = response.json()
        assert isinstance(history_data, list)
        # The database is cleaned in setup_method, so we expect 0 records
        assert len(history_data) == 0


class TestDiffContextVersions:
    """Test class for diff_context_versions function."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.ProductContextHistory).delete()
            db.query(models.ActiveContextHistory).delete()
            db.commit()
        finally:
            db.close()

    def test_diff_context_versions_function_exists(self):
        """Test that the diff_context_versions function exists and is importable."""
        import inspect

        from conport.main import diff_context_versions

        # Check that the function exists
        assert callable(diff_context_versions)

        # Check that it is an async function
        assert inspect.iscoroutinefunction(diff_context_versions)

        # Check the function signature
        sig = inspect.signature(diff_context_versions)
        expected_params = ["workspace_id", "item_type", "version_a", "version_b"]
        for param in expected_params:
            assert param in sig.parameters

        # Check the docstring
        assert diff_context_versions.__doc__ is not None
        assert "diff" in diff_context_versions.__doc__.lower()

    def test_diff_context_versions_invalid_item_type(self, db_session):
        """Test diff with invalid item_type."""
        import asyncio

        from conport.main import diff_context_versions

        result = asyncio.run(diff_context_versions(
            workspace_id="test",
            item_type="invalid_type",
            version_a=1,
            version_b=2,
            db=db_session
        ))

        # Expect an MCPError
        assert hasattr(result, 'error')
        assert "Invalid item_type" in result.error
        assert "invalid_type" in result.details["item_type"]

    def test_diff_context_versions_nonexistent_versions(self, db_session):
        """Test diff with non-existent versions."""
        import asyncio

        from conport.main import diff_context_versions

        # Test with both versions that don't exist
        result = asyncio.run(diff_context_versions(
            workspace_id="test",
            item_type="product_context",
            version_a=999,  # Doesn't exist
            version_b=1000,  # Also doesn't exist
            db=db_session
        ))

        # Expect an MCPError for the first version that is not found
        assert hasattr(result, 'error')
        assert "Version 999 not found" in result.error

    def test_diff_context_versions_dictdiffer_import(self):
        """Test that dictdiffer is correctly imported."""
        try:
            import dictdiffer
            # Test that the diff function exists
            assert hasattr(dictdiffer, 'diff')

            # Test a simple diff to check that it works
            dict1 = {"a": 1, "b": 2}
            dict2 = {"a": 1, "b": 3, "c": 4}

            diff_result = list(dictdiffer.diff(dict1, dict2))
            assert len(diff_result) > 0

        except ImportError:
            pytest.fail("dictdiffer module is not available - required for diff_context_versions")

    def test_diff_context_versions_database_model_structure(self):
        """Test that the history models have the correct structure."""
        # Test ProductContextHistory model
        product_history = models.ProductContextHistory(
            version=1,
            content={"test": "data"},
            change_source="Test"
        )

        # Check the required attributes
        assert hasattr(product_history, 'version')
        assert hasattr(product_history, 'content')
        assert hasattr(product_history, 'change_source')

        # Test ActiveContextHistory model
        active_history = models.ActiveContextHistory(
            version=1,
            content={"test": "data"},
            change_source="Test"
        )

        # Check the required attributes
        assert hasattr(active_history, 'version')
        assert hasattr(active_history, 'content')
        assert hasattr(active_history, 'change_source')
