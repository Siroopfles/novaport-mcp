from pydantic_settings import BaseSettings
from pathlib import Path
import base64
import binascii

class Settings(BaseSettings):
    """Loads application configuration from a .env file and environment variables."""
    PROJECT_NAME: str = "NovaPort MCP"
    EMBEDDING_MODEL_NAME: str = 'all-MiniLM-L6-v2'

    # DUMMY DATABASE_URL voor Alembic CLI.
    # Deze wordt NIET gebruikt door de draaiende applicatie, die de URL per workspace genereert.
    # Dit is alleen nodig zodat 'poetry run alembic revision' een geldige config heeft.
    DATABASE_URL: str = "sqlite:///./dummy_for_alembic_cli.db"

def get_data_dir_for_workspace(workspace_id: str) -> Path:
    """
    Creëert en retourneert een dedicated data directory binnen de opgegeven workspace.
    Dit zorgt voor isolatie per project. De map heet .novaport_data.
    """
    workspace_path = Path(workspace_id)
    if not workspace_path.is_dir():
        try:
            workspace_path.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            raise ValueError(f"De opgegeven workspace_id is geen geldige directory en kon niet worden aangemaakt: {workspace_id} - Error: {e}")
    
    data_dir = workspace_path / ".novaport_data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

def get_database_url_for_workspace(workspace_id: str) -> str:
    """Genereert de SQLite DATABASE_URL voor een specifieke workspace."""
    data_dir = get_data_dir_for_workspace(workspace_id)
    db_path = data_dir / "conport.db"
    return f"sqlite:///{db_path.resolve()}"

def get_vector_db_path_for_workspace(workspace_id: str) -> str:
    """Genereert het pad voor de ChromaDB vector store voor een specifieke workspace."""
    data_dir = get_data_dir_for_workspace(workspace_id)
    vector_db_path = data_dir / "vectordb"
    vector_db_path.mkdir(exist_ok=True)
    return str(vector_db_path)

def encode_workspace_id(workspace_id: str) -> str:
    """Encodeert een workspace pad naar een URL-veilige base64 string."""
    return base64.urlsafe_b64encode(workspace_id.encode()).decode()

def decode_workspace_id(encoded_id: str) -> str:
    """Decodeert een URL-veilige base64 string terug naar een workspace pad."""
    try:
        return base64.urlsafe_b64decode(encoded_id.encode()).decode()
    except (binascii.Error, UnicodeDecodeError):
        raise ValueError("Ongeldige workspace_id encoding.")

settings = Settings()

# ChromaDB configuratie
CHROMA_DEFAULT_COLLECTION_NAME = "conport_default"