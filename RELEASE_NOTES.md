# NovaPort-MCP Release Notes

## Version 0.1.0-beta (Released: December 2024)

This is the inaugural release of **NovaPort-MCP**, a complete, from-the-ground-up rewrite of the original [greatscottymac/context-portal](https://github.com/GreatScottyMac/context-portal). This version represents a major architectural evolution, providing a robust, maintainable, and type-safe Model Context Protocol (MCP) server specifically designed as the backend for the [NovaPort Project](https://github.com/Siroopfles/NovaPort).

### 🚀 New Features

#### Core Functionality
- **Model Context Protocol (MCP) Server**: Full implementation of MCP tools for structured project context management
- **Multi-Workspace Support**: Complete data isolation with per-workspace SQLite databases
- **Context Management**: Comprehensive product and active context management with versioning
- **Decision Tracking**: Structured decision logging with timestamps, rationales, and implementation details
- **Progress Tracking**: Hierarchical progress management with parent-child relationships
- **System Patterns**: Reusable architectural pattern documentation and tracking
- **Custom Data Management**: Flexible key-value storage with category-based organization
- **Knowledge Graph**: Context linking system for relationship mapping between project entities

#### Search Capabilities
- **Full-Text Search (FTS)**: Built-in search across decisions and custom data
- **Vector Search**: Semantic search capabilities using ChromaDB and sentence transformers
- **Advanced Filtering**: Tag-based and metadata filtering across all content types

#### API Features
- **RESTful API**: Complete REST API with automatic OpenAPI documentation
- **Batch Operations**: Efficient batch processing for bulk operations
- **History Tracking**: Comprehensive audit trails for all context changes
- **Error Handling**: Robust error handling with detailed error responses

### 🏗️ Architecture Improvements

#### Modern Technology Stack
- **Python 3.11+**: Built with modern Python features and type hints
- **SQLAlchemy 2.0 ORM**: Latest ORM with excellent async support and type safety
- **Alembic Integration**: Automatic database migrations for schema evolution
- **FastAPI Framework**: High-performance async web framework with automatic documentation
- **Pydantic Validation**: Runtime type checking and data validation throughout

#### Clean Architecture
- **Layered Design**: Clear separation between API, Service, Schema, and Database layers
- **Service Layer**: Business logic abstraction with reusable service components
- **Type Safety**: Full type annotations and Pydantic schemas for all data operations
- **Dependency Injection**: FastAPI dependency injection for clean resource management

#### Async-First Design
- **Full Async Support**: Complete async/await implementation for maximum concurrency
- **Non-blocking I/O**: Efficient resource utilization and scalable request handling
- **Async Database Operations**: SQLAlchemy async sessions with proper connection management
- **Concurrent Processing**: Safe concurrent access to multiple workspaces

#### Workspace Isolation
- **Per-Workspace Databases**: Each project gets its own isolated SQLite database
- **Automatic Schema Migration**: New workspaces automatically receive the latest schema
- **Resource Isolation**: Separate vector databases and embeddings per workspace
- **Thread-Safe Operations**: Workspace-level locks prevent initialization conflicts

### 🛠️ Developer Experience

#### Package Management
- **Poetry Integration**: Modern dependency management with reproducible builds
- **Virtual Environment**: Automatic virtual environment management
- **Development Dependencies**: Comprehensive dev tooling included (pytest, black, ruff, mypy)
- **CLI Interface**: Simple `poetry run novaport-mcp` command for server startup

#### Testing Infrastructure
- **Pytest Framework**: Comprehensive test suite with async support
- **Test Coverage**: Coverage tracking with pytest-cov
- **Integration Tests**: End-to-end API testing with httpx
- **Workspace Test Isolation**: Tests run in isolated environments

#### Documentation
- **API Documentation**: Automatic OpenAPI/Swagger documentation
- **Technical Deep Dive**: Comprehensive architectural documentation
- **README**: Detailed setup and usage instructions
- **Code Documentation**: Inline documentation throughout the codebase

#### Development Tools
- **Code Formatting**: Black formatter with consistent 88-character line length
- **Linting**: Ruff linter with comprehensive rule set
- **Type Checking**: MyPy integration for static type analysis
- **CI/CD**: GitHub Actions workflow for automated testing

### 💥 Breaking Changes

This is a complete rewrite, so there are no direct migration paths from the original context-portal. However, the core concepts and functionality have been preserved and enhanced:

- **API Structure**: New RESTful API design (previous version used different endpoints)
- **Database Schema**: Completely new schema with improved data modeling
- **Configuration**: New environment-based configuration system
- **Dependencies**: Modern dependency stack (requires Python 3.11+)

### 🐛 Known Issues

- **Windows ChromaDB Cleanup**: Some delay required for proper resource cleanup on Windows systems
- **Large Workspace Performance**: Vector search performance may degrade with very large datasets (>10K items)
- **PostgreSQL Support**: PostgreSQL backend is available but requires manual configuration
- **Migration Tools**: No automated migration tools from the original context-portal format

### 📦 Installation

#### Requirements
- Python 3.11 or higher
- [Poetry](https://python-poetry.org/docs/#installation) package manager

#### Quick Installation
```bash
# Clone the repository
git clone https://github.com/Siroopfles/novaport-mcp.git
cd novaport-mcp

# Install dependencies
poetry install

# Configure environment (optional, defaults work for local use)
cp .env.example .env

# Run the server
poetry run novaport-mcp
```

#### VS Code Integration (NovaPort)
Add to your workspace `.vscode/settings.json`:
```json
{
  "mcpServers": {
    "novaport-mcp": {
      "command": "poetry",
      "args": ["run", "novaport-mcp"],
      "cwd": "/path/to/your/cloned/novaport-mcp",
      "disabled": false,
      "description": "The robust, multi-project MCP server for NovaPort."
    }
  }
}
```

**Important**: Ensure your NovaPort system prompts include `"workspace_id": "${workspaceFolder}"` in all `use_mcp_tool` calls.

### 🔄 Migration

#### From Original Context-Portal
There is no automated migration path from the original context-portal. This version represents a complete architectural rewrite with:

- **New Data Format**: Enhanced data modeling with better relationships
- **Improved Schema**: More flexible and extensible database design
- **Modern API**: RESTful API design with better error handling

#### Workspace Setup
- **Automatic**: New workspaces are automatically initialized on first use
- **No Manual Setup**: Database creation and migration handled automatically
- **Data Location**: Workspace data stored in `.novaport_data/` directory within each project

#### Configuration Migration
- **Environment Variables**: Use `.env` file for configuration (copy from `.env.example`)
- **Database URLs**: Per-workspace SQLite databases (no manual database setup required)
- **Vector Search**: Automatic ChromaDB setup per workspace

### 🔧 Technical Details

#### Dependencies
**Core Runtime:**
- `fastapi ^0.111.0` - Web framework
- `sqlalchemy ^2.0.30` - Database ORM
- `alembic ^1.13.1` - Database migrations
- `chromadb ^0.5.3` - Vector database
- `sentence-transformers ^3.0.1` - Text embeddings
- `fastmcp >=0.9.0` - MCP protocol implementation

**Development:**
- `pytest ^8.2.2` - Testing framework
- `black ^24.4.2` - Code formatter
- `ruff ^0.4.10` - Linter
- `mypy ^1.8.0` - Type checker

#### Performance Characteristics
- **Async Operations**: Non-blocking I/O throughout
- **Connection Pooling**: SQLAlchemy connection pooling
- **Caching**: Intelligent model and client caching
- **Resource Management**: Automatic cleanup and garbage collection

#### Security Features
- **Input Validation**: Pydantic schema validation for all inputs
- **SQL Injection Prevention**: SQLAlchemy ORM protection
- **Workspace Isolation**: Strict enforcement of workspace boundaries
- **Path Validation**: Secure workspace path handling

### 🙏 Acknowledgments

This project builds upon the excellent foundation of the original [context-portal](https://github.com/GreatScottyMac/context-portal) by GreatScottyMac. While this is a complete rewrite, the core concepts and user experience principles have been preserved and enhanced.

---

**Next Version**: v0.2.0 planned with PostgreSQL optimizations, enhanced search capabilities, and performance improvements.