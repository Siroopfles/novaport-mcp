# FILE: siroopfles-novaport-mcp/src/conport/main.py

import datetime
import inspect
import logging
from functools import wraps
from pathlib import Path
from typing import Annotated, Any, Callable, Dict, List, Optional, Union

import dictdiffer  # type: ignore
from fastmcp import FastMCP
from pydantic import Field, TypeAdapter, ValidationError
from sqlalchemy.orm import Session

from .db import models
from .db.database import get_db_session_for_workspace
from .schemas import batch as batch_schema
from .schemas import context as context_schema
from .schemas import custom_data as cd_schema
from .schemas import decision as decision_schema
from .schemas import link as link_schema
from .schemas import progress as progress_schema
from .schemas import system_pattern as sp_schema
from .schemas.custom_data import CustomDataRead
from .schemas.decision import DecisionRead
from .schemas.error import MCPError
from .schemas.history import HistoryRead
from .schemas.link import LinkRead
from .schemas.progress import ProgressEntryRead, ProgressEntryUpdate
from .schemas.system_pattern import SystemPatternRead
from .services import (
    context_service,
    custom_data_service,
    decision_service,
    history_service,
    io_service,
    link_service,
    meta_service,
    progress_service,
    system_pattern_service,
    vector_service,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
log = logging.getLogger(__name__)

# Initialize the history service to register event listeners
_history_service_initialized = history_service

mcp_server = FastMCP(name="NovaPort-MCP")


# --- Decorator for DB Session (REMOVED) ---
# The @with_db_session decorator has been removed.
# Its logic is now inlined into each tool function that needs a database session.


# --- Tool Definitions (Workspace-Aware, Async, Refactored) ---


@mcp_server.tool()
async def get_product_context(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
) -> Union[Any, MCPError]:
    """Retrieves the overall project goals, features, and architecture."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        return context_service.get_product_context(db).content


@mcp_server.tool()
async def update_product_context(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    content: Annotated[
        Optional[Dict[str, Any]],
        Field(
            None,
            description="The full new context content as a dictionary. Overwrites existing.",
        ),
    ] = None,
    patch_content: Annotated[
        Optional[Dict[str, Any]],
        Field(
            None,
            description="A dictionary of changes to apply to the existing context (add/update keys).",
        ),
    ] = None,
) -> Union[Any, MCPError]:
    """Updates the product context.

    Accepts full `content` (object) or `patch_content` (object) for partial
    updates (use `__DELETE__` as a value in patch to remove a key).
    """
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    if content is None and patch_content is None:
        return MCPError(error="Either 'content' or 'patch_content' must be provided.")
    if content is not None and patch_content is not None:
        return MCPError(error="Provide either 'content' or 'patch_content', not both.")

    async with get_db_session_for_workspace(workspace_id) as db:
        try:
            update_data = context_schema.ContextUpdate(
                content=content, patch_content=patch_content
            )
            instance = context_service.get_product_context(db)
            updated = context_service.update_context(db, instance, update_data)
            return updated.content
        except ValidationError as e:
            return MCPError(error="Validation error", details=str(e))


@mcp_server.tool()
async def get_active_context(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
) -> Union[Any, MCPError]:
    """Retrieves the current working focus, recent changes, and open issues."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        return context_service.get_active_context(db).content


@mcp_server.tool()
async def update_active_context(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    content: Annotated[
        Optional[Dict[str, Any]],
        Field(
            None,
            description="The full new context content as a dictionary. Overwrites existing.",
        ),
    ] = None,
    patch_content: Annotated[
        Optional[Dict[str, Any]],
        Field(
            None,
            description="A dictionary of changes to apply to the existing context (add/update keys).",
        ),
    ] = None,
) -> Union[Any, MCPError]:
    """Updates the active context.

    Accepts full `content` (object) or `patch_content` (object) for partial
    updates (use `__DELETE__` as a value in patch to remove a key).
    """
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    if content is None and patch_content is None:
        return MCPError(error="Either 'content' or 'patch_content' must be provided.")
    if content is not None and patch_content is not None:
        return MCPError(error="Provide either 'content' or 'patch_content', not both.")

    async with get_db_session_for_workspace(workspace_id) as db:
        try:
            update_data = context_schema.ContextUpdate(
                content=content, patch_content=patch_content
            )
            instance = context_service.get_active_context(db)
            updated = context_service.update_context(db, instance, update_data)
            return updated.content
        except ValidationError as e:
            return MCPError(error="Validation error", details=str(e))


@mcp_server.tool()
async def log_decision(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    summary: Annotated[str, Field(description="A concise summary of the decision.")],
    rationale: Annotated[
        Optional[str], Field(None, description="The reasoning behind the decision.")
    ] = None,
    implementation_details: Annotated[
        Optional[str],
        Field(
            None, description="Details about how the decision will be/was implemented."
        ),
    ] = None,
    tags: Annotated[
        Optional[List[str]],
        Field(None, description="Optional tags for categorization."),
    ] = None,
) -> Union[DecisionRead, MCPError]:
    """Logs an architectural or implementation decision."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        data = decision_schema.DecisionCreate(
            summary=summary,
            rationale=rationale,
            implementation_details=implementation_details,
            tags=tags or [],
        )
        created = decision_service.create(db, workspace_id, data)
        return DecisionRead.model_validate(created)


@mcp_server.tool()
async def get_decisions(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    limit: Annotated[
        Optional[int],
        Field(
            None,
            description="Maximum number of decisions to return (most recent first).",
        ),
    ] = None,
    tags_filter_include_all: Annotated[
        Optional[List[str]],
        Field(None, description="Filter: items must include ALL of these tags."),
    ] = None,
    tags_filter_include_any: Annotated[
        Optional[List[str]],
        Field(
            None, description="Filter: items must include AT LEAST ONE of these tags."
        ),
    ] = None,
) -> Union[List[DecisionRead], MCPError]:
    """Retrieves logged decisions."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        decisions = decision_service.get_multi(
            db,
            limit=limit or 100,
            tags_all=tags_filter_include_all,
            tags_any=tags_filter_include_any,
        )
        return [DecisionRead.model_validate(d) for d in decisions]


@mcp_server.tool()
async def delete_decision_by_id(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    decision_id: int,
) -> Union[Dict[str, Any], MCPError]:
    """Deletes a decision by its ID."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        deleted = decision_service.delete(db, workspace_id, decision_id)
        return (
            {"status": "success", "id": decision_id}
            if deleted
            else MCPError(
                error=f"Decision with ID {decision_id} not found",
                details={"id": decision_id},
            )
        )


@mcp_server.tool()
async def log_progress(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    status: Annotated[
        str, Field(description="Current status (e.g., 'TODO', 'IN_PROGRESS', 'DONE').")
    ],
    description: Annotated[
        str, Field(description="Description of the progress or task.")
    ],
    parent_id: Annotated[
        Optional[int],
        Field(None, description="ID of the parent task, if this is a subtask."),
    ] = None,
    linked_item_type: Annotated[
        Optional[str],
        Field(None, description="Optional: Type of the ConPort item to link."),
    ] = None,
    linked_item_id: Annotated[
        Optional[str],
        Field(None, description="Optional: ID/key of the ConPort item to link."),
    ] = None,
    link_relationship_type: Annotated[
        str,
        Field(
            "relates_to_progress",
            description="Relationship type for the automatic link.",
        ),
    ] = "relates_to_progress",
) -> Union[ProgressEntryRead, MCPError]:
    """Logs a progress entry or task status."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        entry_data = progress_schema.ProgressEntryCreate(
            status=status, description=description, parent_id=parent_id
        )
        created = progress_service.create(
            db,
            workspace_id,
            entry_data,
            linked_item_type,
            linked_item_id,
            link_relationship_type,
        )
        return ProgressEntryRead.model_validate(created)


@mcp_server.tool()
async def get_progress(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    limit: Annotated[
        Optional[int],
        Field(
            None, description="Maximum number of entries to return (most recent first)."
        ),
    ] = None,
    status_filter: Annotated[
        Optional[str], Field(None, description="Filter entries by status.")
    ] = None,
    parent_id_filter: Annotated[
        Optional[int], Field(None, description="Filter entries by parent task ID.")
    ] = None,
) -> Union[List[ProgressEntryRead], MCPError]:
    """Retrieves progress entries."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        entries = progress_service.get_multi(
            db, limit=limit or 50, status=status_filter, parent_id=parent_id_filter
        )
        return [ProgressEntryRead.model_validate(p) for p in entries]


@mcp_server.tool()
async def update_progress(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    progress_id: Annotated[
        int, Field(description="The ID of the progress entry to update.")
    ],
    status: Annotated[
        Optional[str],
        Field(None, description="New status (e.g., 'TODO', 'IN_PROGRESS', 'DONE')."),
    ] = None,
    description: Annotated[
        Optional[str],
        Field(None, description="New description of the progress or task."),
    ] = None,
    parent_id: Annotated[
        Optional[int],
        Field(None, description="New ID of the parent task, if changing."),
    ] = None,
) -> Union[ProgressEntryRead, MCPError]:
    """Updates an existing progress entry."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    update_data = ProgressEntryUpdate(
        status=status, description=description, parent_id=parent_id
    )
    if not update_data.model_dump(exclude_unset=True):
        return MCPError(error="No update fields provided.")

    async with get_db_session_for_workspace(workspace_id) as db:
        updated = progress_service.update(db, progress_id, update_data)
        return (
            ProgressEntryRead.model_validate(updated)
            if updated
            else MCPError(error="Progress entry not found", details={"id": progress_id})
        )


@mcp_server.tool()
async def delete_progress_by_id(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    progress_id: int,
) -> Union[Dict[str, Any], MCPError]:
    """Deletes a progress entry by its ID."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        deleted = progress_service.delete(db, workspace_id, progress_id)
        return (
            {"status": "success", "id": progress_id}
            if deleted
            else MCPError(
                error=f"Progress entry with ID {progress_id} not found",
                details={"id": progress_id},
            )
        )


@mcp_server.tool()
async def log_system_pattern(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    name: Annotated[str, Field(description="Unique name for the system pattern.")],
    description: Annotated[
        Optional[str], Field(None, description="Description of the pattern.")
    ] = None,
    tags: Annotated[
        Optional[List[str]],
        Field(None, description="Optional tags for categorization."),
    ] = None,
) -> Union[SystemPatternRead, MCPError]:
    """Logs or updates a system/coding pattern."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        pattern_data = sp_schema.SystemPatternCreate(
            name=name, description=description, tags=tags or []
        )
        created = system_pattern_service.create(db, workspace_id, pattern_data)
        return SystemPatternRead.model_validate(created)


@mcp_server.tool()
async def get_system_patterns(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    tags_filter_include_all: Annotated[
        Optional[List[str]],
        Field(None, description="Filter: items must include ALL of these tags."),
    ] = None,
    tags_filter_include_any: Annotated[
        Optional[List[str]],
        Field(
            None, description="Filter: items must include AT LEAST ONE of these tags."
        ),
    ] = None,
) -> Union[List[SystemPatternRead], MCPError]:
    """Retrieves system patterns."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        patterns = system_pattern_service.get_multi(
            db, tags_all=tags_filter_include_all, tags_any=tags_filter_include_any
        )
        return [SystemPatternRead.model_validate(p) for p in patterns]


@mcp_server.tool()
async def delete_system_pattern_by_id(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    pattern_id: int,
) -> Union[Dict[str, Any], MCPError]:
    """Deletes a system pattern by its ID."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        deleted = system_pattern_service.delete(db, workspace_id, pattern_id)
        return (
            {"status": "success", "id": pattern_id}
            if deleted
            else MCPError(error="System pattern not found", details={"id": pattern_id})
        )


@mcp_server.tool()
async def log_custom_data(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    category: Annotated[str, Field(description="Category for the custom data.")],
    key: Annotated[
        str, Field(description="Key for the custom data (unique within category).")
    ],
    value: Annotated[
        Any, Field(description="The custom data value (JSON serializable).")
    ],
) -> Union[CustomDataRead, MCPError]:
    """Stores/updates a custom key-value entry under a category. Value is JSON-serializable."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        data = cd_schema.CustomDataCreate(category=category, key=key, value=value)
        created = custom_data_service.upsert(db, workspace_id, data)
        return CustomDataRead.model_validate(created)


@mcp_server.tool()
async def get_custom_data(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    category: Annotated[str, Field(description="Filter by category.")],
    key: Annotated[
        Optional[str], Field(None, description="Filter by key (requires category).")
    ] = None,
) -> Union[List[CustomDataRead], MCPError]:
    """Retrieves custom data."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        if key:
            items = [custom_data_service.get(db, category, key)]
        else:
            items = list(custom_data_service.get_by_category(db, category))
        return [CustomDataRead.model_validate(i) for i in items if i]


@mcp_server.tool()
async def delete_custom_data(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    category: Annotated[str, Field(description="Category of the data to delete.")],
    key: Annotated[str, Field(description="Key of the data to delete.")],
) -> Union[Dict[str, Any], MCPError]:
    """Deletes a specific custom data entry."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        deleted = custom_data_service.delete(db, workspace_id, category, key)
        data_id = f"{category}/{key}"
        return (
            {"status": "success", "category": category, "key": key}
            if deleted
            else MCPError(
                error=f"Custom data with ID {data_id} not found",
                details={"category": category, "key": key},
            )
        )


@mcp_server.tool()
async def export_conport_to_markdown(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    output_path: Annotated[
        Optional[str],
        Field(
            None, description="Optional output directory path relative to workspace_id."
        ),
    ] = None,
) -> Union[Dict[str, Any], MCPError]:
    """Exports ConPort data to markdown files."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        output_dir = Path(workspace_id) / (output_path or "conport_export")
        return io_service.export_to_markdown(db, output_dir)


@mcp_server.tool()
async def import_markdown_to_conport(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    input_path: Annotated[
        Optional[str],
        Field(
            None, description="Optional input directory path containing markdown files."
        ),
    ] = None,
) -> Union[Dict[str, Any], MCPError]:
    """Imports data from markdown files into ConPort."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        input_dir = Path(workspace_id) / (input_path or "conport_export")
        return io_service.import_from_markdown(db, workspace_id, input_dir)


@mcp_server.tool()
async def link_conport_items(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    source_item_type: Annotated[str, Field(description="Type of the source item.")],
    source_item_id: Annotated[str, Field(description="ID or key of the source item.")],
    target_item_type: Annotated[str, Field(description="Type of the target item.")],
    target_item_id: Annotated[str, Field(description="ID or key of the target item.")],
    relationship_type: Annotated[str, Field(description="Nature of the link.")],
    description: Annotated[
        Optional[str], Field(None, description="Optional description for the link.")
    ] = None,
) -> Union[LinkRead, MCPError]:
    """Creates a relationship link between two ConPort items."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        link_data = link_schema.LinkCreate(
            source_item_type=source_item_type,
            source_item_id=source_item_id,
            target_item_type=target_item_type,
            target_item_id=target_item_id,
            relationship_type=relationship_type,
            description=description,
        )
        created = link_service.create(db, link_data)
        return LinkRead.model_validate(created)


@mcp_server.tool()
async def get_linked_items(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    item_type: Annotated[str, Field(description="Type of the item to find links for.")],
    item_id: Annotated[
        str, Field(description="ID or key of the item to find links for.")
    ],
    limit: Annotated[
        Optional[int], Field(None, description="Maximum number of links to return.")
    ] = None,
) -> Union[List[LinkRead], MCPError]:
    """Retrieves items linked to a specific item."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        links = link_service.get_for_item(db, item_type, item_id, limit=limit or 50)
        return [LinkRead.model_validate(link_item) for link_item in links]


@mcp_server.tool()
async def search_decisions_fts(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    query_term: Annotated[
        str, Field(description="The term to search for in decisions.")
    ],
    limit: Annotated[
        Optional[int], Field(None, description="Maximum number of search results.")
    ] = None,
) -> Union[List[DecisionRead], MCPError]:
    """Full-text search across decision fields."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        decisions = decision_service.search_fts(db, query=query_term, limit=limit or 10)
        return [DecisionRead.model_validate(d) for d in decisions]


@mcp_server.tool()
async def search_custom_data_value_fts(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    query_term: Annotated[str, Field(description="The term to search for.")],
    category_filter: Annotated[
        Optional[str],
        Field(None, description="Optional: Filter results to this category."),
    ] = None,
    limit: Annotated[
        Optional[int], Field(None, description="Maximum number of results.")
    ] = None,
) -> Union[List[CustomDataRead], MCPError]:
    """Full-text search across all custom data values, categories, and keys."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        items = custom_data_service.search_fts(
            db, query=query_term, category=category_filter, limit=limit or 10
        )
        return [CustomDataRead.model_validate(i) for i in items]


@mcp_server.tool()
async def search_project_glossary_fts(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    query_term: Annotated[
        str, Field(description="The term to search for in the glossary.")
    ],
    limit: Annotated[
        Optional[int], Field(None, description="Maximum number of search results.")
    ] = None,
) -> Union[List[CustomDataRead], MCPError]:
    """Full-text search within the 'ProjectGlossary' custom data category."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        items = custom_data_service.search_fts(
            db, query=query_term, category="ProjectGlossary", limit=limit or 10
        )
        return [CustomDataRead.model_validate(i) for i in items]


@mcp_server.tool()
async def batch_log_items(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    item_type: Annotated[
        batch_schema.ItemType, Field(description="Type of items to log.")
    ],
    items: Annotated[List[Dict[str, Any]], Field(description="A list of item data.")],
) -> Union[Dict[str, Any], MCPError]:
    """Logs multiple items of the same type in a single call."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        try:
            result = meta_service.batch_log_items(db, workspace_id, item_type, items)
            if result.get("errors"):
                return MCPError(error="Some items failed validation", details=result)
            return result
        except ValidationError as e:
            return MCPError(error="Invalid batch request structure", details=e.errors())


@mcp_server.tool()
async def get_item_history(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    item_type: Annotated[
        str, Field(description="Type of item: 'product_context' or 'active_context'.")
    ],
    limit: Annotated[
        Optional[int], Field(None, description="Max number of history entries.")
    ] = None,
    version: Annotated[
        Optional[int], Field(None, description="Return a specific version.")
    ] = None,
    before_timestamp: Annotated[
        Optional[datetime.datetime],
        Field(None, description="Return entries before this timestamp."),
    ] = None,
    after_timestamp: Annotated[
        Optional[datetime.datetime],
        Field(None, description="Return entries after this timestamp."),
    ] = None,
) -> Union[List[HistoryRead], MCPError]:
    """Retrieves version history for Product or Active Context."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        history_model = None
        if item_type == "product_context":
            history_model = models.ProductContextHistory
        elif item_type == "active_context":
            history_model = models.ActiveContextHistory
        else:
            return MCPError(
                error="Invalid item_type for history retrieval",
                details={
                    "item_type": item_type,
                    "valid_types": ["product_context", "active_context"],
                },
            )

        query = db.query(history_model)
        if version:
            query = query.filter_by(version=version)
        if before_timestamp:
            query = query.filter(history_model.timestamp < before_timestamp)
        if after_timestamp:
            query = query.filter(history_model.timestamp > after_timestamp)

        records = query.order_by(history_model.version.desc()).limit(limit or 10).all()
        return [HistoryRead.model_validate(r) for r in records]


@mcp_server.tool()
async def get_recent_activity_summary(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    hours_ago: Annotated[
        Optional[int], Field(None, description="Look back this many hours.")
    ] = None,
    since_timestamp: Annotated[
        Optional[datetime.datetime],
        Field(None, description="Look back since this timestamp."),
    ] = None,
    limit_per_type: Annotated[
        int, Field(5, description="Maximum number of recent items to show per type.")
    ] = 5,
) -> Union[Dict[str, Any], MCPError]:
    """Provides a summary of recent ConPort activity (new/updated items)."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        since: Optional[datetime.datetime] = None
        if since_timestamp:
            since = since_timestamp
        elif hours_ago:
            since = datetime.datetime.utcnow() - datetime.timedelta(hours=hours_ago)

        activity = meta_service.get_recent_activity(
            db, limit=limit_per_type, since=since
        )
        return {
            "decisions": [
                DecisionRead.model_validate(d) for d in activity["decisions"]
            ],
            "progress": [
                ProgressEntryRead.model_validate(p) for p in activity["progress"]
            ],
            "system_patterns": [
                SystemPatternRead.model_validate(s)
                for s in activity["system_patterns"]
            ],
        }


@mcp_server.tool()
async def semantic_search_conport(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ],
    query_text: Annotated[str, Field(description="The natural language query text.")],
    top_k: Annotated[int, Field(5, description="Number of top results to return.")] = 5,
    filter_item_types: Annotated[
        Optional[List[str]],
        Field(
            None,
            description="Optional list of item types to filter by (e.g., ['decision', 'progress']).",
        ),
    ] = None,
    filter_tags_include_any: Annotated[
        Optional[List[str]],
        Field(None, description="Results must match AT LEAST ONE of these tags."),
    ] = None,
    filter_tags_include_all: Annotated[
        Optional[List[str]],
        Field(None, description="Results must match ALL of these tags."),
    ] = None,
    filter_custom_data_categories: Annotated[
        Optional[List[str]],
        Field(
            None,
            description=(
                "For custom_data, filter by these categories. "
                "Note: filter_custom_data_categories only applies when 'custom_data' "
                "is included in item_type. The filter uses simple category matching "
                "and may not support complex boolean logic depending on ChromaDB version."
            ),
        ),
    ] = None,
) -> Union[List[Dict[str, Any]], MCPError]:
    """Performs a semantic search across ConPort data with advanced filtering."""
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    try:
        and_conditions: List[Dict[str, Any]] = []

        if filter_item_types:
            and_conditions.append({"item_type": {"$in": filter_item_types}})

        if filter_custom_data_categories and "custom_data" in (filter_item_types or []):
            and_conditions.append(
                {"category": {"$in": filter_custom_data_categories}}
            )

        if filter_tags_include_all:
            for tag in filter_tags_include_all:
                and_conditions.append({"tags": {"$contains": tag}})

        if filter_tags_include_any:
            or_tag_conditions = [
                {"tags": {"$contains": tag}} for tag in filter_tags_include_any
            ]
            and_conditions.append({"$or": or_tag_conditions})

        filters = {"$and": and_conditions} if and_conditions else None

        search_results = vector_service.search(
            workspace_id=workspace_id,
            query_text=query_text,
            top_k=top_k,
            filters=filters,
        )
        return search_results

    except Exception as e:
        log.error(f"Semantic search failed for workspace '{workspace_id}': {e}")
        return MCPError(error="Semantic search failed", details=str(e))


def _to_camel_case(snake_str: str) -> str:
    """Helper to convert snake_case to CamelCase."""
    components = snake_str.split("_")
    return "".join(x.title() for x in components)


@mcp_server.tool()
async def get_conport_schema(
    workspace_id: Annotated[
        str, Field(description="Identifier for the workspace (e.g., absolute path)")
    ]
) -> Union[Dict[str, Any], MCPError]:
    """Retrieves the schema of all available ConPort tools.
    The output is a dictionary where each key is a tool name and the value is its JSON schema.
    """
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")

    tool_functions = [f for f in mcp_server.tools.values() if f.__name__ != "get_conport_schema"]  # type: ignore[attr-defined]

    final_schemas = {}
    for func in tool_functions:
        param_schema = TypeAdapter(func).json_schema()

        param_schema["description"] = (
            inspect.getdoc(func) or f"Arguments for {func.__name__}."
        )
        param_schema["title"] = f"{_to_camel_case(func.__name__)}Args"
        param_schema.pop("additionalProperties", None)

        if "properties" in param_schema:
            for prop_name, prop_schema in param_schema["properties"].items():
                prop_schema.pop("title", None)

        final_schemas[func.__name__] = param_schema

    this_func_schema = TypeAdapter(get_conport_schema).json_schema()
    this_func_schema["description"] = inspect.getdoc(get_conport_schema) or ""
    this_func_schema["title"] = "GetConportSchemaArgs"
    this_func_schema.pop("additionalProperties", None)
    if "properties" in this_func_schema:
        for prop_name, prop_schema in this_func_schema["properties"].items():
            prop_schema.pop("title", None)
    final_schemas["get_conport_schema"] = this_func_schema

    return final_schemas


@mcp_server.tool()
async def diff_context_versions(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace")],
    item_type: Annotated[
        str,
        Field(
            description="Type of the item (e.g., 'product_context', 'active_context')"
        ),
    ],
    version_a: Annotated[int, Field(description="Version number of the first item")],
    version_b: Annotated[int, Field(description="Version number of the second item")],
) -> Union[List[Any], MCPError]:
    """Compares two versions of a ConPort item and returns the differences.

    This function retrieves two specific versions of a context item (product_context or active_context)
    and compares their content using dictdiffer to show what has changed between versions.

    Args:
    ----
        workspace_id: Identifier for the workspace
        item_type: Type of the item ('product_context' or 'active_context')
        version_a: Version number of the first item to compare
        version_b: Version number of the second item to compare

    Returns:
    -------
        List of differences found by dictdiffer, or MCPError if versions not found

    """
    if not workspace_id:
        return MCPError(error="workspace_id is a required argument.")
    async with get_db_session_for_workspace(workspace_id) as db:
        history_model = None
        if item_type == "product_context":
            history_model = models.ProductContextHistory
        elif item_type == "active_context":
            history_model = models.ActiveContextHistory
        else:
            return MCPError(
                error="Invalid item_type for diff comparison",
                details={
                    "item_type": item_type,
                    "valid_types": ["product_context", "active_context"],
                },
            )

        version_a_record = db.query(history_model).filter_by(version=version_a).first()
        if not version_a_record:
            return MCPError(
                error=f"Version {version_a} not found",
                details={"item_type": item_type, "version": version_a},
            )

        version_b_record = db.query(history_model).filter_by(version=version_b).first()
        if not version_b_record:
            return MCPError(
                error=f"Version {version_b} not found",
                details={"item_type": item_type, "version": version_b},
            )

        content_a = version_a_record.content  # type: ignore
        content_b = version_b_record.content  # type: ignore

        diff_result = list(dictdiffer.diff(content_a, content_b))

        return diff_result