# Novaport-MCP The Backend for NovaPort

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a **complete, from-the-ground-up rewrite** of the original [greatscottymac/context-portal](https://github.com/GreatScottyMac/context-portal). The purpose of this fork is to provide a robust, maintainable, and type-safe Model Context Protocol (MCP) server, specifically developed as the backend for the [NovaPort Project](https://github.com/Siroopfles/NovaPort).

All original features of ConPort have been preserved, but the underlying architecture has been rebuilt using modern tooling and best practices to ensure stability and scalability.

## Key Architectural Improvements

This version is superior to the original in the following ways:

-   **Modern Python & Tooling:** Built entirely with Python 3.11+ and managed by [Poetry](https://python-poetry.org/) for robust dependency management and reproducible builds.
-   **Robust Database Layer:** Utilizes the **SQLAlchemy 2.0 ORM** with a **per-workspace SQLite database**, ensuring project data is fully isolated and providing superior performance and reliability.
-   **Automated Database Migrations:** Thanks to the **Alembic** integration, no manual database setup is required - a new workspace database is automatically created and migrated to the latest schema on its first use.
-   **Clean Architecture:** The project follows a clear separation of layers (`api`, `services`, `schemas`, `db`), making it highly maintainable and easy to extend while ensuring excellent code organization and scalability.
-   **Fully Tested & Validated:** Built with a comprehensive test suite using `pytest` and validated by a Continuous Integration (CI/CD) workflow on GitHub Actions. This ensures code quality, type-safety, and correct functionality with every change.
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
    
## Docker Deployment

For containerized deployment, NovaPort-MCP provides a production-ready Docker image built with Poetry and optimized for security and performance.

### Building the Image

Build the Docker image with the following command:

```bash
docker build -t novaport-mcp:v0.1.0-beta .
```

You can also build with a custom tag:

```bash
docker build -t novaport-mcp:latest .
```

**Note:** The build process uses Poetry for dependency management and creates a multi-stage build optimized for production use.

### Running the Container

#### Basic Container Run

Start the container with port mapping:

```bash
docker run -d --name novaport-mcp -p 8000:8000 novaport-mcp:v0.1.0-beta
```

#### Running with Volume Mount for Data Persistence

To persist workspace data across container restarts, mount a volume:

```bash
docker run -d --name novaport-mcp \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  novaport-mcp:v0.1.0-beta
```

#### Running with Environment Variables

Configure the application using environment variables:

```bash
docker run -d --name novaport-mcp \
  -p 8000:8000 \
  -e CONPORT_LOG_LEVEL=DEBUG \
  -e CONPORT_HOST=0.0.0.0 \
  -e CONPORT_PORT=8000 \
  -v $(pwd)/data:/app/data \
  novaport-mcp:v0.1.0-beta
```

### Container Management

#### Starting and Stopping

```bash
# Start the container
docker start novaport-mcp

# Stop the container
docker stop novaport-mcp

# Restart the container
docker restart novaport-mcp
```

#### Viewing Logs

```bash
# View container logs
docker logs novaport-mcp

# Follow logs in real-time
docker logs -f novaport-mcp

# View last 100 lines
docker logs --tail 100 novaport-mcp
```

#### Container Status and Health

```bash
# Check container status
docker ps

# Inspect container details
docker inspect novaport-mcp

# Check health status (built-in health check)
docker inspect novaport-mcp | grep Health -A 5
```

#### Removing the Container

```bash
# Stop and remove the container
docker stop novaport-mcp && docker rm novaport-mcp

# Force remove (if container is stuck)
docker rm -f novaport-mcp
```

### Environment Configuration

The Docker image supports the following environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `CONPORT_LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `CONPORT_HOST` | `0.0.0.0` | Host address to bind to |
| `CONPORT_PORT` | `8000` | Port number for the HTTP API |
| `DATABASE_URL` | (auto) | Custom database URL (optional) |
| `PYTHONPATH` | `/app/src` | Python path for module imports |

#### Example with Custom Configuration

```bash
docker run -d --name novaport-mcp \
  -p 9000:9000 \
  -e CONPORT_PORT=9000 \
  -e CONPORT_LOG_LEVEL=DEBUG \
  -e DATABASE_URL="postgresql://user:pass@host:5432/conport" \
  -v $(pwd)/workspace_data:/app/data \
  novaport-mcp:v0.1.0-beta
```

### Troubleshooting

#### Common Issues and Solutions

**Container fails to start:**
```bash
# Check container logs for error details
docker logs novaport-mcp

# Verify the image was built correctly
docker images | grep novaport-mcp

# Try running interactively for debugging
docker run -it --rm novaport-mcp:v0.1.0-beta /bin/bash
```

**Port already in use:**
```bash
# Check what's using the port
sudo netstat -tulpn | grep :8000

# Use a different port mapping
docker run -d --name novaport-mcp -p 8080:8000 novaport-mcp:v0.1.0-beta
```

**Permission issues with volumes:**
```bash
# Ensure the mounted directory has proper permissions
chmod 755 $(pwd)/data

# Check the container user (runs as non-root 'conport' user)
docker exec novaport-mcp id
```

**Health check failures:**
```bash
# Check if the health endpoint is accessible
docker exec novaport-mcp curl -f http://localhost:8000/health

# Verify port configuration
docker port novaport-mcp
```

**Database connectivity issues:**
```bash
# Check environment variables
docker exec novaport-mcp env | grep -E "(DATABASE|CONPORT)"

# Test database connection inside container
docker exec -it novaport-mcp python -c "from src.conport.db.database import get_database; print('DB OK')"
```

#### Production Deployment Considerations

- **Resource Limits:** Set appropriate CPU and memory limits for production:
  ```bash
  docker run -d --name novaport-mcp \
    --memory="512m" --cpus="1.0" \
    -p 8000:8000 \
    novaport-mcp:v0.1.0-beta
  ```

- **Restart Policy:** Use restart policies for automatic recovery:
  ```bash
  docker run -d --name novaport-mcp \
    --restart=unless-stopped \
    -p 8000:8000 \
    novaport-mcp:v0.1.0-beta
  ```

- **Security:** The container runs as a non-root user (`conport`) for enhanced security.

- **Monitoring:** The built-in health check endpoint (`/health`) can be used with orchestration tools like Docker Compose, Kubernetes, or monitoring systems.

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

## Usage with LLM Agents (Custom Instructions)

For LLM agents and AI assistants working with ConPort, comprehensive guidance is available in the [`conport-custom-instructions/generic_conport_strategy.yml`](conport-custom-instructions/generic_conport_strategy.yml) file. This strategy document provides:

- **Tool Usage Patterns:** Best practices for using ConPort tools effectively
- **Workflow Strategies:** Recommended approaches for different types of development tasks
- **Context Management:** Guidelines for maintaining context across tool calls
- **Error Handling:** Common error scenarios and recovery strategies

The custom instructions are designed to help LLM agents understand ConPort's capabilities and use them efficiently in software development workflows.

## Documentation

For detailed technical information, architecture insights, and implementation details, refer to our comprehensive documentation:

- **[Technical Deep Dive](docs/deep_dive.md):** In-depth coverage of ConPort's architecture, design decisions, database schema, and advanced usage patterns. Essential reading for contributors and users requiring detailed understanding of the system.

## Release Information

Stay informed about ConPort updates and changes:

- **[Release Notes](RELEASE_NOTES.md):** Complete version history with detailed changelogs, new features, bug fixes, and breaking changes
- **[Update Guide](UPDATE_GUIDE.md):** Step-by-step migration procedures for updating between versions, including configuration changes and compatibility notes
