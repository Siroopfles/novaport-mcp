# NovaPort-MCP Technical Deep Dive

## Overview

NovaPort-MCP is a robust, database-backed Model Context Protocol (MCP) server designed for managing structured project context across multiple isolated workspaces. This document provides a comprehensive technical analysis of the system's architecture, design decisions, and implementation patterns.

## Architecture Overview

NovaPort-MCP follows a clean, multi-layered architecture that promotes separation of concerns and maintainability:

```
┌─────────────────────────────────────────────────────────────┐
│                        API Layer                            │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Context   │ │  Decisions  │ │    Meta     │   ...    │
│  │   Routes    │ │   Routes    │ │   Routes    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │   Context   │ │  Decision   │ │   Vector    │   ...    │
│  │   Service   │ │   Service   │ │   Service   │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Schema Layer                           │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │  Pydantic   │ │  Pydantic   │ │  Pydantic   │   ...    │
│  │  Context    │ │  Decision   │ │   Error     │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      Database Layer                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ SQLAlchemy  │ │   Alembic   │ │  ChromaDB   │          │
│  │   Models    │ │ Migrations  │ │   Vector    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

### Key Components

- **API Layer** (`src/conport/api/`): FastAPI-based MCP tool implementations
- **Service Layer** (`src/conport/services/`): Business logic abstraction
- **Schema Layer** (`src/conport/schemas/`): Pydantic data validation models
- **Database Layer** (`src/conport/db/`): SQLAlchemy ORM models and Alembic migrations

## Database Layer Architecture

### SQLAlchemy 2.0 ORM as Core

The system uses SQLAlchemy 2.0 as its primary ORM, providing type-safe database operations and modern async support.

#### Core Models

Located in `src/conport/db/models.py`, the system defines several key entities:

**Context Models:**
```python
class ProductContext(Base):
    __tablename__ = "product_context"
    id = Column(Integer, primary_key=True, default=1)
    content = Column(JSON, nullable=False, default={})

class ActiveContext(Base):
    __tablename__ = "active_context"
    id = Column(Integer, primary_key=True, default=1)
    content = Column(JSON, nullable=False, default={})
```

**Decision Tracking:**
```python
class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    summary = Column(String, nullable=False, index=True)
    rationale = Column(Text, nullable=True)
    implementation_details = Column(Text, nullable=True)
    tags = Column(JSON, nullable=True)
```

**Progress Tracking with Hierarchical Structure:**
```python
class ProgressEntry(Base):
    __tablename__ = "progress_entries"
    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    status = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=False)
    parent_id = Column(Integer, ForeignKey("progress_entries.id", ondelete="SET NULL"), nullable=True)
    parent = relationship("ProgressEntry", remote_side=[id], back_populates="children")
    children = relationship("ProgressEntry", back_populates="parent", cascade="all, delete-orphan", lazy="joined")
```

**Knowledge Graph Support:**
```python
class ContextLink(Base):
    __tablename__ = "context_links"
    id = Column(Integer, primary_key=True, index=True)
    source_item_type = Column(String, nullable=False, index=True)
    source_item_id = Column(String, nullable=False, index=True)
    target_item_type = Column(String, nullable=False, index=True)
    target_item_id = Column(String, nullable=False, index=True)
    relationship_type = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
```

### Design Decisions

1. **JSON Columns**: Extensive use of JSON columns for flexible schema-less data storage while maintaining ACID properties
2. **Indexing Strategy**: Strategic indexing on frequently queried columns (timestamps, status, tags)
3. **Soft Relationships**: Self-referential relationships in ProgressEntry enable hierarchical task tracking
4. **Audit Trail**: Separate history tables for tracking changes to critical context data

## Migration System

### Alembic Integration

The system uses Alembic for automatic, per-workspace database migrations, ensuring schema consistency across all workspaces.

#### Automatic Migration Execution

```python
async def get_session_local(workspace_id: str) -> sessionmaker:
    """Retrieves or creates a SessionLocal for a specific workspace"""
    if workspace_id not in _workspace_locks:
        _workspace_locks[workspace_id] = asyncio.Lock()
    
    async with _workspace_locks[workspace_id]:
        # ... initialization logic ...
        
        # RUN MIGRATIONS IN SEPARATE THREAD
        await asyncio.to_thread(run_migrations_for_workspace, engine, db_path)
```

**Key Features:**
- **Per-workspace migrations**: Each workspace gets its own database with automatic schema setup
- **Thread isolation**: Migrations run in separate threads to prevent blocking the async event loop
- **Lock-based safety**: Workspace-level locks prevent concurrent initialization conflicts
- **Dynamic configuration**: Alembic configuration is generated at runtime for each workspace

#### Migration Configuration

The `src/conport/db/alembic/env.py` supports both CLI and programmatic execution:

```python
def run_migrations_online() -> None:
    connectable = context.config.attributes.get("connection", None)
    
    if connectable is None:
        # CLI execution path
        connectable = engine_from_config(...)
    else:
        # Programmatic execution from application
        context.configure(connection=connectable, target_metadata=target_metadata)
```

## Dependency Management

### Poetry for Modern Python Management

The project uses Poetry for dependency management, providing:

**Core Dependencies:**
```toml
[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.111.0"
uvicorn = {extras = ["standard"], version = "^0.30.1"}
sqlalchemy = "^2.0.30"
alembic = "^1.13.1"
pydantic-settings = "^2.3.4"
python-dotenv = "^1.0.1"
psycopg2-binary = "^2.9.9"
chromadb = "^0.5.3"
sentence-transformers = "^3.0.1"
typer = {extras = ["all"], version = "^0.12.3"}
fastmcp = ">=0.9.0"
dictdiffer = "^0.9.0"
```

**Development Dependencies:**
```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.2.2"
pytest-asyncio = "^0.23.7"
pytest-cov = "^5.0.0"
httpx = "^0.27.0"
black = "^24.4.2"
ruff = "^0.4.10"
mypy = "^1.8.0"
```

### Rationale for Key Dependencies

- **FastMCP**: Provides the MCP protocol implementation
- **ChromaDB**: Vector database for semantic search capabilities
- **SQLAlchemy 2.0**: Modern ORM with excellent async support
- **Pydantic**: Runtime type checking and data validation
- **Sentence Transformers**: Pre-trained models for text embeddings

## Async Architecture

### Fully Async Design

The entire system is built with async/await patterns for maximum concurrency and performance.

#### Database Session Management

```python
@asynccontextmanager
async def get_db_session_for_workspace(workspace_id: str) -> AsyncGenerator[Session, None]:
    db = None
    try:
        SessionLocal = await get_session_local(workspace_id)
        db = SessionLocal()
        yield db
    except Exception as e:
        log.error(f"Error while retrieving DB session for workspace '{workspace_id}': {e}")
        raise
    finally:
        if db:
            db.close()
```

#### Async Service Layer

Services are designed to work seamlessly with the async infrastructure:

```python
# Example from vector_service.py
async def cleanup_workspace_async(workspace_id: str) -> None:
    """Async wrapper for workspace cleanup"""
    await asyncio.to_thread(cleanup_chroma_client, workspace_id)
```

**Performance Benefits:**
- Non-blocking I/O operations
- Concurrent request handling
- Efficient resource utilization
- Scalable under load

## Service Layer Design

### Business Logic Abstraction

The service layer abstracts complex business logic from the API endpoints, providing clean separation of concerns.

#### Context Service Pattern

```python
def _get_or_create(db: Session, model: Type[ContextModel]) -> ContextModel:
    """Helper function to retrieve or create a context record with default content."""
    instance = db.query(model).filter_by(id=1).first()
    if not instance:
        instance = model(id=1, content={})
        db.add(instance)
        db.commit()
        db.refresh(instance)
    return instance

def update_context(
    db: Session,
    instance: Union[models.ProductContext, models.ActiveContext],
    update_data: context_schema.ContextUpdate
) -> Union[models.ProductContext, models.ActiveContext]:
    """Updates context with full content or patch-based updates."""
    current_content = cast(Dict[str, Any], instance.content) or {}
    new_content = current_content.copy()
    
    if update_data.content is not None:
        new_content = update_data.content
    elif update_data.patch_content is not None:
        for key, value in update_data.patch_content.items():
            if value == "__DELETE__":
                new_content.pop(key, None)
            else:
                new_content[key] = value
    
    if new_content != current_content:
        instance.content = new_content
        db.add(instance)
        db.commit()
        db.refresh(instance)
    
    return instance
```

**Design Patterns:**
- **Generic type handling**: Type-safe operations across different model types
- **Patch-based updates**: Efficient partial updates with special deletion markers
- **Lazy initialization**: Resources created only when needed
- **Change detection**: Only persists when actual changes occur

## API Layer

### MCP Tool Implementation Patterns

The API layer implements MCP tools using FastAPI with consistent patterns across all endpoints.

#### Standard API Pattern

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter(prefix="/workspaces/{workspace_id_b64}/context", tags=["Context"])

@router.get("/product", response_model=context_schema.ContextRead)
def read_product_context(workspace_id_b64: str, db: Session = Depends(get_db)):
    """Retrieve the global product context for the workspace."""
    ctx = context_service.get_product_context(db)
    return ctx

@router.put("/product", response_model=context_schema.ContextRead)
def update_product_context(
    workspace_id_b64: str, 
    update_data: context_schema.ContextUpdate, 
    db: Session = Depends(get_db)
):
    """Update the product context."""
    instance = context_service.get_product_context(db)
    return context_service.update_context(db, instance, update_data)
```

**Consistent Patterns:**
- **Workspace isolation**: All endpoints include workspace_id_b64 in path
- **Dependency injection**: Database sessions injected via FastAPI dependencies
- **Schema validation**: Pydantic models for request/response validation
- **Service delegation**: Business logic delegated to service layer
- **Type safety**: Full type annotations throughout

#### App Factory Pattern

```python
def create_app() -> FastAPI:
    """Factory to create the FastAPI application instance."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="A robust, multi-workspace MCP server for NovaPort.",
        version="2.1.0"
    )
    
    # Include all API routers
    app.include_router(context.router)
    app.include_router(decisions.router)
    app.include_router(progress.router)
    # ... additional routers
    
    return app
```

## Schema Validation

### Pydantic for Data Validation

The system uses Pydantic extensively for runtime type checking and data validation.

#### Schema Design Patterns

```python
class ContextBase(BaseModel):
    content: Dict[str, Any]

class ContextRead(ContextBase): 
    pass

class ContextUpdate(BaseModel):
    content: Optional[Dict[str, Any]] = Field(None, description="The full new context content.")
    patch_content: Optional[Dict[str, Any]] = Field(None, description="A dictionary of changes to apply.")
```

**Benefits:**
- **Runtime validation**: Automatic validation of incoming data
- **Documentation generation**: Automatic API documentation from schemas
- **Type safety**: IDE support and static analysis
- **Serialization**: Automatic JSON serialization/deserialization

#### Error Handling Schema

```python
class MCPError(BaseModel):
    """Pydantic model for MCP errors."""
    error: str
    details: Optional[Any] = None
```

## Vector Search Integration

### ChromaDB for Semantic Search

The system integrates ChromaDB for advanced semantic search capabilities across project context.

#### Vector Service Architecture

```python
_model: Optional[SentenceTransformer] = None
_chroma_clients: Dict[str, Client] = {}
_collections: Dict[str, chromadb.Collection] = {}

def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        log.info(f"Loading sentence transformer model: {settings.EMBEDDING_MODEL_NAME}...")
        _model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
    return _model

def get_chroma_client(workspace_id: str) -> Client:
    """Initialize a ChromaDB client for a workspace with correctly formatted paths."""
    global _chroma_clients
    db_path = str(Path(get_vector_db_path_for_workspace(workspace_id)).resolve())
    
    if db_path not in _chroma_clients:
        client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        _chroma_clients[db_path] = client
    return _chroma_clients[db_path]
```

**Key Features:**
- **Workspace isolation**: Separate vector databases per workspace
- **Caching strategy**: Intelligent caching of models and clients
- **Cleanup handling**: Robust cleanup for test environments
- **Error resilience**: Graceful handling of collection invalidation

#### Search Implementation

```python
def search(
    workspace_id: str,
    query_text: str,
    top_k: int,
    filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    collection = get_collection(workspace_id)
    query_embedding = generate_embedding(query_text)
    results = collection.query(
        query_embeddings=[query_embedding], 
        n_results=top_k, 
        where=filters
    )
    
    # Process results...
    return output
```

## Error Handling Patterns

### Comprehensive Error Management

The system implements layered error handling across all components.

#### Database Error Handling

```python
async def get_session_local(workspace_id: str) -> sessionmaker:
    try:
        # ... initialization logic ...
        await asyncio.to_thread(run_migrations_for_workspace, engine, db_path)
        # ... success path ...
    except Exception as e:
        log.error(f"Error initializing database for '{workspace_id}': {e}", exc_info=True)
        # Cleanup on failure
        if workspace_id in _session_locals: del _session_locals[workspace_id]
        if workspace_id in _engines: del _engines[workspace_id]
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            detail=f"Database initialization error: {e}"
        )
```

#### API Error Handling

```python
@router.get("/{decision_id}", response_model=decision_schema.DecisionRead)
def read_decision(workspace_id_b64: str, decision_id: int, db: Session = Depends(get_db)):
    """Retrieve a single decision by its ID."""
    db_decision = decision_service.get(db, decision_id=decision_id)
    if db_decision is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return db_decision
```

**Error Handling Strategies:**
- **Layered exceptions**: Different error types at different layers
- **Resource cleanup**: Automatic cleanup on failures
- **Detailed logging**: Comprehensive error logging with context
- **HTTP compliance**: Proper HTTP status codes and error messages

## Testing Strategy

### Current Test Structure

The testing infrastructure is built around pytest with async support and comprehensive coverage.

#### Test Organization

```
tests/
├── __init__.py
├── test_api/
│   ├── __init__.py
│   ├── test_batch.py
│   ├── test_context.py
│   ├── test_decisions.py
│   ├── test_history_extended.py
│   ├── test_meta_extended.py
│   ├── test_search.py
│   └── test_utils.py
```

#### Testing Configuration

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.2.2"
pytest-asyncio = "^0.23.7"
pytest-cov = "^5.0.0"
httpx = "^0.27.0"
```

**Testing Approach:**
- **Async testing**: Full async test support with pytest-asyncio
- **Integration tests**: End-to-end API testing
- **Coverage tracking**: Code coverage monitoring
- **Workspace isolation**: Tests run in isolated workspace environments

## Workspace Isolation Pattern

### Multi-Tenant Architecture

One of the system's most important design decisions is complete workspace isolation.

#### Configuration-Based Isolation

```python
def get_data_dir_for_workspace(workspace_id: str) -> Path:
    """Creates and returns a dedicated data directory within the specified workspace."""
    workspace_path = Path(workspace_id)
    if not workspace_path.is_dir():
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"Invalid workspace_id: {workspace_id} - Error: {e}")
    
    data_dir = workspace_path / ".novaport_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_database_url_for_workspace(workspace_id: str) -> str:
    """Generates the SQLite DATABASE_URL for a specific workspace."""
    data_dir = get_data_dir_for_workspace(workspace_id)
    db_path = data_dir / "conport.db"
    return f"sqlite:///{db_path.resolve()}"

def get_vector_db_path_for_workspace(workspace_id: str) -> str:
    """Generates the path for the ChromaDB vector store for a specific workspace."""
    data_dir = get_data_dir_for_workspace(workspace_id)
    vector_db_path = data_dir / "vectordb"
    vector_db_path.mkdir(exist_ok=True)
    return str(vector_db_path)
```

#### Workspace Encoding

```python
def encode_workspace_id(workspace_id: str) -> str:
    """Encodes a workspace path to a URL-safe base64 string."""
    return base64.urlsafe_b64encode(workspace_id.encode()).decode()

def decode_workspace_id(encoded_id: str) -> str:
    """Decodes a URL-safe base64 string back to a workspace path."""
    try:
        return base64.urlsafe_b64decode(encoded_id.encode()).decode()
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Invalid workspace_id encoding.")
```

**Isolation Benefits:**
- **Data separation**: Complete data isolation between projects
- **Concurrent access**: Multiple projects can be accessed simultaneously
- **Independent schemas**: Each workspace has its own database schema version
- **Resource isolation**: Vector databases and embeddings are workspace-specific

## Performance Considerations

### Optimization Strategies

1. **Connection Pooling**: SQLAlchemy connection pooling for database efficiency
2. **Async Operations**: Non-blocking I/O throughout the system
3. **Caching Layers**: Model and client caching in vector service
4. **Lazy Loading**: Resources initialized only when needed
5. **Batch Operations**: Support for batch API operations to reduce round trips

### Memory Management

```python
def cleanup_chroma_client(workspace_id: str) -> None:
    """Closes the ChromaDB client for a specific workspace."""
    try:
        # ... cleanup logic ...
        
        import time
        time.sleep(CHROMA_CLEANUP_DELAY)  # Give Windows time to release handles
        
        import gc
        gc.collect()
        time.sleep(CHROMA_GC_DELAY)  # Extra wait after garbage collection
        
        del _chroma_clients[db_path]
    except Exception as e:
        log.error(f"Error cleaning up ChromaDB client: {e}")
        raise
```

### Scalability Considerations

- **Horizontal scaling**: Stateless design enables horizontal scaling
- **Resource management**: Careful cleanup prevents resource leaks
- **Async architecture**: High concurrency support
- **Database per workspace**: Prevents cross-workspace performance interference

## Security Considerations

### Data Isolation

- **Workspace boundaries**: Strict enforcement of workspace isolation
- **Path validation**: Secure handling of workspace path encoding/decoding
- **SQL injection prevention**: SQLAlchemy ORM provides built-in protection
- **Input validation**: Pydantic schema validation for all inputs

### Configuration Security

```python
class Settings(BaseSettings):
    """Loads application configuration from .env file and environment variables."""
    PROJECT_NAME: str = "NovaPort MCP"
    EMBEDDING_MODEL_NAME: str = 'all-MiniLM-L6-v2'
    # DUMMY DATABASE_URL for Alembic CLI only
    DATABASE_URL: str = "sqlite:///./dummy_for_alembic_cli.db"
```

**Security Features:**
- **Environment-based configuration**: Sensitive data via environment variables
- **Dummy defaults**: Secure defaults that don't expose real data
- **Workspace validation**: Robust workspace ID validation and encoding

## Conclusion

NovaPort-MCP represents a sophisticated, production-ready implementation of an MCP server with enterprise-grade features:

- **Clean Architecture**: Multi-layered design with clear separation of concerns
- **Modern Technology Stack**: Leveraging the latest Python async capabilities
- **Robust Data Management**: SQLAlchemy 2.0 with automatic migrations
- **Advanced Search**: Vector-based semantic search capabilities
- **Complete Isolation**: Per-workspace data and resource isolation
- **Comprehensive Testing**: Full test coverage with async support
- **Performance Optimized**: Async-first design with intelligent caching

The system is designed for scalability, maintainability, and reliability, making it suitable for production deployments in enterprise environments.