from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

class Settings(BaseSettings):
    """Loads application configuration from a .env file and environment variables."""
    PROJECT_NAME: str = "Context Portal v2"
    
    # Default to a local SQLite DB in a dedicated data directory
    # Example for PostgreSQL: "postgresql://user:pass@host:port/dbname"
    DATABASE_URL: str = f"sqlite:///{Path('./conport_data/conport.db').resolve()}"

    EMBEDDING_MODEL_NAME: str = 'all-MiniLM-L6-v2'
    VECTOR_DB_PATH: str = "./conport_data/vectordb" # Path for persistent ChromaDB

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, env_file_encoding="utf-8")

# Create the main data directory on import
Path("./conport_data").mkdir(exist_ok=True)

settings = Settings()