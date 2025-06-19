"""Tests for main CLI module functions - DISABLED (replaced by async tests)."""

import pytest
from unittest.mock import Mock, patch
from sqlalchemy.orm import Session

from src.conport import main
from src.conport.schemas.decision import DecisionCreate
from src.conport.schemas.progress import ProgressEntryCreate
from src.conport.schemas.system_pattern import SystemPatternCreate
from src.conport.schemas.custom_data import CustomDataCreate

# NOTE: These sync tests are disabled because main.py functions are all async.
# Use test_main_async.py instead.

@pytest.mark.skip("Sync tests disabled - main.py functions are async. Use test_main_async.py")


class TestMainCLIFunctions:
    """Test main CLI functions for coverage."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    def test_get_product_context(self, mock_db_session):
        """Test get_product_context function."""
        with patch('src.conport.main.context_service.get_product_context') as mock_get:
            mock_context = Mock()
            mock_context.content = {"goal": "Test project"}
            mock_get.return_value = mock_context
            
            result = main.get_product_context(db=mock_db_session)
            
            assert result == {"goal": "Test project"}
            mock_get.assert_called_once_with(mock_db_session)

    def test_get_active_context(self, mock_db_session):
        """Test get_active_context function."""
        with patch('src.conport.main.context_service.get_active_context') as mock_get:
            mock_context = Mock()
            mock_context.content = {"current_focus": "Testing"}
            mock_get.return_value = mock_context
            
            result = main.get_active_context(db=mock_db_session)
            
            assert result == {"current_focus": "Testing"}
            mock_get.assert_called_once_with(mock_db_session)

    def test_log_decision(self, mock_db_session, workspace_id):
        """Test log_decision function."""
        with patch('src.conport.main.decision_service.create') as mock_create:
            mock_decision = Mock()
            mock_decision.id = 1
            mock_decision.summary = "Test decision"
            mock_create.return_value = mock_decision
            
            result = main.log_decision(
                workspace_id=workspace_id,
                summary="Test decision",
                rationale="Test rationale",
                db=mock_db_session
            )
            
            assert result["id"] == 1
            assert result["summary"] == "Test decision"
            mock_create.assert_called_once()

    def test_get_decisions(self, mock_db_session):
        """Test get_decisions function."""
        with patch('src.conport.main.decision_service.get_multi') as mock_get:
            mock_decisions = [Mock(id=1, summary="Decision 1")]
            mock_get.return_value = mock_decisions
            
            result = main.get_decisions(limit=10, db=mock_db_session)
            
            assert len(result) == 1
            mock_get.assert_called_once()

    def test_log_progress(self, mock_db_session, workspace_id):
        """Test log_progress function."""
        with patch('src.conport.main.progress_service.create') as mock_create:
            mock_progress = Mock()
            mock_progress.id = 1
            mock_progress.status = "TODO"
            mock_create.return_value = mock_progress
            
            result = main.log_progress(
                workspace_id=workspace_id,
                status="TODO",
                description="Test task",
                db=mock_db_session
            )
            
            assert result["id"] == 1
            assert result["status"] == "TODO"
            mock_create.assert_called_once()

    def test_get_progress(self, mock_db_session):
        """Test get_progress function."""
        with patch('src.conport.main.progress_service.get_multi') as mock_get:
            mock_progress = [Mock(id=1, status="TODO")]
            mock_get.return_value = mock_progress
            
            result = main.get_progress(limit=10, db=mock_db_session)
            
            assert len(result) == 1
            mock_get.assert_called_once()

    def test_log_system_pattern(self, mock_db_session, workspace_id):
        """Test log_system_pattern function."""
        with patch('src.conport.main.system_pattern_service.create') as mock_create:
            mock_pattern = Mock()
            mock_pattern.id = 1
            mock_pattern.name = "Test Pattern"
            mock_create.return_value = mock_pattern
            
            result = main.log_system_pattern(
                workspace_id=workspace_id,
                name="Test Pattern",
                description="Test description",
                db=mock_db_session
            )
            
            assert result["id"] == 1
            assert result["name"] == "Test Pattern"
            mock_create.assert_called_once()

    def test_get_system_patterns(self, mock_db_session):
        """Test get_system_patterns function."""
        with patch('src.conport.main.system_pattern_service.get_multi') as mock_get:
            mock_patterns = [Mock(id=1, name="Pattern 1")]
            mock_get.return_value = mock_patterns
            
            result = main.get_system_patterns(limit=10, db=mock_db_session)
            
            assert len(result) == 1
            mock_get.assert_called_once()

    def test_log_custom_data(self, mock_db_session, workspace_id):
        """Test log_custom_data function."""
        with patch('src.conport.main.custom_data_service.upsert') as mock_upsert:
            mock_data = Mock()
            mock_data.category = "test_category"
            mock_data.key = "test_key"
            mock_upsert.return_value = mock_data
            
            result = main.log_custom_data(
                workspace_id=workspace_id,
                category="test_category",
                key="test_key",
                value={"test": "data"},
                db=mock_db_session
            )
            
            assert result["category"] == "test_category"
            assert result["key"] == "test_key"
            mock_upsert.assert_called_once()

    def test_get_custom_data(self, mock_db_session):
        """Test get_custom_data function."""
        with patch('src.conport.main.custom_data_service.get_by_category') as mock_get:
            mock_data = [Mock(category="test", key="key1")]
            mock_get.return_value = mock_data
            
            result = main.get_custom_data(
                category="test",
                db=mock_db_session
            )
            
            assert len(result) == 1
            mock_get.assert_called_once()

    def test_get_recent_activity_summary(self, mock_db_session, workspace_id):
        """Test get_recent_activity_summary function."""
        with patch('src.conport.main.meta_service.get_recent_activity') as mock_get:
            mock_activity = {"decisions": [], "progress": []}
            mock_get.return_value = mock_activity
            
            result = main.get_recent_activity_summary(
                workspace_id=workspace_id,
                db=mock_db_session
            )
            
            assert "decisions" in result
            assert "progress" in result
            mock_get.assert_called_once()

    def test_link_conport_items(self, mock_db_session, workspace_id):
        """Test link_conport_items function."""
        with patch('src.conport.main.link_service.create') as mock_create:
            mock_link = Mock()
            mock_link.id = 1
            mock_create.return_value = mock_link
            
            result = main.link_conport_items(
                workspace_id=workspace_id,
                source_item_type="decision",
                source_item_id="1",
                target_item_type="progress",
                target_item_id="2",
                relationship_type="implements",
                db=mock_db_session
            )
            
            assert result["id"] == 1
            mock_create.assert_called_once()


class TestMainErrorHandling:
    """Test error handling in main functions."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    def test_get_decisions_with_error(self, mock_db_session):
        """Test get_decisions with service error."""
        with patch('src.conport.main.decision_service.get_multi') as mock_get:
            mock_get.side_effect = Exception("Database error")
            
            with pytest.raises(Exception):
                main.get_decisions(limit=10, db=mock_db_session)

    def test_log_decision_with_invalid_data(self, mock_db_session):
        """Test log_decision with invalid data."""
        with patch('src.conport.main.decision_service.create') as mock_create:
            mock_create.side_effect = ValueError("Invalid decision data")
            
            with pytest.raises(ValueError):
                main.log_decision(
                    workspace_id="test",
                    summary="",  # Invalid empty summary
                    db=mock_db_session
                )