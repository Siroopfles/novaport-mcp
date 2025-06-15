import logging
from typing import Any, Dict, List, Annotated, Optional, Callable
from pydantic import Field, ValidationError, TypeAdapter
from fastmcp import FastMCP
from pathlib import Path
import datetime
import inspect

# Correcte import voor de context manager
from .db.database import get_db_session_for_workspace
from .services import (
    context_service, decision_service, progress_service, system_pattern_service,
    custom_data_service, link_service, meta_service, vector_service,
    io_service, history_service
)
from .schemas import (
    context as context_schema, decision as decision_schema, progress as progress_schema,
    system_pattern as sp_schema, custom_data as cd_schema, link as link_schema,
    search as search_schema, batch as batch_schema, history as history_schema
)
from .db import models

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger(__name__)

# Dit zorgt ervoor dat de history listeners worden geregistreerd
_ = history_service

mcp_server = FastMCP(name="NovaPort-MCP")

# --- Tool Definities (Workspace-Aware) ---
# ... (alle 400+ regels met tool-definities blijven hier ongewijzigd) ...

@mcp_server.tool()
def get_product_context(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")]
) -> Dict[str, Any]:
    """Retrieves the overall project goals, features, and architecture."""
    with get_db_session_for_workspace(workspace_id) as db:
        return context_service.get_product_context(db).content

@mcp_server.tool()
def update_product_context(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    content: Annotated[Optional[Dict[str, Any]], Field(None, description="The full new context content as a dictionary. Overwrites existing.")] = None,
    patch_content: Annotated[Optional[Dict[str, Any]], Field(None, description="A dictionary of changes to apply to the existing context (add/update keys).")] = None
) -> Dict[str, Any]:
    """Updates the product context. Accepts full `content` (object) or `patch_content` (object) for partial updates (use `__DELETE__` as a value in patch to remove a key)."""
    with get_db_session_for_workspace(workspace_id) as db:
        try:
            update_data = context_schema.ContextUpdate(content=content, patch_content=patch_content)
            instance = context_service.get_product_context(db)
            updated = context_service.update_context(db, instance, update_data)
            return updated.content
        except ValidationError as e:
            return {"error": str(e)}

@mcp_server.tool()
def get_active_context(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")]
) -> Dict[str, Any]:
    """Retrieves the current working focus, recent changes, and open issues."""
    with get_db_session_for_workspace(workspace_id) as db:
        return context_service.get_active_context(db).content

@mcp_server.tool()
def update_active_context(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    content: Annotated[Optional[Dict[str, Any]], Field(None, description="The full new context content as a dictionary. Overwrites existing.")] = None,
    patch_content: Annotated[Optional[Dict[str, Any]], Field(None, description="A dictionary of changes to apply to the existing context (add/update keys).")] = None
) -> Dict[str, Any]:
    """Updates the active context. Accepts full `content` (object) or `patch_content` (object) for partial updates (use `__DELETE__` as a value in patch to remove a key)."""
    with get_db_session_for_workspace(workspace_id) as db:
        try:
            update_data = context_schema.ContextUpdate(content=content, patch_content=patch_content)
            instance = context_service.get_active_context(db)
            updated = context_service.update_context(db, instance, update_data)
            return updated.content
        except ValidationError as e:
            return {"error": str(e)}

@mcp_server.tool()
def log_decision(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    summary: Annotated[str, Field(description="A concise summary of the decision.")],
    rationale: Annotated[Optional[str], Field(None, description="The reasoning behind the decision.")] = None,
    implementation_details: Annotated[Optional[str], Field(None, description="Details about how the decision will be/was implemented.")] = None,
    tags: Annotated[Optional[List[str]], Field(None, description="Optional tags for categorization.")] = None
) -> Dict[str, Any]:
    """Logs an architectural or implementation decision."""
    with get_db_session_for_workspace(workspace_id) as db:
        data = decision_schema.DecisionCreate(summary=summary, rationale=rationale, implementation_details=implementation_details, tags=tags or [])
        created = decision_service.create(db, workspace_id, data)
        return decision_schema.DecisionRead.model_validate(created).model_dump(mode='json')

@mcp_server.tool()
def get_decisions(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    limit: Annotated[Optional[int], Field(None, description="Maximum number of decisions to return (most recent first).")] = None,
    tags_filter_include_all: Annotated[Optional[List[str]], Field(None, description="Filter: items must include ALL of these tags.")] = None,
    tags_filter_include_any: Annotated[Optional[List[str]], Field(None, description="Filter: items must include AT LEAST ONE of these tags.")] = None
) -> List[Dict[str, Any]]:
    """Retrieves logged decisions."""
    with get_db_session_for_workspace(workspace_id) as db:
        decisions = decision_service.get_multi(db, limit=limit or 100, tags_all=tags_filter_include_all, tags_any=tags_filter_include_any)
        return [decision_schema.DecisionRead.model_validate(d).model_dump(mode='json') for d in decisions]

@mcp_server.tool()
def delete_decision_by_id(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    decision_id: int
) -> Dict[str, Any]:
    """Deletes a decision by its ID."""
    with get_db_session_for_workspace(workspace_id) as db:
        deleted = decision_service.delete(db, workspace_id, decision_id)
        return {"status": "success", "id": decision_id} if deleted else {"status": "not_found", "id": decision_id}

@mcp_server.tool()
def log_progress(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    status: Annotated[str, Field(description="Current status (e.g., 'TODO', 'IN_PROGRESS', 'DONE').")],
    description: Annotated[str, Field(description="Description of the progress or task.")],
    parent_id: Annotated[Optional[int], Field(None, description="ID of the parent task, if this is a subtask.")] = None,
    linked_item_type: Annotated[Optional[str], Field(None, description="Optional: Type of the ConPort item to link.")] = None,
    linked_item_id: Annotated[Optional[str], Field(None, description="Optional: ID/key of the ConPort item to link.")] = None,
    link_relationship_type: Annotated[str, Field("relates_to_progress", description="Relationship type for the automatic link.")] = "relates_to_progress"
) -> Dict[str, Any]:
    """Logs a progress entry or task status."""
    with get_db_session_for_workspace(workspace_id) as db:
        entry_data = progress_schema.ProgressEntryCreate(status=status, description=description, parent_id=parent_id)
        created = progress_service.create(db, workspace_id, entry_data, linked_item_type, linked_item_id, link_relationship_type)
        return progress_schema.ProgressEntryRead.model_validate(created).model_dump(mode='json')

@mcp_server.tool()
def get_progress(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    limit: Annotated[Optional[int], Field(None, description="Maximum number of entries to return (most recent first).")] = None,
    status_filter: Annotated[Optional[str], Field(None, description="Filter entries by status.")] = None,
    parent_id_filter: Annotated[Optional[int], Field(None, description="Filter entries by parent task ID.")] = None
) -> List[Dict[str, Any]]:
    """Retrieves progress entries."""
    with get_db_session_for_workspace(workspace_id) as db:
        entries = progress_service.get_multi(db, limit=limit or 50, status=status_filter, parent_id=parent_id_filter)
        return [progress_schema.ProgressEntryRead.model_validate(p).model_dump(mode='json') for p in entries]

@mcp_server.tool()
def update_progress(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    progress_id: Annotated[int, Field(description="The ID of the progress entry to update.")],
    status: Annotated[Optional[str], Field(None, description="New status (e.g., 'TODO', 'IN_PROGRESS', 'DONE').")] = None,
    description: Annotated[Optional[str], Field(None, description="New description of the progress or task.")] = None,
    parent_id: Annotated[Optional[int], Field(None, description="New ID of the parent task, if changing.")] = None
) -> Dict[str, Any]:
    """Updates an existing progress entry."""
    with get_db_session_for_workspace(workspace_id) as db:
        update_data = progress_schema.ProgressEntryUpdate(status=status, description=description, parent_id=parent_id)
        if not update_data.model_dump(exclude_unset=True):
            return {"error": "No update fields provided."}
        updated = progress_service.update(db, progress_id, update_data)
        if not updated:
            return {"error": f"Progress entry with ID {progress_id} not found."}
        return progress_schema.ProgressEntryRead.model_validate(updated).model_dump(mode='json')

@mcp_server.tool()
def delete_progress_by_id(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    progress_id: int
) -> Dict[str, Any]:
    """Deletes a progress entry by its ID."""
    with get_db_session_for_workspace(workspace_id) as db:
        deleted = progress_service.delete(db, workspace_id, progress_id)
        return {"status": "success", "id": progress_id} if deleted else {"status": "not_found", "id": progress_id}

@mcp_server.tool()
def log_system_pattern(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    name: Annotated[str, Field(description="Unique name for the system pattern.")],
    description: Annotated[Optional[str], Field(None, description="Description of the pattern.")] = None,
    tags: Annotated[Optional[List[str]], Field(None, description="Optional tags for categorization.")] = None
) -> Dict[str, Any]:
    """Logs or updates a system/coding pattern."""
    with get_db_session_for_workspace(workspace_id) as db:
        pattern_data = sp_schema.SystemPatternCreate(name=name, description=description, tags=tags or [])
        created = system_pattern_service.create(db, workspace_id, pattern_data)
        return sp_schema.SystemPatternRead.model_validate(created).model_dump(mode='json')

@mcp_server.tool()
def get_system_patterns(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    tags_filter_include_all: Annotated[Optional[List[str]], Field(None, description="Filter: items must include ALL of these tags.")] = None,
    tags_filter_include_any: Annotated[Optional[List[str]], Field(None, description="Filter: items must include AT LEAST ONE of these tags.")] = None
) -> List[Dict[str, Any]]:
    """Retrieves system patterns."""
    with get_db_session_for_workspace(workspace_id) as db:
        patterns = system_pattern_service.get_multi(db, tags_all=tags_filter_include_all, tags_any=tags_filter_include_any)
        return [sp_schema.SystemPatternRead.model_validate(p).model_dump(mode='json') for p in patterns]

@mcp_server.tool()
def delete_system_pattern_by_id(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    pattern_id: int
) -> Dict[str, Any]:
    """Deletes a system pattern by its ID."""
    with get_db_session_for_workspace(workspace_id) as db:
        deleted = system_pattern_service.delete(db, workspace_id, pattern_id)
        return {"status": "success", "id": pattern_id} if deleted else {"status": "not_found", "id": pattern_id}

@mcp_server.tool()
def log_custom_data(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    category: Annotated[str, Field(description="Category for the custom data.")],
    key: Annotated[str, Field(description="Key for the custom data (unique within category).")],
    value: Annotated[Any, Field(description="The custom data value (JSON serializable).")]
) -> Dict[str, Any]:
    """Stores/updates a custom key-value entry under a category. Value is JSON-serializable."""
    with get_db_session_for_workspace(workspace_id) as db:
        data = cd_schema.CustomDataCreate(category=category, key=key, value=value)
        created = custom_data_service.upsert(db, workspace_id, data)
        return cd_schema.CustomDataRead.model_validate(created).model_dump(mode='json')

@mcp_server.tool()
def get_custom_data(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    category: Annotated[str, Field(description="Filter by category.")],
    key: Annotated[Optional[str], Field(None, description="Filter by key (requires category).")] = None
) -> List[Dict[str, Any]]:
    """Retrieves custom data."""
    with get_db_session_for_workspace(workspace_id) as db:
        if key:
            items = [custom_data_service.get(db, category, key)]
        else:
            items = custom_data_service.get_by_category(db, category)
        return [cd_schema.CustomDataRead.model_validate(i).model_dump(mode='json') for i in items if i]

@mcp_server.tool()
def delete_custom_data(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    category: Annotated[str, Field(description="Category of the data to delete.")],
    key: Annotated[str, Field(description="Key of the data to delete.")]
) -> Dict[str, Any]:
    """Deletes a specific custom data entry."""
    with get_db_session_for_workspace(workspace_id) as db:
        deleted = custom_data_service.delete(db, workspace_id, category, key)
        return {"status": "success"} if deleted else {"status": "not_found"}

@mcp_server.tool()
def export_conport_to_markdown(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    output_path: Annotated[Optional[str], Field(None, description="Optional output directory path relative to workspace_id.")] = None
) -> Dict[str, Any]:
    """Exports ConPort data to markdown files."""
    output_dir = Path(workspace_id) / (output_path or "conport_export")
    with get_db_session_for_workspace(workspace_id) as db:
        return io_service.export_to_markdown(db, output_dir)

@mcp_server.tool()
def import_markdown_to_conport(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    input_path: Annotated[Optional[str], Field(None, description="Optional input directory path containing markdown files.")] = None
) -> Dict[str, Any]:
    """Imports data from markdown files into ConPort."""
    input_dir = Path(workspace_id) / (input_path or "conport_export")
    with get_db_session_for_workspace(workspace_id) as db:
        return io_service.import_from_markdown(db, workspace_id, input_dir)

@mcp_server.tool()
def link_conport_items(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    source_item_type: Annotated[str, Field(description="Type of the source item.")],
    source_item_id: Annotated[str, Field(description="ID or key of the source item.")],
    target_item_type: Annotated[str, Field(description="Type of the target item.")],
    target_item_id: Annotated[str, Field(description="ID or key of the target item.")],
    relationship_type: Annotated[str, Field(description="Nature of the link.")],
    description: Annotated[Optional[str], Field(None, description="Optional description for the link.")] = None
) -> Dict[str, Any]:
    """Creates a relationship link between two ConPort items."""
    with get_db_session_for_workspace(workspace_id) as db:
        link_data = link_schema.LinkCreate(
            source_item_type=source_item_type, source_item_id=source_item_id,
            target_item_type=target_item_type, target_item_id=target_item_id,
            relationship_type=relationship_type, description=description
        )
        created = link_service.create(db, link_data)
        return link_schema.LinkRead.model_validate(created).model_dump(mode='json')

@mcp_server.tool()
def get_linked_items(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    item_type: Annotated[str, Field(description="Type of the item to find links for.")],
    item_id: Annotated[str, Field(description="ID or key of the item to find links for.")],
    limit: Annotated[Optional[int], Field(None, description="Maximum number of links to return.")] = None
) -> List[Dict[str, Any]]:
    """Retrieves items linked to a specific item."""
    with get_db_session_for_workspace(workspace_id) as db:
        links = link_service.get_for_item(db, item_type, item_id, limit=limit or 50)
        return [link_schema.LinkRead.model_validate(l).model_dump(mode='json') for l in links]

@mcp_server.tool()
def search_decisions_fts(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    query_term: Annotated[str, Field(description="The term to search for in decisions.")],
    limit: Annotated[Optional[int], Field(None, description="Maximum number of search results.")] = None
) -> List[Dict[str, Any]]:
    """Full-text search across decision fields."""
    with get_db_session_for_workspace(workspace_id) as db:
        decisions = decision_service.search_fts(db, query=query_term, limit=limit or 10)
        return [decision_schema.DecisionRead.model_validate(d).model_dump(mode='json') for d in decisions]

@mcp_server.tool()
def search_custom_data_value_fts(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    query_term: Annotated[str, Field(description="The term to search for.")],
    category_filter: Annotated[Optional[str], Field(None, description="Optional: Filter results to this category.")] = None,
    limit: Annotated[Optional[int], Field(None, description="Maximum number of results.")] = None
) -> List[Dict[str, Any]]:
    """Full-text search across all custom data values, categories, and keys."""
    with get_db_session_for_workspace(workspace_id) as db:
        items = custom_data_service.search_fts(db, query=query_term, category=category_filter, limit=limit or 10)
        return [cd_schema.CustomDataRead.model_validate(i).model_dump(mode='json') for i in items]

@mcp_server.tool()
def search_project_glossary_fts(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    query_term: Annotated[str, Field(description="The term to search for in the glossary.")],
    limit: Annotated[Optional[int], Field(None, description="Maximum number of search results.")] = None
) -> List[Dict[str, Any]]:
    """Full-text search within the 'ProjectGlossary' custom data category."""
    with get_db_session_for_workspace(workspace_id) as db:
        items = custom_data_service.search_fts(db, query=query_term, category="ProjectGlossary", limit=limit or 10)
        return [cd_schema.CustomDataRead.model_validate(i).model_dump(mode='json') for i in items]

@mcp_server.tool()
def batch_log_items(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    item_type: Annotated[batch_schema.ItemType, Field(description="Type of items to log.")],
    items: Annotated[List[Dict[str, Any]], Field(description="A list of item data.")]
) -> Dict[str, Any]:
    """Logs multiple items of the same type in a single call."""
    with get_db_session_for_workspace(workspace_id) as db:
        try:
            return meta_service.batch_log_items(db, workspace_id, item_type, items)
        except ValidationError as e:
            return {"error": "Invalid batch request structure", "details": e.errors()}

@mcp_server.tool()
def get_item_history(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    item_type: Annotated[str, Field(description="Type of item: 'product_context' or 'active_context'.")],
    limit: Annotated[Optional[int], Field(None, description="Max number of history entries.")] = None,
    version: Annotated[Optional[int], Field(None, description="Return a specific version.")] = None,
    before_timestamp: Annotated[Optional[datetime.datetime], Field(None, description="Return entries before this timestamp.")] = None,
    after_timestamp: Annotated[Optional[datetime.datetime], Field(None, description="Return entries after this timestamp.")] = None
) -> List[Dict[str, Any]]:
    """Retrieves version history for Product or Active Context."""
    with get_db_session_for_workspace(workspace_id) as db:
        history_model = None
        if item_type == "product_context":
            history_model = models.ProductContextHistory
        elif item_type == "active_context":
            history_model = models.ActiveContextHistory
        else:
            return [{"error": "Invalid item_type"}]
        
        query = db.query(history_model)
        if version:
            query = query.filter_by(version=version)
        if before_timestamp:
            query = query.filter(history_model.timestamp < before_timestamp)
        if after_timestamp:
            query = query.filter(history_model.timestamp > after_timestamp)
            
        records = query.order_by(history_model.version.desc()).limit(limit or 10).all()
        return [history_schema.HistoryRead.model_validate(r).model_dump(mode='json') for r in records]

@mcp_server.tool()
def get_recent_activity_summary(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    hours_ago: Annotated[Optional[int], Field(None, description="Look back this many hours.")] = None,
    since_timestamp: Annotated[Optional[datetime.datetime], Field(None, description="Look back since this timestamp.")] = None,
    limit_per_type: Annotated[int, Field(5, description="Maximum number of recent items to show per type.")] = 5
) -> Dict[str, Any]:
    """Provides a summary of recent ConPort activity (new/updated items)."""
    with get_db_session_for_workspace(workspace_id) as db:
        activity = meta_service.get_recent_activity(db, limit=limit_per_type)
        return {
            "decisions": [decision_schema.DecisionRead.model_validate(d).model_dump(mode='json') for d in activity["decisions"]],
            "progress": [progress_schema.ProgressEntryRead.model_validate(p).model_dump(mode='json') for p in activity["progress"]],
            "system_patterns": [sp_schema.SystemPatternRead.model_validate(s).model_dump(mode='json') for s in activity["system_patterns"]]
        }
    
@mcp_server.tool()
def semantic_search_conport(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")],
    query_text: Annotated[str, Field(description="The natural language query text.")],
    top_k: Annotated[int, Field(5, description="Number of top results to return.")] = 5,
    filter_item_types: Annotated[Optional[List[str]], Field(None, description="Optional list of item types to filter by.")] = None,
    filter_tags_include_any: Annotated[Optional[List[str]], Field(None, description="Optional list of tags; results must match ANY of these.")] = None,
    filter_tags_include_all: Annotated[Optional[List[str]], Field(None, description="Optional list of tags; results must match ALL of these.")] = None,
    filter_custom_data_categories: Annotated[Optional[List[str]], Field(None, description="Optional list of categories to filter by.")] = None
) -> List[Dict[str, Any]]:
    """Performs a semantic search across ConPort data."""
    filters: Dict[str, Any] = {}
    and_conditions: List[Dict[str, Any]] = []
    if filter_item_types:
        and_conditions.append({"item_type": {"$in": filter_item_types}})
    if filter_custom_data_categories:
        and_conditions.append({"category": {"$in": filter_custom_data_categories}})
    if filter_tags_include_all:
        for tag in filter_tags_include_all:
            and_conditions.append({"tags": {"$contains": tag}})
    if filter_tags_include_any:
        or_conditions = [{"tags": {"$contains": tag}} for tag in filter_tags_include_any]
        if or_conditions:
            and_conditions.append({"$or": or_conditions})
    
    if len(and_conditions) > 1:
        filters = {"$and": and_conditions}
    elif len(and_conditions) == 1:
        filters = and_conditions[0]
        
    return vector_service.search(workspace_id=workspace_id, query_text=query_text, top_k=top_k, filters=filters or None)


def _to_camel_case(snake_str: str) -> str:
    """Helper om snake_case om te zetten naar CamelCase."""
    components = snake_str.split('_')
    return ''.join(x.title() for x in components)

@mcp_server.tool()
def get_conport_schema(
    workspace_id: Annotated[str, Field(description="Identifier for the workspace (e.g., absolute path)")]
) -> Dict[str, Any]:
    """
    Retrieves the schema of all available ConPort tools.
    The output is a dictionary where each key is a tool name and the value is its JSON schema.
    """
    tool_functions = [
        get_product_context, update_product_context, get_active_context, update_active_context,
        log_decision, get_decisions, delete_decision_by_id,
        log_progress, get_progress, update_progress, delete_progress_by_id,
        log_system_pattern, get_system_patterns, delete_system_pattern_by_id,
        log_custom_data, get_custom_data, delete_custom_data,
        export_conport_to_markdown, import_markdown_to_conport,
        link_conport_items, get_linked_items,
        search_decisions_fts, search_custom_data_value_fts, search_project_glossary_fts,
        batch_log_items, get_item_history, get_recent_activity_summary,
        semantic_search_conport,
    ]

    final_schemas = {}
    for func in tool_functions:
        param_schema = TypeAdapter(func).json_schema()
        
        # De beschrijving is de docstring van de functie
        param_schema['description'] = inspect.getdoc(func) or f"Arguments for {func.__name__}."
        
        # De titel wordt programmatisch gegenereerd in CamelCase.
        param_schema['title'] = f"{_to_camel_case(func.__name__)}Args"
        
        # Verwijder de interne Pydantic sleutel voor een schoner schema
        param_schema.pop("additionalProperties", None)
        
        # Verwijder de "title" van de individuele properties voor een 1:1 match met het doelformaat
        if 'properties' in param_schema:
            for prop_name, prop_schema in param_schema['properties'].items():
                prop_schema.pop('title', None)

        final_schemas[func.__name__] = param_schema
        
    # Voeg de schema-definitie van deze functie zelf toe
    this_func_schema = TypeAdapter(get_conport_schema).json_schema()
    this_func_schema['description'] = inspect.getdoc(get_conport_schema) or ""
    this_func_schema['title'] = "GetConportSchemaArgs"
    this_func_schema.pop("additionalProperties", None)
    if 'properties' in this_func_schema:
        for prop_name, prop_schema in this_func_schema['properties'].items():
            prop_schema.pop('title', None)
    final_schemas['get_conport_schema'] = this_func_schema

    return final_schemas