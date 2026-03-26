"""Regression tests for chart file streaming."""

from __future__ import annotations

import os

os.environ.pop("POSTGRES_HOST", None)
os.environ.pop("POSTGRES_USER", None)
os.environ.pop("POSTGRES_PASSWORD", None)
os.environ.pop("POSTGRES_DB", None)
os.environ.pop("POSTGRES_PORT", None)

from pathlib import Path

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.main import app
from database.models import Base, Chart
from database.session import get_db


@pytest_asyncio.fixture
async def chart_file_client(tmp_path: Path):
    db_path = tmp_path / 'chart_file.db'
    pdf_path = tmp_path / 'sample.pdf'
    pdf_path.write_bytes(b'%PDF-1.4\n%synthetic medinsight pdf\n')

    engine = create_async_engine(f'sqlite+aiosqlite:///{db_path}', echo=False)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with session_factory() as session:
        chart = Chart(filename='sample.pdf', file_path=str(pdf_path), status='completed')
        session.add(chart)
        await session.commit()
        await session.refresh(chart)

    async def override_get_db():
        async with session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client, chart.id
    finally:
        app.dependency_overrides.clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_chart_file_endpoint_streams_pdf(chart_file_client):
    client, chart_id = chart_file_client

    response = client.get(f'/api/charts/{chart_id}/file')

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('application/pdf')
    assert response.content.startswith(b'%PDF-1.4')
