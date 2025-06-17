# Novaport-MCP The Backend for NovaPort

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a **complete, from-the-ground-up rewrite** of the original [greatscottymac/context-portal](https://github.com/GreatScottyMac/context-portal). The purpose of this fork is to provide a robust, maintainable, and type-safe Model Context Protocol (MCP) server, specifically developed as the backend for the [NovaPort Project](https://github.com/Siroopfles/NovaPort).

All original features of ConPort have been preserved, but the underlying architecture has been rebuilt using modern tooling and best practices to ensure stability and scalability.

## Key Architectural Improvements

This version is superior to the original in the following ways:

-   **Modern Python & Tooling:** Built entirely with Python 3.11+ and managed by [Poetry](https://python-poetry.org/) for robust dependency management and reproducible builds.
-   **Robust Database Layer:** Utilizes the **SQLAlchemy 2.0 ORM** with a **per-workspace SQLite database**, ensuring project data is fully isolated.
-   **Automated Database Migrations:** Thanks to the **Alembic** integration, a new workspace database is automatically created and migrated to the latest schema on its first use.
-   **Clean Architecture:** The project follows a clear separation of layers (`api`, `services`, `schemas`, `db`), making it highly maintainable and easy to extend.
-   **Reliable Server Communication:** Uses the excellent `fastmcp` library to provide a stable `stdio`-based server, as required by MCP clients like Roo Code.
-   **Full Type Safety:** Pydantic schemas are used throughout the application for strict data validation, from tool inputs to database outputs.

## Requirements

-   Python 3.11+
-   [Poetry](https://python-poetry.org/docs/#installation)

## Installation and Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Siroopfles/novaport-mcp.git
    cd novaport-mcp
    ```

2.  **Install dependencies:**
    This command creates a virtual environment and installs all necessary packages.
    ```bash
    poetry install
    ```

3.  **Configure your environment:**
    -   Copy the `.env.example` file to a new file named `.env`.
    -   The default settings are fine for local use. The `DATABASE_URL` is a placeholder for command-line tools; the application itself will create a dedicated SQLite database for each project (workspace) it interacts with.

4.  **Database Setup:**
    There is no manual database setup needed! The server automatically creates and migrates a `conport.db` file inside a `.novaport_data` directory within your project workspace the first time you use a tool for that workspace.

## Running the Server

To start the server for use with an MCP client like Roo Code, run the following command in your terminal:

```bash
poetry run conport
```

The server will start and wait for `stdio` input. It is multi-project aware; the specific project context is determined by the `workspace_id` parameter sent with each tool call.

## Integration with Roo Code (for NovaPort)

To use this server in VS Code as the backend for NovaPort, configure your workspace `settings.json`.

1.  Open your **Workspace `settings.json`** (located in the `.vscode` folder of your *NovaPort* project).
2.  Add the following `mcpServers` object:

```json
{
  "mcpServers": {
    "novaport-mcp": {
      "command": "poetry",
      "args": [
        "run",
        "conport"
      ],
      // This path MUST point to the directory where you cloned the novaport-mcp repository.
      "cwd": "/path/to/your/cloned/novaport-mcp", 
      
      "disabled": false,
      "description": "The robust, multi-project MCP server for NovaPort."
    }
  }
}
```
**Important:**
1.  Ensure the `cwd` path is correct and points to the directory where you cloned `novaport-mcp`.
2.  Your NovaPort system prompts must be updated to include `"workspace_id": "${workspaceFolder}"` in the `arguments` of every `use_mcp_tool` call. Without this, the server will not know which project's database to use.

## Search Capabilities

ConPort includes powerful Full-Text Search (FTS) capabilities for enhanced content discovery:

### Available FTS Tools
- `search_decisions_fts`: Full-text search across decision summaries and rationales
- `search_custom_data_value_fts`: Full-text search within custom data values

### Database Backend Options

**SQLite (Default):**
- Per-workspace SQLite databases with basic FTS support
- Suitable for development and small to medium workspaces
- Automatic setup, no additional configuration required

**PostgreSQL (Advanced):**
For better FTS performance and advanced search capabilities, you can configure PostgreSQL:

1. Install PostgreSQL and create a database
2. Set environment variables:
   ```bash
   export DATABASE_URL="postgresql://username:password@localhost/conport_db"
   ```
3. PostgreSQL provides superior FTS performance with advanced ranking and indexing

Note: PostgreSQL configuration requires running database migrations and is recommended for production environments with large datasets.

## Development

-   **Running Tests:** Use `pytest` to run the test suite.
    ```bash
    poetry run pytest
    ```
-   **Creating a New Database Migration:** After modifying the models in `src/conport/db/models.py`, generate a new migration script:
    ```bash
    # Note: The migration will be applied automatically to new or existing workspace databases.
    # This command only generates the script for version control.
    poetry run alembic revision --autogenerate -m "A description of your change"
    ```
-   **Exploring the HTTP API:** The server can also run as a standard FastAPI web server, which is useful for exploring the API endpoints via a web browser.
    1.  **Start the server with Uvicorn:**
        ```bash
        # Note: This mode is for exploration and does not use the per-workspace database logic.
        poetry run uvicorn src.conport.app_factory:create_app --factory --host 0.0.0.0 --port 8000
        ```
    2.  **Open your browser:**
        -   Interactive API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
        -   Alternative API docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)
