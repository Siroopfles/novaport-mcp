from logging.config import fileConfig

from alembic import context
from conport.core.config import settings

# Import the Base and settings from our application
from conport.db.models import Base
from sqlalchemy import engine_from_config, pool

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set the URL for the CLI
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
    # Get the connection that was passed by the application.
    # This will be a Connection object if run from the app,
    # and None if run from the Alembic CLI.
    connectable = context.config.attributes.get("connection", None)

    if connectable is None:
        # SCENARIO: Run from command line (e.g., "poetry run alembic upgrade head")
        # Create a new engine from alembic.ini
        connectable = engine_from_config(
            config.get_section(config.config_ini_section, {}),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )

        # Since we have an engine, we need to manage the connection ourselves.
        with connectable.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)

            with context.begin_transaction():
                context.run_migrations()
    else:
        # SCENARIO: Run from the application.
        # 'connectable' IS ALREADY A Connection object.
        # The transaction is already managed by `engine.begin()` in database.py.
        # We only need to configure Alembic to use this existing connection.
        context.configure(connection=connectable, target_metadata=target_metadata)

        # The transaction is already started, but Alembic's context manager
        # will "join" the existing transaction instead of starting a new one.
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
