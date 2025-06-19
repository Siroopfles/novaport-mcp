import base64
import binascii
from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Loads application configuration from a .env file and environment variables."""

    PROJECT_NAME: str = "NovaPort MCP"
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"

    # DUMMY DATABASE_URL for Alembic CLI.
    # This is NOT used by the running application, which generates the URL per workspace.
    # This is only needed so that 'poetry run alembic revision' has a valid config.
    DATABASE_URL: str = "sqlite:///./dummy_for_alembic_cli.db"


def get_data_dir_for_workspace(workspace_id: str) -> Path:
    """Creates and returns a dedicated data directory within the specified workspace.
    This ensures isolation per project. The folder is named .novaport_data.
    """
    workspace_path = Path(workspace_id)
    if not workspace_path.is_dir():
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(
                f"The specified workspace_id is not a valid directory and could not be created: {workspace_id} - Error: {e}"
            )

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


def encode_workspace_id(workspace_id: str) -> str:
    """Encodes a workspace path to a URL-safe base64 string."""
    return base64.urlsafe_b64encode(workspace_id.encode()).decode()


def decode_workspace_id(encoded_id: str) -> str:
    """Decodes a URL-safe base64 string back to a workspace path."""
    try:
        return base64.urlsafe_b64decode(encoded_id.encode()).decode()
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Invalid workspace_id encoding.")


settings = Settings()

# ChromaDB configuration
CHROMA_DEFAULT_COLLECTION_NAME = "conport_default"
