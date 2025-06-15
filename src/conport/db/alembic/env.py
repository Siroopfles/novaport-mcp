from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Importeer de Base en de settings uit onze applicatie
from conport.db.models import Base
from conport.core.config import settings

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Stel de URL in voor de CLI
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

target_metadata = Base.metadata

def run_migrations_offline() -> None:
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
    
    # Krijg de verbinding die is doorgegeven door de applicatie.
    # Dit zal een Connection object zijn als het vanuit de app wordt gedraaid,
    # en None als het vanuit de Alembic CLI wordt gedraaid.
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        # SCENARIO: Gedraaid vanaf de command line (e.g., "poetry run alembic upgrade head")
        # Maak een nieuwe engine aan vanuit alembic.ini
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        # Omdat we een engine hebben, moeten we de verbinding zelf beheren.
        with connectable.connect() as connection:
            context.configure(
                connection=connection,
                target_metadata=target_metadata
            )

            with context.begin_transaction():
                context.run_migrations()
    else:
        # SCENARIO: Gedraaid vanuit de applicatie.
        # 'connectable' IS AL EEN Connection object.
        # De transactie wordt al beheerd door `engine.begin()` in database.py.
        # We hoeven alleen maar Alembic te configureren om deze bestaande verbinding te gebruiken.
        context.configure(
            connection=connectable,
            target_metadata=target_metadata
        )
        
        # De transactie is al gestart, maar Alembic's context manager
        # zal de bestaande transactie "joinen" in plaats van een nieuwe te starten.
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()