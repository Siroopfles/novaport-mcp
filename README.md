# Novaport-MCP The Backend for NovaPort

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a **complete, from-the-ground-up rewrite** of the original [greatscottymac/context-portal](https://github.com/GreatScottyMac/context-portal). The purpose of this fork is to provide a robust, maintainable, and type-safe Model Context Protocol (MCP) server, specifically developed as the backend for the [NovaPort Project](https://github.com/Siroopfles/NovaPort).

All original features of the original project have been preserved, but the underlying architecture has been rebuilt using modern tooling and best practices to ensure stability and scalability.

## Key Architectural Improvements

This version is superior to the original in the following ways:

-   **Modern Python & Tooling:** Built entirely with Python 3.11+ and managed by [Poetry](https://python-poetry.org/) for robust dependency management and reproducible builds.
-   **Robust Database Layer:** Utilizes the **SQLAlchemy 2.0 ORM** with a **per-workspace SQLite database**, ensuring project data is fully isolated and interactions are type-safe.
-   **Automated Database Migrations:** Thanks to the **Alembic** integration, a new workspace database is automatically created and migrated to the latest schema on its first use. No manual setup is required.
-   **Clean Architecture:** The project follows a clear separation of layers (`api`, `services`, `schemas`, `db`), making it highly maintainable and easy to extend.
-   **Reliable Server Communication:** Uses the excellent `fastmcp` library to provide a stable `stdio`-based server, as required by MCP clients like Roo Code.
-   **Full Type Safety:** Pydantic schemas are used throughout the application for strict data validation, from tool inputs to database outputs.
-   **Fully Tested & Validated**: Built with a comprehensive test suite using `pytest` and validated by a Continuous Integration (CI/CD) workflow on GitHub Actions. This ensures code quality, type-safety, and correct functionality with every change.

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
poetry run novaport-mcp
```

The server will start and wait for `stdio` input. It is multi-project aware; the specific project context is determined by the `workspace_id` parameter sent with each tool call.

## Integration with Roo Code

To use `novaport-mcp` as a powerful, database-backed memory source for the Roo Code extension in VS Code, you need to configure it as an MCP server. This allows Roo Code to manage the server's lifecycle (starting and stopping it as needed) via the fast and efficient `stdio` transport.

### Standard Configuration

This is the simplest method and should work for most setups where `poetry` is correctly installed and available in the system's PATH.

In your project workspace, create or open the `mcp_settings.json` file and add the following `mcpServers` object:

```json
{
  "mcpServers": {
    "novaport-mcp": {
      "command": "poetry",
      "args": [
        "run",
        "novaport-mcp"
      ],
      "cwd": "<absolute path to your cloned novaport-mcp directory>",
      "disabled": false,
      "description": "The robust, multi-project MCP server for NovaPort."
    }
  }
}
```

### Troubleshooting & Robust Configuration

If you encounter an `MCP error -32000: Connection closed` with the standard setup, it's almost always due to how Roo Code's environment executes the `poetry` command. The most reliable solution is to call the project's Python interpreter directly.

1.  **Find your project's Python executable path.** In your terminal, navigate to the `novaport-mcp` directory and run the following command:
    ```bash
    poetry env info -p
    ```
    This will output the absolute path to the Python interpreter within the virtual environment created by Poetry.
    *   **Windows Example:** `C:\Users\YourUser\AppData\Local\pypoetry\Cache\virtualenvs\novaport-mcp-...-py3.11\Scripts\python.exe`
    *   **Linux/macOS Example:** `/home/youruser/.cache/pypoetry/virtualenvs/novaport-mcp-...-py3.11/bin/python`

2.  **Update `mcp_settings.json`**. Use the path from the previous step as the `command` and adjust the `args` as shown below.

```json
{
  "mcpServers": {
    "novaport-mcp": {
      "command": "<path from 'poetry env info -p'>",
      "args": [
        "-m",
        "novaport_mcp"
      ],
      "cwd": "<absolute path to your cloned novaport-mcp directory>",
      "disabled": false,
      "description": "The robust, multi-project MCP server for NovaPort."
    }
  }
}
```

### Important Notes for Configuration

*   **`cwd` Path:** The `cwd` (Current Working Directory) **must** be the absolute path to the directory where you cloned the `novaport-mcp` repository.
*   **`command` Path (for Robust Config):** This must be the full, absolute path to the `python` executable. Remember to use double backslashes (`\\`) or forward slashes (`/`) for paths in JSON on Windows.
*   **`workspace_id` in Prompts:** Remember to include `"workspace_id": "${workspaceFolder}"` in the `arguments` of your `use_mcp_tool` calls. The `${workspaceFolder}` variable is automatically replaced by VS Code with the absolute path to your current project, which `novaport-mcp` uses to manage the correct, isolated database for that project.

## Docker Deployment

For containerized deployment, NovaPort-MCP provides a production-ready Docker image built with Poetry and optimized for security and performance.

### Building the Image

Build the Docker image with the following command:

```bash
docker build -t novaport-mcp:v0.1.0-beta .
```

### Running the Container

To persist workspace data across container restarts, mount a volume:

```bash
docker run -d --name novaport-mcp \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  novaport-mcp:v0.1.0-beta
```

## Development

-   **Running Tests:** Use `pytest` to run the test suite.
    ```bash
    poetry run pytest
    ```
-   **Creating a New Database Migration:** After modifying the models in `src/novaport_mcp/db/models.py`, generate a new migration script:
    ```bash
    # Note: The migration will be applied automatically to new or existing workspace databases.
    # This command only generates the script for version control.
    poetry run alembic revision --autogenerate -m "A description of your change"
    ```
-   **Exploring the HTTP API:** The server can also run as a standard FastAPI web server, which is useful for exploring the API endpoints via a web browser.
    1.  **Start the server with Uvicorn:**
        ```bash
        # Note: This mode is for exploration and does not use the per-workspace database logic.
        poetry run uvicorn src.novaport_mcp.app_factory:create_app --factory --host 0.0.0.0 --port 8000
        ```
    2.  **Open your browser:**
        -   Interactive API docs (Swagger): [http://localhost:8000/docs](http://localhost:8000/docs)
        -   Alternative API docs (ReDoc): [http://localhost:8000/redoc](http://localhost:8000/redoc)

## Usage with LLM Agents (Custom Instructions)

For LLM agents and AI assistants working with NovaPort-MCP, comprehensive guidance is available in the [`novaport-mcp-custom-instructions/generic_conport_strategy.yml`](novaport-mcp-custom-instructions/generic_conport_strategy.yml) file. This strategy document provides:

- **Tool Usage Patterns:** Best practices for using NovaPort-MCP tools effectively
- **Workflow Strategies:** Recommended approaches for different types of development tasks
- **Context Management:** Guidelines for maintaining context across tool calls
- **Error Handling:** Common error scenarios and recovery strategies

The custom instructions are designed to help LLM agents understand NovaPort-MCP's capabilities and use them efficiently in software development workflows.

## Documentation

For detailed technical information, architecture insights, and implementation details, refer to our comprehensive documentation:

- **[Technical Deep Dive](docs/deep_dive.md):** In-depth coverage of NovaPort-MCP's architecture, design decisions, database schema, and advanced usage patterns.

## Release Information

Stay informed about NovaPort-MCP updates and changes:

- **[Release Notes](RELEASE_NOTES.md):** Complete version history with detailed changelogs.
- **[Update Guide](UPDATE_GUIDE.md):** Step-by-step migration procedures for updating between versions.
