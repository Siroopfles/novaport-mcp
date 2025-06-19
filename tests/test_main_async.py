"""Tests voor main CLI module functies - async versie."""

import pytest
import pytest_asyncio
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from src.conport import main
from src.conport.schemas.decision import DecisionCreate
from src.conport.schemas.progress import ProgressEntryCreate
from src.conport.schemas.system_pattern import SystemPatternCreate
from src.conport.schemas.custom_data import CustomDataCreate


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

    @pytest_asyncio.fixture
    async def mock_db_context(self, mock_db_session):
        """Mock async database context manager."""
        context_manager = AsyncMock()
        context_manager.__aenter__.return_value = mock_db_session
        context_manager.__aexit__.return_value = None
        return context_manager

    @pytest.mark.asyncio
    async def test_get_product_context(self, mock_db_context, workspace_id):
        """Test get_product_context async function."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.context_service.get_product_context') as mock_get:
                mock_context = Mock()
                mock_context.content = {"goal": "Test project"}
                mock_get.return_value = mock_context
                
                result = await main.get_product_context(workspace_id=workspace_id)
                
                assert result == {"goal": "Test project"}
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_context(self, mock_db_context, workspace_id):
        """Test get_active_context async function."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.context_service.get_active_context') as mock_get:
                mock_context = Mock()
                mock_context.content = {"current_focus": "Testing"}
                mock_get.return_value = mock_context
                
                result = await main.get_active_context(workspace_id=workspace_id)
                
                assert result == {"current_focus": "Testing"}
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_product_context(self, mock_db_context, workspace_id):
        """Test update_product_context async function."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.context_service.get_product_context') as mock_get:
                with patch('src.conport.main.context_service.update_context') as mock_update:
                    mock_context = Mock()
                    mock_get.return_value = mock_context
                    
                    updated_context = Mock()
                    updated_context.content = {"goal": "Updated project"}
                    mock_update.return_value = updated_context
                    
                    result = await main.update_product_context(
                        workspace_id=workspace_id,
                        content={"goal": "Updated project"}
                    )
                    
                    assert result == {"goal": "Updated project"}
                    mock_get.assert_called_once()
                    mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_active_context(self, mock_db_context, workspace_id):
        """Test update_active_context async function."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.context_service.get_active_context') as mock_get:
                with patch('src.conport.main.context_service.update_context') as mock_update:
                    mock_context = Mock()
                    mock_get.return_value = mock_context
                    
                    updated_context = Mock()
                    updated_context.content = {"current_focus": "Updated testing"}
                    mock_update.return_value = updated_context
                    
                    result = await main.update_active_context(
                        workspace_id=workspace_id,
                        content={"current_focus": "Updated testing"}
                    )
                    
                    assert result == {"current_focus": "Updated testing"}
                    mock_get.assert_called_once()
                    mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_decision(self, mock_db_context, workspace_id):
        """Test log_decision async function."""
        from src.conport.schemas.decision import DecisionCreate
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.decision_service.create') as mock_create:
                # Gebruik een dict met echte types
                mock_decision = {
                    "id": 1,
                    "summary": "Test decision",
                    "rationale": "Test rationale",
                    "implementation_details": None,
                    "tags": [],
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_create.return_value = mock_decision

                result = await main.log_decision(
                    workspace_id=workspace_id,
                    summary="Test decision",
                    rationale="Test rationale"
                )

                assert result.id == 1
                assert result.summary == "Test decision"
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_decisions(self, mock_db_context, workspace_id):
        """Test get_decisions async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.decision_service.get_multi') as mock_get:
                mock_decision = {
                    "id": 1,
                    "summary": "Decision 1",
                    "rationale": None,
                    "implementation_details": None,
                    "tags": [],
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_decisions = [mock_decision]
                mock_get.return_value = mock_decisions

                result = await main.get_decisions(workspace_id=workspace_id, limit=10)

                assert len(result) == 1
                assert result[0].id == 1
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_progress(self, mock_db_context, workspace_id):
        """Test log_progress async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.progress_service.create') as mock_create:
                mock_progress = {
                    "id": 1,
                    "status": "TODO",
                    "description": "Test task",
                    "parent_id": None,
                    "linked_item_type": None,
                    "linked_item_id": None,
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0),
                    "children": []
                }
                mock_create.return_value = mock_progress

                result = await main.log_progress(
                    workspace_id=workspace_id,
                    status="TODO",
                    description="Test task"
                )

                assert result.id == 1
                assert result.status == "TODO"
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_progress(self, mock_db_context, workspace_id):
        """Test get_progress async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.progress_service.get_multi') as mock_get:
                mock_progress = {
                    "id": 1,
                    "status": "TODO",
                    "description": "Test task",
                    "parent_id": None,
                    "linked_item_type": None,
                    "linked_item_id": None,
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0),
                    "children": []
                }
                mock_progress_list = [mock_progress]
                mock_get.return_value = mock_progress_list

                result = await main.get_progress(workspace_id=workspace_id, limit=10)

                assert len(result) == 1
                assert result[0].id == 1
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_system_pattern(self, mock_db_context, workspace_id):
        """Test log_system_pattern async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.system_pattern_service.create') as mock_create:
                mock_pattern = {
                    "id": 1,
                    "name": "Test Pattern",
                    "description": "Test description",
                    "implementation_notes": None,
                    "tags": [],
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_create.return_value = mock_pattern

                result = await main.log_system_pattern(
                    workspace_id=workspace_id,
                    name="Test Pattern",
                    description="Test description"
                )

                assert result.id == 1
                assert result.name == "Test Pattern"
                mock_create.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_system_patterns(self, mock_db_context, workspace_id):
        """Test get_system_patterns async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.system_pattern_service.get_multi') as mock_get:
                mock_pattern = {
                    "id": 1,
                    "name": "Pattern 1",
                    "description": "Test description",
                    "implementation_notes": None,
                    "tags": [],
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_patterns = [mock_pattern]
                mock_get.return_value = mock_patterns

                result = await main.get_system_patterns(workspace_id=workspace_id, limit=10)

                assert len(result) == 1
                assert result[0].id == 1
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_log_custom_data(self, mock_db_context, workspace_id):
        """Test log_custom_data async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.custom_data_service.upsert') as mock_upsert:
                mock_data = {
                    "id": 1,
                    "category": "test_category",
                    "key": "test_key",
                    "value": {"test": "data"},
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_upsert.return_value = mock_data

                result = await main.log_custom_data(
                    workspace_id=workspace_id,
                    category="test_category",
                    key="test_key",
                    value={"test": "data"}
                )

                assert result.category == "test_category"
                assert result.key == "test_key"
                mock_upsert.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_custom_data(self, mock_db_context, workspace_id):
        """Test get_custom_data async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.custom_data_service.get_by_category') as mock_get:
                mock_data = {
                    "id": 1,
                    "category": "test",
                    "key": "key1",
                    "value": {"test": "data"},
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "updated_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_data_list = [mock_data]
                mock_get.return_value = mock_data_list

                result = await main.get_custom_data(
                    workspace_id=workspace_id,
                    category="test"
                )

                assert len(result) == 1
                assert result[0].category == "test"
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_recent_activity_summary(self, mock_db_context, workspace_id):
        """Test get_recent_activity_summary async function."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.meta_service.get_recent_activity') as mock_get:
                mock_activity = {"decisions": [], "progress": []}
                mock_get.return_value = mock_activity
                
                result = await main.get_recent_activity_summary(workspace_id=workspace_id)
                
                assert "decisions" in result
                assert "progress" in result
                mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_link_conport_items(self, mock_db_context, workspace_id):
        """Test link_conport_items async function."""
        from datetime import datetime

        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            with patch('src.conport.main.link_service.create') as mock_create:
                mock_link = {
                    "id": 1,
                    "source_item_type": "decision",
                    "source_item_id": "1",
                    "target_item_type": "progress",
                    "target_item_id": "2",
                    "relationship_type": "implements",
                    "description": None,
                    "created_at": datetime(2024, 1, 1, 0, 0, 0),
                    "timestamp": datetime(2024, 1, 1, 0, 0, 0)
                }
                mock_create.return_value = mock_link

                result = await main.link_conport_items(
                    workspace_id=workspace_id,
                    source_item_type="decision",
                    source_item_id="1",
                    target_item_type="progress",
                    target_item_id="2",
                    relationship_type="implements"
                )

                assert result.id == 1
                assert result.source_item_type == "decision"
                mock_create.assert_called_once()


class TestMainAsyncErrorHandling:
    """Test error handling in main async functions."""

    @pytest_asyncio.fixture
    async def mock_db_context(self):
        """Mock async database context manager."""
        mock_db_session = Mock(spec=Session)
        context_manager = AsyncMock()
        context_manager.__aenter__.return_value = mock_db_session
        context_manager.__aexit__.return_value = None
        return context_manager

    @pytest.mark.asyncio
    async def test_update_product_context_validation_error(self, mock_db_context):
        """Test update_product_context with validation error."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            result = await main.update_product_context(workspace_id="test")
            
            # Should return MCPError when neither content nor patch_content provided
            assert hasattr(result, 'error')
            assert result.error == "Either 'content' or 'patch_content' must be provided."

    @pytest.mark.asyncio
    async def test_update_active_context_both_params_error(self, mock_db_context):
        """Test update_active_context with both content and patch_content."""
        with patch('src.conport.main.get_db_session_for_workspace', return_value=mock_db_context):
            result = await main.update_active_context(
                workspace_id="test",
                content={"test": "data"},
                patch_content={"test": "patch"}
            )
            
            # Should return MCPError when both params provided
            assert hasattr(result, 'error')
            assert result.error == "Provide either 'content' or 'patch_content', not both."

    @pytest.mark.asyncio
    async def test_with_db_session_missing_workspace_id(self):
        """Test decorator with missing workspace_id."""
        @main.with_db_session
        async def dummy_func(**kwargs):
            return "should not reach here"
        
        result = await dummy_func()
        assert hasattr(result, 'error')
        assert result.error == "workspace_id is a required argument."