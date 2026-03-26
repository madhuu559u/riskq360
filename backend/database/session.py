"""Database session factory.

Backend selection:
  - `DB_BACKEND=postgres`: force Postgres using settings.database credentials
  - `DB_BACKEND=sqlite`: force local SQLite file
  - `DB_BACKEND=auto` (default): legacy behavior (Postgres only when POSTGRES_HOST env is present)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncGenerator

import sqlalchemy
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config.settings import get_settings
from database.models import Base

settings = get_settings()
_sqlite_path = Path("outputs/medinsight360.db")
_backend = (settings.db_backend or "auto").strip().lower()

if _backend == "postgres":
    DATABASE_URL = settings.database.async_url
elif _backend == "sqlite":
    _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    DATABASE_URL = f"sqlite+aiosqlite:///{_sqlite_path}"
else:
    # Legacy fallback path.
    _pg_host = os.getenv("POSTGRES_HOST")
    if _pg_host:
        _user = os.getenv("POSTGRES_USER", "medinsight")
        _pass = os.getenv("POSTGRES_PASSWORD", "")
        _db = os.getenv("POSTGRES_DB", "medinsight360")
        _port = os.getenv("POSTGRES_PORT", "5432")
        DATABASE_URL = f"postgresql+asyncpg://{_user}:{_pass}@{_pg_host}:{_port}/{_db}"
    else:
        _sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        DATABASE_URL = f"sqlite+aiosqlite:///{_sqlite_path}"

engine = create_async_engine(DATABASE_URL, echo=False)

# Enable foreign-key enforcement for SQLite (disabled by default).
if "sqlite" in DATABASE_URL:
    @sqlalchemy.event.listens_for(engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, connection_record):  # type: ignore[misc]
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

async_session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def init_tables() -> None:
    """Create all tables (call once at startup)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields an async DB session with auto-commit."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

