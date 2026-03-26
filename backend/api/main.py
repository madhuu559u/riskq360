"""FastAPI application initialization for MedInsight 360."""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.middleware import add_middleware
from api.routers import (
    audit,
    charts,
    clinical,
    coding_helper,
    config,
    dashboard,
    encounters,
    hedis,
    patients,
    pipeline,
    review,
    risk_adjustment,
)
from config.settings import PROJECT_ROOT, get_settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    settings = get_settings()
    settings.init()
    # Initialize database tables
    from database.session import init_tables
    await init_tables()
    logger.info("app.startup", api_port=settings.server.port)
    yield
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="MedInsight 360",
        description="Unified Risk Adjustment + Quality Intelligence Platform",
        version="1.0.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Custom middleware
    add_middleware(app)

    # Routers
    app.include_router(charts.router, prefix="/api/charts", tags=["Charts"])
    app.include_router(patients.router, prefix="/api/patients", tags=["Patients"])
    app.include_router(clinical.router, prefix="/api/clinical", tags=["Clinical"])
    app.include_router(risk_adjustment.router, prefix="/api/risk", tags=["Risk Adjustment"])
    app.include_router(hedis.router, prefix="/api/hedis", tags=["HEDIS"])
    app.include_router(encounters.router, prefix="/api/encounters", tags=["Encounters"])
    app.include_router(audit.router, prefix="/api/audit", tags=["Audit"])
    app.include_router(config.router, prefix="/api/config", tags=["Configuration"])
    app.include_router(pipeline.router, prefix="/api/pipeline", tags=["Pipeline"])
    app.include_router(dashboard.router, prefix="/api/dashboard", tags=["Dashboard"])
    app.include_router(coding_helper.router, prefix="/api/coding-helper", tags=["Coding Helper"])
    app.include_router(review.router, prefix="/api/review", tags=["Review"])

    # Serve dashboard static files
    dashboard_dir = PROJECT_ROOT / "dashboard"
    if dashboard_dir.exists():
        app.mount("/dashboard", StaticFiles(directory=str(dashboard_dir), html=True), name="dashboard")

    @app.get("/", tags=["Health"])
    async def health_check():
        return {
            "status": "healthy",
            "service": "MedInsight 360",
            "version": "1.0.0",
        }

    return app


app = create_app()
