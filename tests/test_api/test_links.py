"""Comprehensive tests for Link service functionality.

Tests the link management functionality for ConPort including:
- Link creation between ConPort items
- Retrieving links for specific items
- Different relationship types and bidirectional links
- Error handling for invalid parameters and duplicate links
- Link integrity and validation tests
"""

import base64
from datetime import datetime
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

# Use a fixed test workspace for link tests
TEST_WORKSPACE_DIR = Path("./test_workspace_links")


def get_test_db_url():
    """Generates the URL for the test database."""
    data_dir = TEST_WORKSPACE_DIR / ".novaport_data"
    data_dir.mkdir(parents=True, exist_ok=True)
    db_path = data_dir.resolve() / "conport.db"
    return f"sqlite:///{db_path}"


# Setup a test-specific database engine
engine = create_engine(get_test_db_url(), connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Run the real Alembic migrations on the test database
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


def create_test_items(db_session):
    """Helper function to create test items for linking."""
    # Generate unique timestamp for this test run
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

    # Create test decisions
    decision1 = models.Decision(
        summary="Use microservices architecture",
        rationale="Better scalability and maintainability",
    )
    decision2 = models.Decision(
        summary="Implement API gateway", rationale="Centralized routing and security"
    )

    # Create test progress entries
    progress1 = models.ProgressEntry(
        status="IN_PROGRESS", description="Design microservices architecture"
    )
    progress2 = models.ProgressEntry(status="TODO", description="Set up API gateway")

    # Create test system patterns with unique names
    pattern1 = models.SystemPattern(
        name=f"Service Discovery Pattern {timestamp}",
        description="Pattern for service registration and discovery",
    )

    db_session.add_all([decision1, decision2, progress1, progress2, pattern1])
    db_session.commit()

    return {
        "decisions": [decision1, decision2],
        "progress": [progress1, progress2],
        "patterns": [pattern1],
    }


class TestLinkCreation:
    """Test class for link creation functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.ContextLink).delete()
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()

    def test_create_link_endpoint_success(self, client: TestClient, db_session):
        """Test successful link creation via API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test items
        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        # Create link between decision and progress entry
        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "progress",
            "target_item_id": str(progress.id),
            "relationship_type": "implements",
            "description": "This progress entry implements the decision",
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 201
        created_link = response.json()

        assert created_link["source_item_type"] == "decision"
        assert created_link["source_item_id"] == str(decision.id)
        assert created_link["target_item_type"] == "progress"
        assert created_link["target_item_id"] == str(progress.id)
        assert created_link["relationship_type"] == "implements"
        assert "id" in created_link
        assert "timestamp" in created_link

    def test_create_link_minimal_data(self, client: TestClient, db_session):
        """Test link creation with minimal required data (no description)."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        pattern = test_items["patterns"][0]

        # Create link without description
        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "system_pattern",
            "target_item_id": str(pattern.id),
            "relationship_type": "uses",
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 201
        created_link = response.json()

        assert created_link["description"] is None
        assert created_link["relationship_type"] == "uses"

    def test_create_bidirectional_links(self, client: TestClient, db_session):
        """Test creating bidirectional links between items."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision1 = test_items["decisions"][0]
        decision2 = test_items["decisions"][1]

        # Create link from decision1 to decision2
        link_data_1 = {
            "source_item_type": "decision",
            "source_item_id": str(decision1.id),
            "target_item_type": "decision",
            "target_item_id": str(decision2.id),
            "relationship_type": "depends_on",
            "description": "Decision 1 depends on Decision 2",
        }

        response1 = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data_1)
        assert response1.status_code == 201

        # Create reverse link from decision2 to decision1
        link_data_2 = {
            "source_item_type": "decision",
            "source_item_id": str(decision2.id),
            "target_item_type": "decision",
            "target_item_id": str(decision1.id),
            "relationship_type": "enables",
            "description": "Decision 2 enables Decision 1",
        }

        response2 = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data_2)
        assert response2.status_code == 201

        # Verify both links exist
        links = db_session.query(models.ContextLink).all()
        assert len(links) == 2

        relationship_types = [link.relationship_type for link in links]
        assert "depends_on" in relationship_types
        assert "enables" in relationship_types

    def test_create_link_service_function_directly(self, db_session):
        """Test the link creation service function directly."""
        from conport.schemas.link import LinkCreate
        from conport.services import link_service

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        link_data = LinkCreate(
            source_item_type="decision",
            source_item_id=str(decision.id),
            target_item_type="progress",
            target_item_id=str(progress.id),
            relationship_type="guides",
            description="Decision guides progress implementation",
        )

        created_link = link_service.create(db_session, link_data)

        assert str(created_link.source_item_type) == "decision"
        assert str(created_link.source_item_id) == str(decision.id)
        assert str(created_link.target_item_type) == "progress"
        assert str(created_link.target_item_id) == str(progress.id)
        assert str(created_link.relationship_type) == "guides"
        assert created_link.id is not None
        assert created_link.timestamp is not None


class TestLinkRetrieval:
    """Test class for link retrieval functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.ContextLink).delete()
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()

    def test_get_links_for_item_endpoint(self, client: TestClient, db_session):
        """Test retrieving links for a specific item via API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test items and links
        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress1 = test_items["progress"][0]
        progress2 = test_items["progress"][1]

        # Create multiple links involving the decision
        links_data = [
            {
                "source_item_type": "decision",
                "source_item_id": str(decision.id),
                "target_item_type": "progress",
                "target_item_id": str(progress1.id),
                "relationship_type": "implements",
            },
            {
                "source_item_type": "progress",
                "source_item_id": str(progress2.id),
                "target_item_type": "decision",
                "target_item_id": str(decision.id),
                "relationship_type": "references",
            },
        ]

        # Create the links
        for link_data in links_data:
            client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        # Retrieve links for the decision
        response = client.get(
            f"/workspaces/{workspace_b64}/links/decision/{decision.id}"
        )

        assert response.status_code == 200
        links = response.json()

        assert len(links) == 2

        # Verify both links are returned (decision can be source or target)
        relationship_types = [link["relationship_type"] for link in links]
        assert "implements" in relationship_types
        assert "references" in relationship_types

    def test_get_links_for_item_no_links(self, client: TestClient, db_session):
        """Test retrieving links for item that has no links."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]

        response = client.get(
            f"/workspaces/{workspace_b64}/links/decision/{decision.id}"
        )

        assert response.status_code == 200
        links = response.json()
        assert len(links) == 0

    def test_get_links_for_nonexistent_item(self, client: TestClient):
        """Test retrieving links for nonexistent item."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        response = client.get(f"/workspaces/{workspace_b64}/links/decision/99999")

        assert response.status_code == 200
        links = response.json()
        assert len(links) == 0

    def test_get_links_service_function_directly(self, db_session):
        """Test the get links service function directly."""
        from conport.schemas.link import LinkCreate
        from conport.services import link_service

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        # Create a link first
        link_data = LinkCreate(
            source_item_type="decision",
            source_item_id=str(decision.id),
            target_item_type="progress",
            target_item_id=str(progress.id),
            relationship_type="directs",
        )
        link_service.create(db_session, link_data)

        # Retrieve links for the decision
        links = link_service.get_for_item(db_session, "decision", str(decision.id))

        assert len(links) == 1
        assert str(links[0].relationship_type) == "directs"
        assert str(links[0].source_item_id) == str(decision.id)

        # Retrieve links for the progress entry
        links = link_service.get_for_item(db_session, "progress", str(progress.id))

        assert len(links) == 1
        assert str(links[0].relationship_type) == "directs"
        assert str(links[0].target_item_id) == str(progress.id)


class TestLinkRelationshipTypes:
    """Test class for different relationship types and link patterns."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.ContextLink).delete()
            db.query(models.Decision).delete()
            db.query(models.ProgressEntry).delete()
            db.query(models.SystemPattern).delete()
            db.commit()
        finally:
            db.close()

    def test_various_relationship_types(self, client: TestClient, db_session):
        """Test creating links with various relationship types."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]
        pattern = test_items["patterns"][0]

        relationship_types = [
            "implements",
            "depends_on",
            "enables",
            "uses",
            "references",
            "conflicts_with",
            "supersedes",
            "validates",
            "complements",
        ]

        # Create links with different relationship types
        for i, rel_type in enumerate(relationship_types):
            if i % 3 == 0:
                # Decision to Progress
                source_type, source_id = "decision", str(decision.id)
                target_type, target_id = "progress", str(progress.id)
            elif i % 3 == 1:
                # Progress to Pattern
                source_type, source_id = "progress", str(progress.id)
                target_type, target_id = "system_pattern", str(pattern.id)
            else:
                # Pattern to Decision
                source_type, source_id = "system_pattern", str(pattern.id)
                target_type, target_id = "decision", str(decision.id)

            link_data = {
                "source_item_type": source_type,
                "source_item_id": source_id,
                "target_item_type": target_type,
                "target_item_id": target_id,
                "relationship_type": rel_type,
                "description": f"Test {rel_type} relationship",
            }

            response = client.post(
                f"/workspaces/{workspace_b64}/links/", json=link_data
            )
            assert response.status_code == 201

        # Verify all links were created
        links = db_session.query(models.ContextLink).all()
        assert len(links) == len(relationship_types)

        created_rel_types = [link.relationship_type for link in links]
        for rel_type in relationship_types:
            assert rel_type in created_rel_types

    def test_self_referential_links(self, client: TestClient, db_session):
        """Test creating links from an item to itself."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]

        # Create self-referential link
        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "decision",
            "target_item_id": str(decision.id),
            "relationship_type": "references",
            "description": "Self-referential relationship for versioning",
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 201
        created_link = response.json()
        assert created_link["source_item_id"] == created_link["target_item_id"]

    def test_multiple_links_same_items(self, client: TestClient, db_session):
        """Test creating multiple links between the same items with different relationships."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        # Create multiple relationships between same items
        relationships = ["implements", "references", "validates"]

        for rel_type in relationships:
            link_data = {
                "source_item_type": "decision",
                "source_item_id": str(decision.id),
                "target_item_type": "progress",
                "target_item_id": str(progress.id),
                "relationship_type": rel_type,
                "description": f"Decision {rel_type} progress",
            }

            response = client.post(
                f"/workspaces/{workspace_b64}/links/", json=link_data
            )
            assert response.status_code == 201

        # Verify all relationships exist
        links = db_session.query(models.ContextLink).all()
        assert len(links) == 3

        created_rel_types = [link.relationship_type for link in links]
        for rel_type in relationships:
            assert rel_type in created_rel_types


class TestLinkErrorHandling:
    """Test class for link error handling and edge cases."""

    def test_create_link_missing_required_fields(self, client: TestClient):
        """Test link creation with missing required fields."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Test missing source_item_type
        incomplete_link = {
            "source_item_id": "1",
            "target_item_type": "progress",
            "target_item_id": "2",
            "relationship_type": "implements",
        }

        response = client.post(
            f"/workspaces/{workspace_b64}/links/", json=incomplete_link
        )

        assert response.status_code == 422  # Validation error

    def test_create_link_empty_relationship_type(self, client: TestClient, db_session):
        """Test link creation with empty relationship type."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "progress",
            "target_item_id": str(progress.id),
            "relationship_type": "",  # Empty relationship type
            "description": "Empty relationship type test",
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 422  # Validation error

    def test_get_links_with_limit(self, client: TestClient, db_session):
        """Test retrieving links with the default limit."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]

        # Create many links to test limit (default is 50)
        for i in range(10):  # Create 10 links
            progress = models.ProgressEntry(
                status="TODO", description=f"Test progress {i}"
            )
            db_session.add(progress)
            db_session.commit()

            link_data = {
                "source_item_type": "decision",
                "source_item_id": str(decision.id),
                "target_item_type": "progress",
                "target_item_id": str(progress.id),
                "relationship_type": "implements",
            }

            client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        response = client.get(
            f"/workspaces/{workspace_b64}/links/decision/{decision.id}"
        )

        assert response.status_code == 200
        links = response.json()
        assert len(links) == 10  # All links should be returned (under limit)

    def test_link_with_very_long_description(self, client: TestClient, db_session):
        """Test creating a link with a very long description."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        # Very long description
        long_description = "A" * 2000  # 2000 character description

        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "progress",
            "target_item_id": str(progress.id),
            "relationship_type": "implements",
            "description": long_description,
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 201
        created_link = response.json()
        assert len(created_link["description"]) == 2000

    def test_link_with_special_characters(self, client: TestClient, db_session):
        """Test creating links with special characters in descriptions."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        test_items = create_test_items(db_session)
        decision = test_items["decisions"][0]
        progress = test_items["progress"][0]

        special_description = (
            "Special chars: äöü ñ 中文 🚀 <tag> & \"quotes\" 'apostrophes'"
        )

        link_data = {
            "source_item_type": "decision",
            "source_item_id": str(decision.id),
            "target_item_type": "progress",
            "target_item_id": str(progress.id),
            "relationship_type": "implements",
            "description": special_description,
        }

        response = client.post(f"/workspaces/{workspace_b64}/links/", json=link_data)

        assert response.status_code == 201
        created_link = response.json()
        assert created_link["description"] == special_description
