"""Tests voor main CLI module functies - async versie."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session
from typing import List, Union

from src.novaport_mcp import main
from src.novaport_mcp.schemas.decision import DecisionCreate, DecisionRead
from src.novaport_mcp.schemas.progress import ProgressEntryCreate, ProgressEntryRead
from src.novaport_mcp.schemas.system_pattern import SystemPatternCreate, SystemPatternRead
from src.novaport_mcp.schemas.custom_data import CustomDataCreate, CustomDataRead
from src.novaport_mcp.schemas.link import LinkRead
from src.novaport_mcp.schemas.error import MCPError


class TestMainAsyncCLIFunctions:
    """Test main CLI async functions voor coverage."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        return Mock(spec=Session)

    @pytest.fixture
    def workspace_id(self):
        """Test workspace ID."""
        return "test_workspace"

    @pytest.mark.asyncio
    async def test_get_product_context(self, mock_db_session, workspace_id):
        """Test get_product_context async function."""
        with patch('src.novaport_mcp.main.context_service.get_product_context') as mock_get:
            mock_context = Mock()
            mock_context.content = {"goal": "Test project"}
            mock_get.return_value = mock_context
            
            token = main.db_session_context.set(mock_db_session)
            result = await main.get_product_context(workspace_id=workspace_id)
            main.db_session_context.reset(token)

            assert result == {"goal": "Test project"}
            mock_get.assert_called_once_with(mock_db_session)

    @pytest.mark.asyncio
    async def test_get_active_context(self, mock_db_session, workspace_id):
        """Test get_active_context async function."""
        with patch('src.novaport_mcp.main.context_service.get_active_context') as mock_get:
            mock_context = Mock()
            mock_context.content = {"current_focus": "Testing"}
            mock_get.return_value = mock_context
            
            token = main.db_session_context.set(mock_db_session)
            result = await main.get_active_context(workspace_id=workspace_id)
            main.db_session_context.reset(token)
            
            assert result == {"current_focus": "Testing"}
            mock_get.assert_called_once_with(mock_db_session)

    @pytest.mark.asyncio
    async def test_update_product_context(self, mock_db_session, workspace_id):
        """Test update_product_context async function."""
        with patch('src.novaport_mcp.main.context_service.get_product_context') as mock_get:
            with patch('src.novaport_mcp.main.context_service.update_context') as mock_update:
                mock_context = Mock()
                mock_get.return_value = mock_context
                
                updated_context = Mock()
                updated_context.content = {"goal": "Updated project"}
                mock_update.return_value = updated_context
                
                token = main.db_session_context.set(mock_db_session)
                result = await main.update_product_context(
                    workspace_id=workspace_id,
                    content={"goal": "Updated project"}
                )
                main.db_session_context.reset(token)
                
                assert result == {"goal": "Updated project"}
                mock_get.assert_called_once()
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_active_context(self, mock_db_session, workspace_id):
        """Test update_active_context async function."""
        with patch('src.novaport_mcp.main.context_service.get_active_context') as mock_get:
            with patch('src.novaport_mcp.main.context_service.update_context') as mock_update:
                mock_context = Mock()
                mock_get.return_value = mock_context
                
                updated_context = Mock()
                updated_context.content = {"current_focus": "Updated testing"}
                mock_update.return_value = updated_context
                
                token = main.db_session_context.set(mock_db_session)
                result = await main.update_active_context(
                    workspace_id=workspace_id,
                    content={"current_focus": "Updated testing"}
                )
                main.db_session_context.reset(token)
                
                assert result == {"current_focus": "Updated testing"}
                mock_get.assert_called_once()
                mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_decision(self, mock_db_session, workspace_id):
        """Test log_decision async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.decision_service.create') as mock_create:
            mock_decision = {
                "id": 1, "summary": "Test decision", "rationale": "Test rationale",
                "implementation_details": None, "tags": [], "timestamp": datetime.now()
            }
            mock_create.return_value = mock_decision

            token = main.db_session_context.set(mock_db_session)
            result = await main.log_decision(
                workspace_id=workspace_id,
                summary="Test decision",
                rationale="Test rationale"
            )
            main.db_session_context.reset(token)

            assert isinstance(result, DecisionRead)
            assert result.id == 1
            assert result.summary == "Test decision"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_decisions(self, mock_db_session, workspace_id):
        """Test get_decisions async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.decision_service.get_multi') as mock_get:
            mock_decision = {"id": 1, "summary": "Decision 1", "rationale": None,
                             "implementation_details": None, "tags": [], "timestamp": datetime.now()}
            mock_get.return_value = [mock_decision]

            token = main.db_session_context.set(mock_db_session)
            result = await main.get_decisions(workspace_id=workspace_id)
            main.db_session_context.reset(token)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_progress(self, mock_db_session, workspace_id):
        """Test log_progress async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.progress_service.create') as mock_create:
            mock_progress = {"id": 1, "status": "TODO", "description": "Test task",
                             "parent_id": None, "timestamp": datetime.now(), "children": []}
            mock_create.return_value = mock_progress

            token = main.db_session_context.set(mock_db_session)
            result = await main.log_progress(workspace_id=workspace_id, status="TODO", description="Test task")
            main.db_session_context.reset(token)

            assert isinstance(result, ProgressEntryRead)
            assert result.id == 1
            assert result.status == "TODO"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_progress(self, mock_db_session, workspace_id):
        """Test get_progress async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.progress_service.get_multi') as mock_get:
            mock_progress = {"id": 1, "status": "TODO", "description": "Test task",
                             "parent_id": None, "timestamp": datetime.now(), "children": []}
            mock_get.return_value = [mock_progress]

            token = main.db_session_context.set(mock_db_session)
            result = await main.get_progress(workspace_id=workspace_id)
            main.db_session_context.reset(token)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_system_pattern(self, mock_db_session, workspace_id):
        """Test log_system_pattern async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.system_pattern_service.create') as mock_create:
            mock_pattern = {"id": 1, "name": "Test Pattern", "description": "Test description",
                            "tags": [], "timestamp": datetime.now()}
            mock_create.return_value = mock_pattern

            token = main.db_session_context.set(mock_db_session)
            result = await main.log_system_pattern(workspace_id=workspace_id, name="Test Pattern", description="Test description")
            main.db_session_context.reset(token)

            assert isinstance(result, SystemPatternRead)
            assert result.id == 1
            assert result.name == "Test Pattern"
            mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_system_patterns(self, mock_db_session, workspace_id):
        """Test get_system_patterns async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.system_pattern_service.get_multi') as mock_get:
            mock_pattern = {"id": 1, "name": "Pattern 1", "description": None, "tags": [], "timestamp": datetime.now()}
            mock_get.return_value = [mock_pattern]

            token = main.db_session_context.set(mock_db_session)
            result = await main.get_system_patterns(workspace_id=workspace_id)
            main.db_session_context.reset(token)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].id == 1
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_custom_data(self, mock_db_session, workspace_id):
        """Test log_custom_data async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.custom_data_service.upsert') as mock_upsert:
            mock_data = {"id": 1, "category": "test_category", "key": "test_key", "value": {"test": "data"}, "timestamp": datetime.now()}
            mock_upsert.return_value = mock_data

            token = main.db_session_context.set(mock_db_session)
            result = await main.log_custom_data(
                workspace_id=workspace_id,
                category="test_category",
                key="test_key",
                value={"test": "data"}
            )
            main.db_session_context.reset(token)

            assert isinstance(result, CustomDataRead)
            assert result.category == "test_category"
            assert result.key == "test_key"
            mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_custom_data(self, mock_db_session, workspace_id):
        """Test get_custom_data async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.custom_data_service.get_by_category') as mock_get:
            mock_data = {"id": 1, "category": "test", "key": "key1", "value": {"test": "data"}, "timestamp": datetime.now()}
            mock_get.return_value = [mock_data]

            token = main.db_session_context.set(mock_db_session)
            result = await main.get_custom_data(workspace_id=workspace_id, category="test")
            main.db_session_context.reset(token)

            assert isinstance(result, list)
            assert len(result) == 1
            assert result[0].category == "test"
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_activity_summary(self, mock_db_session, workspace_id):
        """Test get_recent_activity_summary async function."""
        with patch('src.novaport_mcp.main.meta_service.get_recent_activity') as mock_get:
            mock_activity = {"decisions": [], "progress": [], "system_patterns": []}
            mock_get.return_value = mock_activity
            
            token = main.db_session_context.set(mock_db_session)
            result = await main.get_recent_activity_summary(workspace_id=workspace_id)
            main.db_session_context.reset(token)
            
            assert isinstance(result, dict)
            assert "decisions" in result
            assert "progress" in result
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_conport_items(self, mock_db_session, workspace_id):
        """Test link_conport_items async function."""
        from datetime import datetime

        with patch('src.novaport_mcp.main.link_service.create') as mock_create:
            mock_link = {"id": 1, "source_item_type": "decision", "source_item_id": "1",
                         "target_item_type": "progress", "target_item_id": "2",
                         "relationship_type": "implements", "description": None, "timestamp": datetime.now()}
            mock_create.return_value = mock_link

            token = main.db_session_context.set(mock_db_session)
            result = await main.link_conport_items(
                workspace_id=workspace_id,
                source_item_type="decision",
                source_item_id="1",
                target_item_type="progress",
                target_item_id="2",
                relationship_type="implements"
            )
            main.db_session_context.reset(token)

            assert isinstance(result, LinkRead)
            assert result.id == 1
            assert result.source_item_type == "decision"
            mock_create.assert_called_once()


class TestMainAsyncErrorHandling:
    """Test error handling in main async functions."""

    @pytest.mark.asyncio
    async def test_update_product_context_validation_error(self):
        """Test update_product_context with validation error."""
        result = await main.update_product_context(workspace_id="test")
        
        assert isinstance(result, MCPError)
        assert "Either 'content' or 'patch_content' must be provided." in result.error

    @pytest.mark.asyncio
    async def test_update_active_context_both_params_error(self):
        """Test update_active_context with both content and patch_content."""
        result = await main.update_active_context(
            workspace_id="test",
            content={"test": "data"},
            patch_content={"test": "patch"}
        )
        
        assert isinstance(result, MCPError)
        assert "Provide either 'content' or 'patch_content', not both." in result.error

    @pytest.mark.asyncio
    async def test_with_db_session_missing_workspace_id(self):
        """Test decorator with missing workspace_id."""
        @main.with_db_session
        async def dummy_func():
            return "should not reach here"
        
        result = await dummy_func()
        assert isinstance(result, MCPError)
        assert "workspace_id is a required argument." in result.error