"""Additional tests for service modules to improve coverage."""

import pytest
import datetime
import json
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock, patch, mock_open, MagicMock
from sqlalchemy.orm import Session
from sqlalchemy.exc import NoResultFound
from pydantic import ValidationError

from src.conport.services import (
    custom_data_service, 
    progress_service, 
    io_service, 
    meta_service, 
    link_service
)
from src.conport.schemas.custom_data import CustomDataCreate
from src.conport.schemas.progress import ProgressEntryCreate, ProgressEntryUpdate
from src.conport.schemas.decision import DecisionCreate
from src.conport.schemas.link import LinkCreate


class TestCustomDataServiceCoverage:
    """Test custom_data_service functions for coverage improvement."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_get_function(self, mock_db_session):
        """Test get function."""
        mock_result = Mock()
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = mock_result
        
        result = custom_data_service.get(mock_db_session, "test_category", "test_key")
        
        assert result == mock_result
        mock_db_session.query.assert_called_once()

    def test_get_function_not_found(self, mock_db_session):
        """Test get function when not found."""
        mock_db_session.query.return_value.filter_by.return_value.first.return_value = None
        
        result = custom_data_service.get(mock_db_session, "nonexistent", "key")
        
        assert result is None

    def test_delete_function_exists(self, mock_db_session, workspace_id):
        """Test delete function when record exists."""
        mock_existing = Mock()
        mock_existing.id = 1
        
        with patch.object(custom_data_service, 'get') as mock_get:
            with patch('src.conport.services.vector_service.delete_embedding') as mock_delete_vector:
                mock_get.return_value = mock_existing
                
                result = custom_data_service.delete(
                    mock_db_session, workspace_id, "test_category", "test_key"
                )
                
                assert result == mock_existing
                mock_db_session.delete.assert_called_once_with(mock_existing)
                mock_db_session.commit.assert_called_once()
                mock_delete_vector.assert_called_once()

    def test_delete_function_not_exists(self, mock_db_session, workspace_id):
        """Test delete function when record doesn't exist."""
        with patch.object(custom_data_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = custom_data_service.delete(
                mock_db_session, workspace_id, "test_category", "test_key"
            )
            
            assert result is None
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()

    def test_upsert_create_new(self, mock_db_session, workspace_id):
        """Test upsert when creating new record."""
        data = CustomDataCreate(
            category="test_category",
            key="test_key",
            value={"new": "data"}
        )
        
        # Mock NoResultFound exception to simulate new record
        mock_db_session.query.return_value.filter_by.return_value.one.side_effect = NoResultFound()
        
        with patch('src.conport.services.vector_service.upsert_embedding') as mock_upsert_vector:
            result = custom_data_service.upsert(mock_db_session, workspace_id, data)
            
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
            mock_upsert_vector.assert_called_once()

    def test_upsert_update_existing(self, mock_db_session, workspace_id):
        """Test upsert when updating existing record."""
        data = CustomDataCreate(
            category="test_category",
            key="test_key",
            value={"updated": "data"}
        )
        
        mock_existing = Mock()
        mock_existing.id = 1
        mock_existing.category = "test_category"
        mock_existing.key = "test_key"
        mock_existing.value = {"updated": "data"}
        
        mock_db_session.query.return_value.filter_by.return_value.one.return_value = mock_existing
        
        with patch('src.conport.services.vector_service.upsert_embedding') as mock_upsert_vector:
            result = custom_data_service.upsert(mock_db_session, workspace_id, data)
            
            assert mock_existing.value == {"updated": "data"}
            mock_db_session.add.assert_not_called()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
            mock_upsert_vector.assert_called_once()

    def test_upsert_serialization_error(self, mock_db_session, workspace_id):
        """Test upsert when serialization fails for vector embedding."""
        data = CustomDataCreate(
            category="test_category",
            key="test_key",
            value={"new": "data"}
        )
        
        mock_db_session.query.return_value.filter_by.return_value.one.side_effect = NoResultFound()
        
        with patch('src.conport.services.vector_service.upsert_embedding') as mock_upsert_vector:
            with patch('json.dumps', side_effect=TypeError("Cannot serialize")):
                with patch('src.conport.services.custom_data_service.log') as mock_log:
                    result = custom_data_service.upsert(mock_db_session, workspace_id, data)
                    
                    mock_db_session.add.assert_called_once()
                    mock_db_session.commit.assert_called_once()
                    mock_db_session.refresh.assert_called_once()
                    mock_upsert_vector.assert_not_called()
                    mock_log.warning.assert_called_once()

    def test_get_by_category(self, mock_db_session):
        """Test get_by_category function."""
        mock_results = [Mock(), Mock()]
        mock_db_session.query.return_value.filter_by.return_value.all.return_value = mock_results
        
        result = custom_data_service.get_by_category(mock_db_session, "test_category")
        
        assert result == mock_results
        mock_db_session.query.assert_called_once()

    def test_search_fts_without_category(self, mock_db_session):
        """Test search_fts function without category filter."""
        mock_row1 = Mock()
        mock_row1._mapping = {"id": 1, "category": "cat1", "key": "key1", "value": {"data": "value1"}}
        mock_row2 = Mock()
        mock_row2._mapping = {"id": 2, "category": "cat2", "key": "key2", "value": {"data": "value2"}}
        
        mock_db_session.execute.return_value = [mock_row1, mock_row2]
        
        with patch('src.conport.db.models.CustomData') as mock_model:
            result = custom_data_service.search_fts(mock_db_session, "test query", limit=5)
            
            mock_db_session.execute.assert_called_once()
            assert mock_model.call_count == 2

    def test_search_fts_with_category(self, mock_db_session):
        """Test search_fts function with category filter."""
        mock_row = Mock()
        mock_row._mapping = {"id": 1, "category": "specific_cat", "key": "key1", "value": {"data": "value1"}}
        
        mock_db_session.execute.return_value = [mock_row]
        
        with patch('src.conport.db.models.CustomData') as mock_model:
            result = custom_data_service.search_fts(mock_db_session, "test query", category="specific_cat", limit=10)
            
            mock_db_session.execute.assert_called_once()
            assert mock_model.call_count == 1


class TestProgressServiceCoverage:
    """Test progress_service functions for coverage improvement."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_create_with_parent_id(self, mock_db_session, workspace_id):
        """Test create function with parent_id."""
        entry_data = ProgressEntryCreate(
            status="TODO",
            description="Test task with parent",
            parent_id=1
        )
        
        with patch('src.conport.services.vector_service.upsert_embedding') as mock_upsert:
            result = progress_service.create(
                mock_db_session,
                workspace_id,
                entry_data,
                linked_item_type=None,
                linked_item_id=None,
                link_relationship_type="relates_to"
            )
            
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()
            mock_upsert.assert_called_once()

    def test_create_with_linking(self, mock_db_session, workspace_id):
        """Test create function with item linking."""
        entry_data = ProgressEntryCreate(
            status="IN_PROGRESS",
            description="Test task with linking"
        )
        
        with patch('src.conport.services.vector_service.upsert_embedding') as mock_upsert:
            with patch('src.conport.services.link_service.create') as mock_link:
                result = progress_service.create(
                    mock_db_session,
                    workspace_id,
                    entry_data,
                    linked_item_type="decision",
                    linked_item_id="123",
                    link_relationship_type="implements"
                )
                
                mock_db_session.add.assert_called_once()
                mock_db_session.commit.assert_called_once()
                mock_link.assert_called_once()

    def test_get_function(self, mock_db_session):
        """Test get function."""
        mock_progress = Mock()
        mock_progress.id = 1
        
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_progress
        
        result = progress_service.get(mock_db_session, 1)
        
        assert result == mock_progress
        mock_db_session.query.assert_called_once()

    def test_get_not_found(self, mock_db_session):
        """Test get function when not found."""
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        result = progress_service.get(mock_db_session, 999)
        
        assert result is None

    def test_update_function(self, mock_db_session):
        """Test update function."""
        mock_progress = Mock()
        mock_progress.id = 1
        mock_progress.status = "TODO"
        mock_progress.description = "Old description"
        
        update_data = ProgressEntryUpdate(
            status="DONE",
            description="Updated description"
        )
        
        with patch.object(progress_service, 'get') as mock_get:
            mock_get.return_value = mock_progress
            
            result = progress_service.update(
                mock_db_session,
                1,
                update_data
            )
            
            assert result == mock_progress
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_update_not_found(self, mock_db_session):
        """Test update function when progress not found."""
        update_data = ProgressEntryUpdate(status="DONE")
        
        with patch.object(progress_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = progress_service.update(
                mock_db_session, 999, update_data
            )
            
            assert result is None
            mock_db_session.commit.assert_not_called()

    def test_delete_function(self, mock_db_session, workspace_id):
        """Test delete function."""
        mock_progress = Mock()
        mock_progress.id = 1
        
        with patch.object(progress_service, 'get') as mock_get:
            with patch('src.conport.services.vector_service.delete_embedding') as mock_delete:
                mock_get.return_value = mock_progress
                
                result = progress_service.delete(
                    mock_db_session, workspace_id, 1
                )
                
                assert result == mock_progress
                mock_db_session.delete.assert_called_once_with(mock_progress)
                mock_db_session.commit.assert_called_once()
                mock_delete.assert_called_once()

    def test_delete_not_found(self, mock_db_session, workspace_id):
        """Test delete function when progress not found."""
        with patch.object(progress_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = progress_service.delete(
                mock_db_session, workspace_id, 999
            )
            
            assert result is None
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()


class TestIOServiceCoverage:
    """Test io_service functions for coverage improvement."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_export_to_markdown_with_decisions(self, mock_db_session):
        """Test export_to_markdown when decisions exist."""
        mock_decision1 = Mock()
        mock_decision1.summary = "Decision 1"
        mock_decision1.timestamp = "2024-01-01T10:00:00Z"
        mock_decision1.rationale = "Test rationale"
        mock_decision1.implementation_details = "Test implementation"
        mock_decision1.tags = ["tag1", "tag2"]

        mock_decision2 = Mock()
        mock_decision2.summary = "Decision 2"
        mock_decision2.timestamp = "2024-01-02T11:00:00Z"
        mock_decision2.rationale = None
        mock_decision2.implementation_details = None
        mock_decision2.tags = []

        mock_export_path = MagicMock(spec=Path)
        
        with patch('src.conport.services.decision_service.get_multi') as mock_get_multi:
            with patch('builtins.open', mock_open()) as mock_file:
                mock_get_multi.return_value = [mock_decision1, mock_decision2]
                
                result = io_service.export_to_markdown(mock_db_session, mock_export_path)
                
                assert result["status"] == "success"
                assert "decisions.md" in result["files_created"]
                mock_export_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)
                mock_file.assert_called_once()

    def test_export_to_markdown_no_decisions(self, mock_db_session):
        """Test export_to_markdown when no decisions exist."""
        mock_export_path = MagicMock(spec=Path)
        
        with patch('src.conport.services.decision_service.get_multi') as mock_get_multi:
            mock_get_multi.return_value = []
            
            result = io_service.export_to_markdown(mock_db_session, mock_export_path)
            
            assert result["status"] == "success"
            assert result["files_created"] == []
            mock_export_path.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_import_from_markdown_success(self, mock_db_session, workspace_id):
        """Test import_from_markdown with valid content."""
        mock_import_path = MagicMock(spec=Path)
        mock_decisions_file = MagicMock()
        mock_decisions_file.exists.return_value = True
        mock_import_path.__truediv__.return_value = mock_decisions_file
        
        markdown_content = """# Decision Log

## First Decision

**Timestamp:** 2024-01-01T10:00:00Z

**Rationale:**
This is the rationale for first decision

**Implementation Details:**
Implementation details here

**Tags:** tag1, tag2

---

## Second Decision

**Timestamp:** 2024-01-02T11:00:00Z

---"""

        with patch('builtins.open', mock_open(read_data=markdown_content)):
            with patch('src.conport.services.decision_service.create') as mock_create:
                result = io_service.import_from_markdown(mock_db_session, workspace_id, mock_import_path)
                
                assert result["status"] == "completed"
                assert result["imported"] == 2
                assert result["failed"] == 0
                assert mock_create.call_count == 2

    def test_import_from_markdown_file_not_found(self, mock_db_session, workspace_id):
        """Test import_from_markdown when decisions.md doesn't exist."""
        mock_import_path = MagicMock(spec=Path)
        mock_decisions_file = MagicMock()
        mock_decisions_file.exists.return_value = False
        mock_import_path.__truediv__.return_value = mock_decisions_file
        
        result = io_service.import_from_markdown(mock_db_session, workspace_id, mock_import_path)
        
        assert result["status"] == "failed"
        assert result["error"] == "decisions.md not found"

    def test_import_from_markdown_parse_errors(self, mock_db_session, workspace_id):
        """Test import_from_markdown with malformed content."""
        mock_import_path = MagicMock(spec=Path)
        mock_decisions_file = MagicMock()
        mock_decisions_file.exists.return_value = True
        mock_import_path.__truediv__.return_value = mock_decisions_file
        
        malformed_content = """# Decision Log

## Valid Decision

**Timestamp:** 2024-01-01T10:00:00Z

---

Invalid block without proper header

---

## Another Valid Decision

**Timestamp:** 2024-01-02T11:00:00Z

---"""

        with patch('builtins.open', mock_open(read_data=malformed_content)):
            with patch('src.conport.services.decision_service.create') as mock_create:
                # First call succeeds, second call raises exception
                mock_create.side_effect = [None, Exception("Creation failed")]
                
                result = io_service.import_from_markdown(mock_db_session, workspace_id, mock_import_path)
                
                assert result["status"] == "completed"
                assert result["imported"] == 1
                assert result["failed"] == 1


class TestMetaServiceCoverage:
    """Test meta_service functions for coverage improvement."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_get_recent_activity(self, mock_db_session):
        """Test get_recent_activity function."""
        mock_decisions = [Mock(), Mock()]
        mock_progress = [Mock()]
        mock_patterns = [Mock(), Mock(), Mock()]
        
        with patch('src.conport.services.decision_service.get_multi') as mock_decision_multi:
            with patch('src.conport.services.progress_service.get_multi') as mock_progress_multi:
                with patch('src.conport.services.system_pattern_service.get_multi') as mock_pattern_multi:
                    mock_decision_multi.return_value = mock_decisions
                    mock_progress_multi.return_value = mock_progress
                    mock_pattern_multi.return_value = mock_patterns
                    
                    result = meta_service.get_recent_activity(mock_db_session, limit=10)
                    
                    assert result["decisions"] == mock_decisions
                    assert result["progress"] == mock_progress
                    assert result["system_patterns"] == mock_patterns
                    
                    mock_decision_multi.assert_called_once_with(mock_db_session, limit=10, since=None)
                    mock_progress_multi.assert_called_once_with(mock_db_session, limit=10, since=None)
                    mock_pattern_multi.assert_called_once_with(mock_db_session, limit=10, since=None)

    def test_get_recent_activity_with_since(self, mock_db_session):
        """Test get_recent_activity function with since parameter."""
        since_date = datetime.datetime(2024, 1, 1)
        
        with patch('src.conport.services.decision_service.get_multi') as mock_decision_multi:
            with patch('src.conport.services.progress_service.get_multi') as mock_progress_multi:
                with patch('src.conport.services.system_pattern_service.get_multi') as mock_pattern_multi:
                    result = meta_service.get_recent_activity(mock_db_session, limit=5, since=since_date)
                    
                    mock_decision_multi.assert_called_once_with(mock_db_session, limit=5, since=since_date)
                    mock_progress_multi.assert_called_once_with(mock_db_session, limit=5, since=since_date)
                    mock_pattern_multi.assert_called_once_with(mock_db_session, limit=5, since=since_date)

    def test_batch_log_items_decisions_success(self, mock_db_session, workspace_id):
        """Test batch_log_items for decisions with successful items."""
        items = [
            {"summary": "Decision 1", "rationale": "Rationale 1"},
            {"summary": "Decision 2", "rationale": "Rationale 2"}
        ]
        
        with patch('src.conport.services.decision_service.create') as mock_create:
            result = meta_service.batch_log_items(mock_db_session, workspace_id, "decision", items)
            
            assert result["succeeded"] == 2
            assert result["failed"] == 0
            assert result["details"] == []
            assert mock_create.call_count == 2

    def test_batch_log_items_progress_success(self, mock_db_session, workspace_id):
        """Test batch_log_items for progress entries."""
        items = [
            {"status": "TODO", "description": "Task 1"},
            {"status": "IN_PROGRESS", "description": "Task 2"}
        ]
        
        with patch('src.conport.services.progress_service.create') as mock_create:
            result = meta_service.batch_log_items(mock_db_session, workspace_id, "progress", items)
            
            assert result["succeeded"] == 2
            assert result["failed"] == 0
            # Verify progress-specific kwargs were added
            mock_create.assert_called()

    def test_batch_log_items_custom_data_success(self, mock_db_session, workspace_id):
        """Test batch_log_items for custom_data."""
        items = [
            {"category": "test", "key": "key1", "value": {"data": "value1"}},
            {"category": "test", "key": "key2", "value": {"data": "value2"}}
        ]
        
        with patch('src.conport.services.custom_data_service.upsert') as mock_upsert:
            result = meta_service.batch_log_items(mock_db_session, workspace_id, "custom_data", items)
            
            assert result["succeeded"] == 2
            assert result["failed"] == 0
            assert mock_upsert.call_count == 2

    def test_batch_log_items_invalid_type(self, mock_db_session, workspace_id):
        """Test batch_log_items with invalid item_type."""
        items = [{"some": "data"}]
        
        with pytest.raises(ValueError, match="Invalid item_type for batch operation"):
            meta_service.batch_log_items(mock_db_session, workspace_id, "invalid_type", items)

    def test_batch_log_items_validation_errors(self, mock_db_session, workspace_id):
        """Test batch_log_items with validation errors."""
        items = [
            {"summary": "Valid Decision"},  # Valid
            {"invalid": "data"},            # Invalid - missing required fields
            {"summary": "Another Valid Decision"}  # Valid
        ]
        
        with patch('src.conport.services.decision_service.create') as mock_create:
            result = meta_service.batch_log_items(mock_db_session, workspace_id, "decision", items)
            
            assert result["succeeded"] == 2
            assert result["failed"] == 1
            assert len(result["details"]) == 1
            assert "error" in result["details"][0]


class TestLinkServiceCoverage:
    """Test link_service functions for coverage improvement."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    def test_create_link(self, mock_db_session):
        """Test create function."""
        link_data = LinkCreate(
            source_item_type="decision",
            source_item_id="1",
            target_item_type="progress_entry",
            target_item_id="2",
            relationship_type="implements"
        )
        
        mock_link = Mock()
        mock_link.id = 1
        
        mock_db_session.add.return_value = None
        mock_db_session.commit.return_value = None
        mock_db_session.refresh.return_value = None
        
        with patch('src.conport.db.models.ContextLink') as mock_model:
            mock_model.return_value = mock_link
            
            result = link_service.create(mock_db_session, link_data)
            
            mock_db_session.add.assert_called_once()
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_get_for_item_as_source(self, mock_db_session):
        """Test get_for_item when item is source."""
        mock_links = [Mock(), Mock()]
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_links
        
        result = link_service.get_for_item(mock_db_session, "decision", "123", limit=25)
        
        assert result == mock_links
        mock_db_session.query.assert_called_once()

    def test_get_for_item_as_target(self, mock_db_session):
        """Test get_for_item when item is target."""
        mock_links = [Mock()]
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = mock_links
        
        result = link_service.get_for_item(mock_db_session, "progress_entry", "456", limit=50)
        
        assert result == mock_links
        mock_db_session.query.assert_called_once()

    def test_get_for_item_no_results(self, mock_db_session):
        """Test get_for_item when no links found."""
        mock_db_session.query.return_value.filter.return_value.limit.return_value.all.return_value = []
        
        result = link_service.get_for_item(mock_db_session, "custom_data", "nonexistent")
        
        assert result == []
        mock_db_session.query.assert_called_once()
class TestDecisionServiceExtended:
    """Additional tests for decision_service to improve coverage."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_get_multi_with_since(self, mock_db_session):
        """Test get_multi function with since parameter."""
        since_date = datetime.datetime(2024, 1, 1)
        mock_decisions = [Mock(), Mock()]
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_decisions
        
        from src.conport.services import decision_service
        result = decision_service.get_multi(mock_db_session, limit=10, since=since_date)
        
        assert result == mock_decisions
        mock_db_session.query.assert_called_once()

    def test_update_function(self, mock_db_session):
        """Test update function."""
        from src.conport.services import decision_service
        from src.conport.schemas.decision import DecisionUpdate
        
        mock_decision = Mock()
        mock_decision.id = 1
        mock_decision.summary = "Updated Decision"
        
        update_data = DecisionUpdate(summary="Updated Decision")
        
        with patch.object(decision_service, 'get') as mock_get:
            mock_get.return_value = mock_decision
            
            result = decision_service.update(mock_db_session, 1, update_data)
            
            assert result == mock_decision
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_update_not_found(self, mock_db_session):
        """Test update function when decision not found."""
        from src.conport.services import decision_service
        from src.conport.schemas.decision import DecisionUpdate
        
        update_data = DecisionUpdate(summary="Updated Decision")
        
        with patch.object(decision_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = decision_service.update(mock_db_session, 999, update_data)
            
            assert result is None
            mock_db_session.commit.assert_not_called()

    def test_delete_function(self, mock_db_session, workspace_id):
        """Test delete function."""
        from src.conport.services import decision_service
        
        mock_decision = Mock()
        mock_decision.id = 1
        
        with patch.object(decision_service, 'get') as mock_get:
            with patch('src.conport.services.vector_service.delete_embedding') as mock_delete:
                mock_get.return_value = mock_decision
                
                result = decision_service.delete(mock_db_session, workspace_id, 1)
                
                assert result == mock_decision
                mock_db_session.delete.assert_called_once_with(mock_decision)
                mock_db_session.commit.assert_called_once()
                mock_delete.assert_called_once()

    def test_delete_not_found(self, mock_db_session, workspace_id):
        """Test delete function when decision not found."""
        from src.conport.services import decision_service
        
        with patch.object(decision_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = decision_service.delete(mock_db_session, workspace_id, 999)
            
            assert result is None
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()


class TestSystemPatternServiceExtended:
    """Additional tests for system_pattern_service to improve coverage."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_get_multi_with_since(self, mock_db_session):
        """Test get_multi function with since parameter."""
        since_date = datetime.datetime(2024, 1, 1)
        mock_patterns = [Mock(), Mock()]
        
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_patterns
        
        from src.conport.services import system_pattern_service
        result = system_pattern_service.get_multi(mock_db_session, limit=10, since=since_date)
        
        assert result == mock_patterns
        mock_db_session.query.assert_called_once()

    def test_update_function(self, mock_db_session):
        """Test update function."""
        from src.conport.services import system_pattern_service
        from src.conport.schemas.system_pattern import SystemPatternUpdate
        
        mock_pattern = Mock()
        mock_pattern.id = 1
        mock_pattern.name = "Updated Pattern"
        
        update_data = SystemPatternUpdate(name="Updated Pattern")
        
        with patch.object(system_pattern_service, 'get') as mock_get:
            mock_get.return_value = mock_pattern
            
            result = system_pattern_service.update(mock_db_session, 1, update_data)
            
            assert result == mock_pattern
            mock_db_session.commit.assert_called_once()
            mock_db_session.refresh.assert_called_once()

    def test_update_not_found(self, mock_db_session):
        """Test update function when pattern not found."""
        from src.conport.services import system_pattern_service
        from src.conport.schemas.system_pattern import SystemPatternUpdate
        
        update_data = SystemPatternUpdate(name="Updated Pattern")
        
        with patch.object(system_pattern_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = system_pattern_service.update(mock_db_session, 999, update_data)
            
            assert result is None
            mock_db_session.commit.assert_not_called()

    def test_delete_function(self, mock_db_session, workspace_id):
        """Test delete function."""
        from src.conport.services import system_pattern_service
        
        mock_pattern = Mock()
        mock_pattern.id = 1
        
        with patch.object(system_pattern_service, 'get') as mock_get:
            with patch('src.conport.services.vector_service.delete_embedding') as mock_delete:
                mock_get.return_value = mock_pattern
                
                result = system_pattern_service.delete(mock_db_session, workspace_id, 1)
                
                assert result == mock_pattern
                mock_db_session.delete.assert_called_once_with(mock_pattern)
                mock_db_session.commit.assert_called_once()
                mock_delete.assert_called_once()

    def test_delete_not_found(self, mock_db_session, workspace_id):
        """Test delete function when pattern not found."""
        from src.conport.services import system_pattern_service
        
        with patch.object(system_pattern_service, 'get') as mock_get:
            mock_get.return_value = None
            
            result = system_pattern_service.delete(mock_db_session, workspace_id, 999)
            
            assert result is None
            mock_db_session.delete.assert_not_called()
            mock_db_session.commit.assert_not_called()