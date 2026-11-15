"""
Alembic environment for Land Stack backend.

Supports both offline (SQL script generation) and online (live DB) modes.
Uses asyncpg driver via SQLAlchemy 2.0 async engine, mirroring core/database.py.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# ---------------------------------------------------------------------------
# Import Base so that all model metadata is registered.
# Models are imported in backend/models/__init__.py; importing Base here
# ensures that any model imported elsewhere has already registered its
# metadata on Base.metadata before we call run_migrations.
# ---------------------------------------------------------------------------
from core.database import Base  # noqa: F401 — registers all subclasses

# ---------------------------------------------------------------------------
# Alembic Config — gives access to alembic.ini values
# ---------------------------------------------------------------------------
config = context.config

# Interpret the config file's logging section.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ---------------------------------------------------------------------------
# Target metadata — Alembic uses this for autogenerate support.
# ---------------------------------------------------------------------------
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# Database URL — read from environment; fall back to alembic.ini value only
# when the env var is absent.
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://landstack:landstack@localhost:5432/landstack",
)
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# ---------------------------------------------------------------------------
# Offline mode — emit SQL to stdout / a file without touching the DB.
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Configures the context with just the URL and not an Engine.  Calls to
    context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# Online mode — run against a live database using an async engine.
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """Synchronous callback invoked from within run_sync().

    Alembic's migration runner is synchronous; we pass this function to
    ``async_connection.run_sync`` so it executes inside an async context.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations through a sync callback.

    The engine is disposed immediately after the migration completes so
    this function is safe to call from scripts, CLI wrappers, or test
    fixtures without leaking connections.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as async_connection:
        await async_connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online mode — called by Alembic's runner."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# Dispatch: offline vs. online
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
