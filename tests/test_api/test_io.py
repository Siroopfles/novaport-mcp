"""Comprehensive tests for I/O service functionality.

Tests the export/import functionality for ConPort data including:
- Export to markdown functionality
- Import from markdown functionality
- Error handling for invalid parameters
- Edge cases and boundary conditions
"""

import base64
import shutil
import tempfile
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

# Use a fixed test workspace for I/O tests
TEST_WORKSPACE_DIR = Path("./test_workspace_io")

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

def create_test_decisions(db_session, count: int = 3):
    """Helper function to create test decisions for export/import testing."""
    decisions = []
    for i in range(count):
        decision = models.Decision(
            summary=f"Test Decision {i+1}",
            rationale=f"Test rationale for decision {i+1}",
            implementation_details=f"Implementation details for decision {i+1}",
            tags=["test", f"decision{i+1}"]
        )
        decisions.append(decision)

    db_session.add_all(decisions)
    db_session.commit()
    return decisions


class TestIOExportFunctionality:
    """Test class for I/O export functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.commit()
        finally:
            db.close()

    def test_export_data_endpoint_success(self, client: TestClient, db_session):
        """Test successful data export via API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create test data
        create_test_decisions(db_session, 2)

        # Test the export endpoint
        response = client.post(
            f"/workspaces/{workspace_b64}/io/export",
            params={"export_dir": "test_export"}
        )

        assert response.status_code == 200
        export_result = response.json()

        assert export_result["status"] == "success"
        assert "path" in export_result
        assert "files_created" in export_result
        assert "decisions.md" in export_result["files_created"]

        # Verify the exported file exists and has content
        export_path = Path(export_result["path"])
        decisions_file = export_path / "decisions.md"
        assert decisions_file.exists()

        content = decisions_file.read_text(encoding="utf-8")
        assert "# Decision Log" in content
        assert "Test Decision 1" in content
        assert "Test Decision 2" in content

    def test_export_data_empty_database(self, client: TestClient):
        """Test export with empty database."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        response = client.post(
            f"/workspaces/{workspace_b64}/io/export",
            params={"export_dir": "empty_export"}
        )

        assert response.status_code == 200
        export_result = response.json()

        assert export_result["status"] == "success"
        # Should have empty files_created list for empty database
        assert export_result["files_created"] == []

    def test_export_data_with_complex_content(self, client: TestClient, db_session):
        """Test export with complex decision content including special characters."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create decision with complex content
        complex_decision = models.Decision(
            summary="Decision with special chars: äöü & <tags>",
            rationale="Multi-line\nrationale with\n**markdown** formatting",
            implementation_details="Details with\n- bullet points\n- and more",
            tags=["special-chars", "markdown", "unicode"]
        )
        db_session.add(complex_decision)
        db_session.commit()

        response = client.post(
            f"/workspaces/{workspace_b64}/io/export",
            params={"export_dir": "complex_export"}
        )

        assert response.status_code == 200
        export_result = response.json()
        assert export_result["status"] == "success"

        # Verify complex content is properly exported
        export_path = Path(export_result["path"])
        decisions_file = export_path / "decisions.md"
        content = decisions_file.read_text(encoding="utf-8")

        assert "äöü & <tags>" in content
        assert "Multi-line\nrationale" in content
        assert "special-chars, markdown, unicode" in content

    def test_export_service_function_directly(self, db_session):
        """Test the export service function directly."""
        from conport.services import io_service

        # Create test data
        create_test_decisions(db_session, 1)

        # Create temporary export directory
        with tempfile.TemporaryDirectory() as temp_dir:
            export_path = Path(temp_dir) / "direct_export"

            result = io_service.export_to_markdown(db_session, export_path)

            assert result["status"] == "success"
            assert str(export_path) == result["path"]
            assert "decisions.md" in result["files_created"]

            # Verify file was created
            decisions_file = export_path / "decisions.md"
            assert decisions_file.exists()
            content = decisions_file.read_text(encoding="utf-8")
            assert "Test Decision 1" in content


class TestIOImportFunctionality:
    """Test class for I/O import functionality."""

    def setup_method(self):
        """Setup for each test method."""
        # Clean database for each test
        db = TestingSessionLocal()
        try:
            db.query(models.Decision).delete()
            db.commit()
        finally:
            db.close()

    def test_import_data_endpoint_success(self, client: TestClient, db_session):
        """Test successful data import via API endpoint."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create a markdown file to import
        with tempfile.TemporaryDirectory() as temp_dir:
            import_dir = Path(temp_dir) / "import_test"
            import_dir.mkdir(parents=True, exist_ok=True)

            decisions_content = """# Decision Log

## Use FastAPI for API development

**Rationale:**
FastAPI provides excellent performance and automatic API documentation.

---

## Implement PostgreSQL database

**Rationale:**
PostgreSQL offers ACID compliance and excellent performance.

---
"""

            decisions_file = import_dir / "decisions.md"
            decisions_file.write_text(decisions_content, encoding="utf-8")

            # Copy the import directory to the workspace
            workspace_import_dir = Path(workspace_path) / "import_test"
            if workspace_import_dir.exists():
                robust_rmtree(workspace_import_dir)
            shutil.copytree(import_dir, workspace_import_dir)

            # Test the import endpoint
            response = client.post(
                f"/workspaces/{workspace_b64}/io/import",
                params={"import_dir": "import_test"}
            )

            assert response.status_code == 200
            import_result = response.json()

            assert import_result["status"] == "completed"
            assert import_result["imported"] == 2
            assert import_result["failed"] == 0

            # Verify decisions were imported
            decisions = db_session.query(models.Decision).all()
            assert len(decisions) == 2

            summaries = [d.summary for d in decisions]
            assert "Use FastAPI for API development" in summaries
            assert "Implement PostgreSQL database" in summaries

    def test_import_data_missing_file(self, client: TestClient):
        """Test import with missing decisions.md file."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        response = client.post(
            f"/workspaces/{workspace_b64}/io/import",
            params={"import_dir": "nonexistent_dir"}
        )

        # The service returns success with error message, not HTTP 500
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "failed"
        assert "not found" in result["error"]

    def test_import_data_malformed_content(self, client: TestClient, db_session):
        """Test import with malformed markdown content."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        # Create malformed markdown file
        with tempfile.TemporaryDirectory() as temp_dir:
            import_dir = Path(temp_dir) / "malformed_import"
            import_dir.mkdir(parents=True, exist_ok=True)

            # Content with valid and invalid decision blocks
            malformed_content = """# Decision Log

## Valid Decision
**Rationale:** This should work.
---

Invalid block without proper structure
---

## Another Valid Decision
**Rationale:** This should also work.
---
"""

            decisions_file = import_dir / "decisions.md"
            decisions_file.write_text(malformed_content, encoding="utf-8")

            # Copy to workspace
            workspace_import_dir = Path(workspace_path) / "malformed_import"
            if workspace_import_dir.exists():
                robust_rmtree(workspace_import_dir)
            shutil.copytree(import_dir, workspace_import_dir)

            response = client.post(
                f"/workspaces/{workspace_b64}/io/import",
                params={"import_dir": "malformed_import"}
            )

            assert response.status_code == 200
            import_result = response.json()

            assert import_result["status"] == "completed"
            assert import_result["imported"] == 2  # 2 valid decisions found
            assert import_result["failed"] == 0   # No actual parsing failures

    def test_import_service_function_directly(self, db_session):
        """Test the import service function directly."""
        from conport.services import io_service

        # Create temporary import directory with valid content
        with tempfile.TemporaryDirectory() as temp_dir:
            import_path = Path(temp_dir)

            decisions_content = """# Decision Log

## Direct Service Test Decision

**Rationale:**
Testing the service function directly.

---
"""

            decisions_file = import_path / "decisions.md"
            decisions_file.write_text(decisions_content, encoding="utf-8")

            result = io_service.import_from_markdown(
                db_session, "test_workspace", import_path
            )

            assert result["status"] == "completed"
            assert result["imported"] == 1
            assert result["failed"] == 0

            # Verify decision was imported
            decisions = db_session.query(models.Decision).all()
            assert len(decisions) == 1
            assert decisions[0].summary == "Direct Service Test Decision"


class TestIOErrorHandling:
    """Test class for I/O error handling and edge cases."""

    def test_export_invalid_workspace(self, client: TestClient):
        """Test export with invalid workspace encoding."""
        invalid_workspace_b64 = "invalid_base64_encoding"

        response = client.post(
            f"/workspaces/{invalid_workspace_b64}/io/export"
        )

        assert response.status_code == 500
        assert "Export failed" in response.json()["detail"]

    def test_import_invalid_workspace(self, client: TestClient):
        """Test import with invalid workspace encoding."""
        invalid_workspace_b64 = "invalid_base64_encoding"

        response = client.post(
            f"/workspaces/{invalid_workspace_b64}/io/import"
        )

        assert response.status_code == 500
        assert "Import failed" in response.json()["detail"]

    def test_export_with_custom_directory_name(self, client: TestClient, db_session):
        """Test export with custom directory name."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        create_test_decisions(db_session, 1)

        custom_dir = "my_custom_export_folder"
        response = client.post(
            f"/workspaces/{workspace_b64}/io/export",
            params={"export_dir": custom_dir}
        )

        assert response.status_code == 200
        export_result = response.json()
        assert custom_dir in export_result["path"]

    def test_import_empty_decisions_file(self, client: TestClient):
        """Test import with empty decisions.md file."""
        workspace_path = str(TEST_WORKSPACE_DIR.resolve())
        workspace_b64 = b64_encode(workspace_path)

        with tempfile.TemporaryDirectory() as temp_dir:
            import_dir = Path(temp_dir) / "empty_import"
            import_dir.mkdir(parents=True, exist_ok=True)

            # Create empty decisions file
            decisions_file = import_dir / "decisions.md"
            decisions_file.write_text("", encoding="utf-8")

            # Copy to workspace
            workspace_import_dir = Path(workspace_path) / "empty_import"
            if workspace_import_dir.exists():
                robust_rmtree(workspace_import_dir)
            shutil.copytree(import_dir, workspace_import_dir)

            response = client.post(
                f"/workspaces/{workspace_b64}/io/import",
                params={"import_dir": "empty_import"}
            )

            assert response.status_code == 200
            import_result = response.json()
            assert import_result["imported"] == 0
            assert import_result["failed"] == 0
