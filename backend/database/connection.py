"""Database connection pool management."""

from __future__ import annotations

from typing import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import get_settings

settings = get_settings()

# Async engine (primary — used by API and pipelines)
async_engine = create_async_engine(
    settings.database.async_url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Sync engine (used by Alembic migrations and scripts)
sync_engine = create_engine(
    settings.database.sync_url,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    echo=False,
)

SyncSessionLocal = sessionmaker(bind=sync_engine)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_sync_session() -> Session:
    """Return a sync DB session for scripts."""
    return SyncSessionLocal()
