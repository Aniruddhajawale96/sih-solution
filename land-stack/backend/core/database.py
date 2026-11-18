"""
SQLAlchemy 2.0 async engine, session factory, and FastAPI dependency.

Environment variable:
  DATABASE_URL  — full async connection string
                  default: postgresql+asyncpg://landstack:landstack@localhost:5432/landstack
"""

import os
from dotenv import load_dotenv
load_dotenv()
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Declarative base — imported by all model modules
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Engine — created once at import time, reused across the process lifetime
# ---------------------------------------------------------------------------

DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://landstack:landstack@localhost:5432/landstack",
)

engine = create_async_engine(
    DATABASE_URL,
    echo=False,          # set to True for SQL query logging during development
    pool_pre_ping=True,  # verify connections before checkout
    pool_size=10,
    max_overflow=20,
)

# ---------------------------------------------------------------------------
# Session factory — expire_on_commit=False keeps loaded objects usable after
# the transaction closes, which is important for async usage patterns.
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession and guarantee it is closed after the request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
