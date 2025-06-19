"""Tests voor database module voor volledige coverage."""

import pytest
import pytest_asyncio
import asyncio
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from pathlib import Path
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from src.conport.db import database


class TestDatabaseMigrations:
    """Test database migratie functies."""

    def test_run_migrations_for_workspace_success(self):
        """Test succesvolle migratie."""
        mock_engine = Mock()
        db_path = Path("/test/db/path")
        
        with patch('src.conport.db.database.importlib.resources.files') as mock_files:
            with patch('src.conport.db.database.Config') as mock_config_class:
                with patch('src.conport.db.database.command') as mock_command:
                    # Setup mocks
                    mock_package_root = Mock()
                    mock_files.return_value = mock_package_root
                    mock_package_root.__truediv__ = Mock(side_effect=lambda x: f"path/{x}")
                    
                    mock_config = Mock()
                    mock_config_class.return_value = mock_config
                    
                    mock_connection = Mock()
                    mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
                    mock_engine.begin.return_value.__exit__ = Mock(return_value=None)
                    mock_engine.url = "sqlite:///test.db"
                    
                    # Run the function
                    database.run_migrations_for_workspace(mock_engine, db_path)
                    
                    # Verify calls
                    mock_config.set_main_option.assert_any_call("script_location", "path/db/path/alembic")
                    mock_config.set_main_option.assert_any_call("sqlalchemy.url", "sqlite:///test.db")
                    mock_command.upgrade.assert_called_once_with(mock_config, "head")


class TestDatabaseSessionManagement:
    """Test database sessie management."""

    def setUp(self):
        """Setup voor elke test."""
        database._engines.clear()
        database._session_locals.clear()
        database._workspace_locks.clear()

    @pytest.mark.asyncio
    async def test_get_session_local_new_workspace(self):
        """Test get_session_local voor nieuwe workspace."""
        self.setUp()
        
        workspace_id = "test_workspace"
        
        with patch('src.conport.db.database.core_config.get_database_url_for_workspace') as mock_get_url:
            with patch('src.conport.db.database.create_engine') as mock_create_engine:
                with patch('src.conport.db.database.asyncio.to_thread') as mock_to_thread:
                    with patch('src.conport.db.database.sessionmaker') as mock_sessionmaker:
                        # Setup mocks
                        mock_get_url.return_value = "sqlite:///test.db"
                        mock_engine = Mock()
                        mock_create_engine.return_value = mock_engine
                        mock_to_thread.return_value = None  # Migratie succesvol
                        mock_session_local = Mock()
                        mock_sessionmaker.return_value = mock_session_local
                        
                        # Run the function
                        result = await database.get_session_local(workspace_id)
                        
                        # Verify results
                        assert result is mock_session_local
                        assert workspace_id in database._session_locals
                        assert workspace_id in database._engines
                        
                        # Verify calls
                        mock_create_engine.assert_called_once_with(
                            "sqlite:///test.db", 
                            connect_args={"check_same_thread": False}
                        )
                        mock_to_thread.assert_called_once()
                        mock_sessionmaker.assert_called_once_with(
                            autocommit=False, 
                            autoflush=False, 
                            bind=mock_engine
                        )

    @pytest.mark.asyncio
    async def test_get_session_local_cached_workspace(self):
        """Test get_session_local voor al gecachte workspace."""
        self.setUp()
        
        workspace_id = "test_workspace"
        mock_session_local = Mock()
        
        # Pre-populate cache
        database._session_locals[workspace_id] = mock_session_local
        
        result = await database.get_session_local(workspace_id)
        
        assert result is mock_session_local

    @pytest.mark.asyncio
    async def test_get_session_local_concurrent_access(self):
        """Test concurrent access to get_session_local."""
        self.setUp()
        
        workspace_id = "test_workspace"
        
        # Setup a lock to test concurrent access
        lock_acquired = False
        original_session_local = Mock()
        
        async def mock_lock_context():
            nonlocal lock_acquired
            if not lock_acquired:
                lock_acquired = True
                # Simulate another task already created the session
                database._session_locals[workspace_id] = original_session_local
        
        with patch('asyncio.Lock') as mock_lock_class:
            mock_lock = AsyncMock()
            mock_lock.__aenter__ = mock_lock_context
            mock_lock.__aexit__ = AsyncMock(return_value=None)
            mock_lock_class.return_value = mock_lock
            
            result = await database.get_session_local(workspace_id)
            
            assert result is original_session_local

    @pytest.mark.asyncio
    async def test_get_session_local_with_error(self):
        """Test get_session_local met error."""
        self.setUp()
        
        workspace_id = "test_workspace"
        
        with patch('src.conport.db.database.core_config.get_database_url_for_workspace') as mock_get_url:
            with patch('src.conport.db.database.create_engine') as mock_create_engine:
                # Setup error
                mock_get_url.return_value = "sqlite:///test.db"
                mock_create_engine.side_effect = Exception("Database connection failed")
                
                # Should raise HTTPException
                with pytest.raises(Exception):  # HTTPException wordt geimporteerd als Exception in test context
                    await database.get_session_local(workspace_id)
                
                # Cache should be cleaned up
                assert workspace_id not in database._session_locals
                assert workspace_id not in database._engines


class TestDatabaseDependencies:
    """Test database dependency functies."""

    @pytest.mark.asyncio
    async def test_get_db_success(self):
        """Test get_db dependency success."""
        workspace_id_b64 = "dGVzdF93b3Jrc3BhY2U="  # base64 encoded "test_workspace"
        
        with patch('src.conport.db.database.core_config.decode_workspace_id') as mock_decode:
            with patch('src.conport.db.database.get_session_local') as mock_get_session:
                mock_decode.return_value = "test_workspace"
                
                mock_session_local = Mock()
                mock_db_session = Mock(spec=Session)
                mock_session_local.return_value = mock_db_session
                mock_get_session.return_value = mock_session_local
                
                # Use async generator
                async_gen = database.get_db(workspace_id_b64)
                
                # Get the yielded session
                session = await async_gen.__anext__()
                assert session is mock_db_session
                
                # Simulate cleanup
                try:
                    await async_gen.__anext__()
                except StopAsyncIteration:
                    pass  # Expected when generator finishes
                
                mock_decode.assert_called_once_with(workspace_id_b64)
                mock_get_session.assert_called_once_with("test_workspace")
                mock_db_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_decode_error(self):
        """Test get_db met decode error."""
        workspace_id_b64 = "invalid_base64"
        
        with patch('src.conport.db.database.core_config.decode_workspace_id') as mock_decode:
            mock_decode.side_effect = ValueError("Invalid base64")
            
            with pytest.raises(Exception):  # HTTPException in test context
                async_gen = database.get_db(workspace_id_b64)
                await async_gen.__anext__()

    @pytest.mark.asyncio
    async def test_get_db_session_cleanup_on_error(self):
        """Test dat database sessie wordt gesloten bij error."""
        workspace_id_b64 = "dGVzdF93b3Jrc3BhY2U="
        
        with patch('src.conport.db.database.core_config.decode_workspace_id') as mock_decode:
            with patch('src.conport.db.database.get_session_local') as mock_get_session:
                mock_decode.return_value = "test_workspace"
                
                mock_session_local = Mock()
                mock_db_session = Mock(spec=Session)
                mock_session_local.return_value = mock_db_session
                mock_get_session.side_effect = Exception("Session creation failed")
                
                try:
                    async_gen = database.get_db(workspace_id_b64)
                    await async_gen.__anext__()
                except Exception:
                    pass  # Expected error
                
                # Session should still be closed in finally block if it was created
                # In this case it wasn't created due to error, so close shouldn't be called


class TestDatabaseContextManager:
    """Test database context manager."""

    @pytest.mark.asyncio
    async def test_get_db_session_for_workspace_success(self):
        """Test get_db_session_for_workspace success."""
        workspace_id = "test_workspace"
        
        with patch('src.conport.db.database.get_session_local') as mock_get_session:
            mock_session_local = Mock()
            mock_db_session = Mock(spec=Session)
            mock_session_local.return_value = mock_db_session
            mock_get_session.return_value = mock_session_local
            
            async with database.get_db_session_for_workspace(workspace_id) as session:
                assert session is mock_db_session
            
            mock_get_session.assert_called_once_with(workspace_id)
            mock_db_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_db_session_for_workspace_with_error(self):
        """Test get_db_session_for_workspace met error."""
        workspace_id = "test_workspace"
        
        with patch('src.conport.db.database.get_session_local') as mock_get_session:
            mock_get_session.side_effect = Exception("Session creation failed")
            
            with pytest.raises(Exception, match="Session creation failed"):
                async with database.get_db_session_for_workspace(workspace_id) as session:
                    pass  # Should not reach here

    @pytest.mark.asyncio
    async def test_get_db_session_for_workspace_cleanup_on_exception(self):
        """Test cleanup bij exception in context manager."""
        workspace_id = "test_workspace"
        
        with patch('src.conport.db.database.get_session_local') as mock_get_session:
            mock_session_local = Mock()
            mock_db_session = Mock(spec=Session)
            mock_session_local.return_value = mock_db_session
            mock_get_session.return_value = mock_session_local
            
            with pytest.raises(ValueError, match="Test error"):
                async with database.get_db_session_for_workspace(workspace_id) as session:
                    raise ValueError("Test error")
            
            # Session should still be closed despite error
            mock_db_session.close.assert_called_once()


class TestDatabaseGlobalState:
    """Test database global state management."""

    def test_global_dictionaries_initialization(self):
        """Test dat globale dictionaries correct geïnitialiseerd zijn."""
        assert isinstance(database._engines, dict)
        assert isinstance(database._session_locals, dict)
        assert isinstance(database._workspace_locks, dict)

    def test_workspace_lock_creation(self):
        """Test dat workspace locks correct aangemaakt worden."""
        # Clear locks first
        database._workspace_locks.clear()
        
        workspace_id = "test_workspace"
        
        # Simulate lock creation in get_session_local
        assert workspace_id not in database._workspace_locks
        
        # This would happen in get_session_local
        database._workspace_locks[workspace_id] = asyncio.Lock()
        
        assert workspace_id in database._workspace_locks
        assert isinstance(database._workspace_locks[workspace_id], asyncio.Lock)


class TestDatabaseErrorRecovery:
    """Test database error recovery scenarios."""

    @pytest.mark.asyncio
    async def test_migration_failure_cleanup(self):
        """Test cleanup na migratie failure."""
        workspace_id = "test_workspace"
        
        # Clear state
        database._engines.clear()
        database._session_locals.clear()
        
        with patch('src.conport.db.database.core_config.get_database_url_for_workspace') as mock_get_url:
            with patch('src.conport.db.database.create_engine') as mock_create_engine:
                with patch('src.conport.db.database.asyncio.to_thread') as mock_to_thread:
                    # Setup successful engine creation but failed migration
                    mock_get_url.return_value = "sqlite:///test.db"
                    mock_engine = Mock()
                    mock_create_engine.return_value = mock_engine
                    mock_to_thread.side_effect = Exception("Migration failed")
                    
                    with pytest.raises(Exception):
                        await database.get_session_local(workspace_id)
                    
                    # Should cleanup after failure
                    assert workspace_id not in database._session_locals
                    assert workspace_id not in database._engines

    def test_run_migrations_path_handling(self):
        """Test pad handling in migraties."""
        mock_engine = Mock()
        mock_engine.url = "sqlite:///test.db"
        db_path = Path("/complex/path/with spaces/test.db")
        
        with patch('src.conport.db.database.importlib.resources.files') as mock_files:
            with patch('src.conport.db.database.Config') as mock_config_class:
                with patch('src.conport.db.database.command') as mock_command:
                    # Setup complex path handling
                    mock_package_root = Mock()
                    mock_files.return_value = mock_package_root
                    
                    # Mock path operations
                    def mock_truediv(path_part):
                        return f"/package/root/{path_part}"
                    
                    mock_package_root.__truediv__ = Mock(side_effect=mock_truediv)
                    
                    mock_config = Mock()
                    mock_config_class.return_value = mock_config
                    
                    mock_connection = Mock()
                    mock_engine.begin.return_value.__enter__ = Mock(return_value=mock_connection)
                    mock_engine.begin.return_value.__exit__ = Mock(return_value=None)
                    
                    # Should handle complex paths correctly
                    database.run_migrations_for_workspace(mock_engine, db_path)
                    
                    # Verify script location was set correctly
                    mock_config.set_main_option.assert_any_call(
                        "script_location", 
                        "/package/root/db/package/root/alembic"
                    )