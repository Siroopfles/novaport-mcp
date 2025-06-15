from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Importeer de Base en de settings uit onze applicatie
from conport.db.database import Base
from conport.core.config import settings # <-- Belangrijk

# Dit is het Alembic Config object, wat toegang geeft tot de
# waarden in het .ini bestand.
config = context.config

# Interpreteer het config bestand voor Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# BELANGRIJK: Hier stellen we de `sqlalchemy.url` programmatisch in
# op basis van onze Pydantic settings. Dit is voor de CLI.
# De draaiende app stelt dit per workspace in.
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

# Voeg je model's MetaData object hier toe
# voor 'autogenerate' support.
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()