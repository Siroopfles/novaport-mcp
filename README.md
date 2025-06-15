# Novaport-MCP The Backend for NovaPort

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

This is a **complete, from-the-ground-up rewrite** of the original [greatscottymac/context-portal](https://github.com/GreatScottyMac/context-portal). The purpose of this fork is to provide a robust, maintainable, and type-safe Model Context Protocol (MCP) server, specifically developed as the backend for the [NovaPort Project](https://github.com/Siroopfles/NovaPort).

All original features of ConPort have been preserved, but the underlying architecture has been rebuilt using modern tooling and best practices to ensure stability and scalability.

## Key Architectural Improvements

This version is superior to the original in the following ways:

-   **Modern Python & Tooling:** Built entirely with Python 3.11+ and managed by [Poetry](https://python-poetry.org/) for robust dependency management and reproducible builds.
-   **Robust Database Layer:** Utilizes the **SQLAlchemy 2.0 ORM**, ensuring type-safe queries and a clean separation between application logic and the database.
-   **Automated Database Migrations:** Thanks to the **Alembic** integration with `autogenerate`, changes to the data models are automatically translated into migration scripts. No more manual database modifications.
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

3.  **Configure your database:**
    -   Copy the `.env.example` file to a new file named `.env`.
    -   Open `.env` and modify the `DATABASE_URL`. The default is a local SQLite database, which is perfect for getting started.
        ```
        # Example .env file
        DATABASE_URL="sqlite:///./conport_data/conport.db"
        ```

4.  **Run database migrations:**
    This command creates the database file and all necessary tables according to the models.
    ```bash
    poetry run alembic upgrade head
    ```

## Running the Server

To start the server for use with an MCP client like Roo Code, run the following command in your terminal:

```bash
poetry run conport
```

The server will start and wait for `stdio` input. You **do not** need to run this command manually; the client extension (Roo Code) will do this for you based on the configuration below.

## Integration with Roo Code (for NovaPort)

To use this server in VS Code as the backend for NovaPort, configure your workspace `settings.json`.

1.  Open your **Workspace `settings.json`** (located in the `.vscode` folder of your *NovaPort* project).
2.  Add the following `mcpServers` object:

```json
{
  "mcpServers": {
    "conport-v2": {
      "command": "poetry",
      "args": [
        "run",
        "conport"
      ],
      // CRITICAL: This tells VS Code to run the command from the correct directory.
      // Adjust this path to the location of your conport-v2 server on your machine.
      "cwd": "D:\\Desktop\\Projecten\\Novaport-mcp\\novaport-mcp", 
      
      "disabled": false,
      "description": "The new, robust ConPort v2 server for NovaPort."
    }
  }
}
```
**Important:** Ensure the `cwd` path is correct and points to the directory where you cloned `conport-v2`.

## Development

-   **Running Tests:** Use `pytest` to run the test suite.
    ```bash
    poetry run pytest
    ```
-   **Creating a New Database Migration:** After modifying the models in `src/conport/db/models.py`:
    ```bash
    poetry run alembic revision --autogenerate -m "A description of your change"
    poetry run alembic upgrade head
    ```

## License

This project is licensed under the Apache 2.0 License. See the `LICENSE` file for details.

