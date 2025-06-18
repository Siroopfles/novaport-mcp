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
        import inspect

        from conport.main import get_conport_schema

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
class TestTimestampFiltering:
    """Test class for timestamp filtering functionality in get_recent_activity."""

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

    def test_get_recent_activity_with_since_parameter(self, db_session):
        """Test get_recent_activity with since datetime parameter."""
        import datetime

        from conport.services import meta_service

        # Create test data at different times
        now = datetime.datetime.utcnow()
        two_hours_ago = now - datetime.timedelta(hours=2)
        four_hours_ago = now - datetime.timedelta(hours=4)

        # Create decisions with different timestamps
        old_decision = models.Decision(
            summary="Old decision",
            rationale="This is old",
            timestamp=four_hours_ago
        )
        recent_decision = models.Decision(
            summary="Recent decision",
            rationale="This is recent",
            timestamp=now
        )

        db_session.add_all([old_decision, recent_decision])
        db_session.commit()

        # Test filtering with since parameter
        result = meta_service.get_recent_activity(db_session, limit=10, since=two_hours_ago)

        assert isinstance(result, dict)
        assert "decisions" in result
        assert len(result["decisions"]) == 1
        assert result["decisions"][0].summary == "Recent decision"

    def test_get_recent_activity_with_since_endpoint(self, client: TestClient, db_session):
        """Test get_recent_activity endpoint with since timestamp parameter."""
        import datetime

        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test data
        now = datetime.datetime.utcnow()
        three_hours_ago = now - datetime.timedelta(hours=3)

        old_decision = models.Decision(
            summary="Old decision for endpoint test",
            timestamp=three_hours_ago
        )
        recent_decision = models.Decision(
            summary="Recent decision for endpoint test",
            timestamp=now
        )

        db_session.add_all([old_decision, recent_decision])
        db_session.commit()

        # Test endpoint with since parameter (ISO format)
        one_hour_ago = now - datetime.timedelta(hours=1)
        since_param = one_hour_ago.isoformat()

        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"since": since_param}
        )

        assert response.status_code == 200
        activity_data = response.json()

        assert len(activity_data["decisions"]) == 1
        assert activity_data["decisions"][0]["summary"] == "Recent decision for endpoint test"

    def test_get_recent_activity_with_hours_ago_parameter(self, client: TestClient, db_session):
        """Test get_recent_activity endpoint with hours_ago parameter."""
        import datetime

        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test data
        now = datetime.datetime.utcnow()
        five_hours_ago = now - datetime.timedelta(hours=5)

        old_progress = models.ProgressEntry(
            status="DONE",
            description="Old progress entry",
            timestamp=five_hours_ago
        )
        recent_progress = models.ProgressEntry(
            status="IN_PROGRESS",
            description="Recent progress entry",
            timestamp=now
        )

        db_session.add_all([old_progress, recent_progress])
        db_session.commit()

        # Test with hours_ago=3 (should get only recent entry)
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"hours_ago": 3}
        )

        assert response.status_code == 200
        activity_data = response.json()

        # Should only get the recent progress entry
        assert len(activity_data["progress"]) == 1
        assert activity_data["progress"][0]["description"] == "Recent progress entry"

    def test_get_recent_activity_edge_cases(self, client: TestClient, db_session):
        """Test edge cases for timestamp filtering."""
        import datetime

        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test data
        create_test_data(db_session, "_edge_cases")

        # Test with invalid timestamp format
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"since": "invalid-timestamp"}
        )
        # Should handle gracefully, possibly return 400 or ignore invalid parameter
        assert response.status_code in [200, 400]

        # Test with future timestamp
        future_time = datetime.datetime.utcnow() + datetime.timedelta(hours=1)
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"since": future_time.isoformat()}
        )

        assert response.status_code == 200
        activity_data = response.json()
        # Future timestamp should return empty results
        assert len(activity_data["decisions"]) == 0
        assert len(activity_data["progress"]) == 0
        assert len(activity_data["system_patterns"]) == 0

        # Test with very large hours_ago value
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"hours_ago": 999999}
        )

        assert response.status_code == 200
        activity_data = response.json()
        # Should return all items
        assert len(activity_data["decisions"]) > 0

        # Test with negative hours_ago
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={"hours_ago": -1}
        )
        # Should handle gracefully
        assert response.status_code in [200, 400]

    def test_get_recent_activity_combination_parameters(self, client: TestClient, db_session):
        """Test combination of both since_timestamp and hours_ago parameters."""
        import datetime

        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test data with specific timestamps
        now = datetime.datetime.utcnow()
        six_hours_ago = now - datetime.timedelta(hours=6)
        two_hours_ago = now - datetime.timedelta(hours=2)

        pattern1 = models.SystemPattern(
            name="Old Pattern",
            description="Created 6 hours ago",
            timestamp=six_hours_ago
        )
        pattern2 = models.SystemPattern(
            name="Recent Pattern",
            description="Created 2 hours ago",
            timestamp=two_hours_ago
        )
        pattern3 = models.SystemPattern(
            name="Very Recent Pattern",
            description="Created now",
            timestamp=now
        )

        db_session.add_all([pattern1, pattern2, pattern3])
        db_session.commit()

        # Test with both parameters - since should take precedence or they should work together
        three_hours_ago = now - datetime.timedelta(hours=3)
        response = client.get(
            f"/workspaces/{workspace_b64}/meta/recent-activity",
            params={
                "since": three_hours_ago.isoformat(),
                "hours_ago": 1  # This would normally only get the very recent one
            }
        )

        assert response.status_code == 200
        activity_data = response.json()

        # Should get patterns created in the last 3 hours (pattern2 and pattern3)
        assert len(activity_data["system_patterns"]) == 2
        pattern_names = [p["name"] for p in activity_data["system_patterns"]]
        assert "Recent Pattern" in pattern_names
        assert "Very Recent Pattern" in pattern_names
        assert "Old Pattern" not in pattern_names

    def test_timestamp_filtering_with_different_item_types(self, db_session):
        """Test timestamp filtering works correctly across different item types."""
        import datetime

        from conport.services import meta_service

        now = datetime.datetime.utcnow()
        cutoff_time = now - datetime.timedelta(hours=2)
        old_time = now - datetime.timedelta(hours=4)

        # Create items of different types with timestamps before and after cutoff
        old_decision = models.Decision(
            summary="Old decision",
            timestamp=old_time
        )
        recent_decision = models.Decision(
            summary="Recent decision",
            timestamp=now
        )

        old_progress = models.ProgressEntry(
            status="DONE",
            description="Old progress",
            timestamp=old_time
        )
        recent_progress = models.ProgressEntry(
            status="IN_PROGRESS",
            description="Recent progress",
            timestamp=now
        )

        old_pattern = models.SystemPattern(
            name="Old Pattern",
            timestamp=old_time
        )
        recent_pattern = models.SystemPattern(
            name="Recent Pattern",
            timestamp=now
        )

        db_session.add_all([
            old_decision, recent_decision,
            old_progress, recent_progress,
            old_pattern, recent_pattern
        ])
        db_session.commit()

        # Test filtering with since parameter
        result = meta_service.get_recent_activity(db_session, limit=10, since=cutoff_time)

        # Should only get recent items
        assert len(result["decisions"]) == 1
        assert result["decisions"][0].summary == "Recent decision"

        assert len(result["progress"]) == 1
        assert result["progress"][0].description == "Recent progress"

        assert len(result["system_patterns"]) == 1
        assert result["system_patterns"][0].name == "Recent Pattern"

    def test_timestamp_filtering_boundary_conditions(self, db_session):
        """Test timestamp filtering boundary conditions."""
        import datetime

        from conport.services import meta_service

        now = datetime.datetime.utcnow()
        exact_cutoff = now - datetime.timedelta(hours=1)

        # Create items exactly at the cutoff time and just before/after
        before_cutoff = models.Decision(
            summary="Before cutoff",
            timestamp=exact_cutoff - datetime.timedelta(seconds=1)
        )
        at_cutoff = models.Decision(
            summary="At cutoff",
            timestamp=exact_cutoff
        )
        after_cutoff = models.Decision(
            summary="After cutoff",
            timestamp=exact_cutoff + datetime.timedelta(seconds=1)
        )

        db_session.add_all([before_cutoff, at_cutoff, after_cutoff])
        db_session.commit()

        # Test with exact cutoff time
        result = meta_service.get_recent_activity(db_session, limit=10, since=exact_cutoff)

        # Should include items at or after cutoff time
        assert len(result["decisions"]) == 2
        summaries = [d.summary for d in result["decisions"]]
        assert "At cutoff" in summaries
        assert "After cutoff" in summaries
        assert "Before cutoff" not in summaries

    def test_timestamp_filtering_with_limit(self, db_session):
        """Test that timestamp filtering works correctly with limit parameter."""
        import datetime

        from conport.services import meta_service

        now = datetime.datetime.utcnow()
        cutoff_time = now - datetime.timedelta(hours=1)

        # Create many recent items (more than typical limit)
        recent_decisions = []
        for i in range(10):
            decision = models.Decision(
                summary=f"Recent decision {i}",
                timestamp=now - datetime.timedelta(minutes=i)
            )
            recent_decisions.append(decision)

        db_session.add_all(recent_decisions)
        db_session.commit()

        # Test with both since parameter and small limit
        result = meta_service.get_recent_activity(db_session, limit=3, since=cutoff_time)

        # Should respect both filters
        assert len(result["decisions"]) == 3  # Limited by limit parameter

        # All returned items should be after cutoff
        for decision in result["decisions"]:
            assert decision.timestamp >= cutoff_time
        assert len(result["system_patterns"]) == 0
