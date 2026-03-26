"""Tests for the API layer — FastAPI app, routes, schemas."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ── App Creation Tests ───────────────────────────────────────────────────────

class TestAppCreation:
    def test_app_imports(self) -> None:
        from api.main import app
        assert app is not None

    def test_app_has_routes(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert len(routes) > 20, f"Expected 20+ routes, got {len(routes)}"

    def test_health_endpoint_exists(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        assert "/health" in routes or "/api/health" in routes or "/" in routes

    def test_chart_routes_exist(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        chart_routes = [r for r in routes if "/charts" in r]
        assert len(chart_routes) >= 3, f"Expected chart routes, got: {chart_routes}"

    def test_risk_routes_exist(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        risk_routes = [r for r in routes if "/risk" in r]
        assert len(risk_routes) >= 3, f"Expected risk routes, got: {risk_routes}"

    def test_hedis_routes_exist(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        hedis_routes = [r for r in routes if "/hedis" in r]
        assert len(hedis_routes) >= 2

    def test_config_routes_exist(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        config_routes = [r for r in routes if "/config" in r]
        assert len(config_routes) >= 2

    def test_dashboard_routes_exist(self) -> None:
        from api.main import app
        routes = [r.path for r in app.routes if hasattr(r, "path")]
        dash_routes = [r for r in routes if "/dashboard" in r]
        assert len(dash_routes) >= 2


# ── Schema Tests ─────────────────────────────────────────────────────────────

class TestSchemas:
    def test_chart_schemas_import(self) -> None:
        from api.schemas.chart_schemas import (
            ChartUploadResponse,
            ChartProcessResponse,
            ChartListResponse,
        )
        assert ChartUploadResponse is not None
        assert ChartProcessResponse is not None

    def test_risk_schemas_import(self) -> None:
        from api.schemas.risk_schemas import (
            HCCPackSchema,
            RAFSummarySchema,
        )
        assert HCCPackSchema is not None
        assert RAFSummarySchema is not None

    def test_clinical_schemas_import(self) -> None:
        from api.schemas.clinical_schemas import (
            DiagnosisSchema,
            SentenceSchema,
        )
        assert DiagnosisSchema is not None
        assert SentenceSchema is not None

    def test_hedis_schemas_import(self) -> None:
        from api.schemas.hedis_schemas import (
            HEDISGapSchema,
        )
        assert HEDISGapSchema is not None

    def test_config_schemas_import(self) -> None:
        from api.schemas.config_schemas import (
            ConfigResponse,
            FeatureFlagUpdate,
        )
        assert ConfigResponse is not None
        assert FeatureFlagUpdate is not None


# ── Router Import Tests ──────────────────────────────────────────────────────

class TestRouterImports:
    def test_all_routers_import(self) -> None:
        from api.routers import charts
        from api.routers import patients
        from api.routers import clinical
        from api.routers import risk_adjustment
        from api.routers import hedis
        from api.routers import encounters
        from api.routers import audit
        from api.routers import config
        from api.routers import pipeline
        from api.routers import dashboard
        assert all([
            charts, patients, clinical, risk_adjustment,
            hedis, encounters, audit, config, pipeline, dashboard,
        ])


# ── Config Integration Tests ─────────────────────────────────────────────────

class TestConfigIntegration:
    def test_settings_loads(self) -> None:
        from config.settings import get_settings
        settings = get_settings()
        assert settings is not None
        assert settings.server.host is not None

    def test_feature_flags(self) -> None:
        from config.feature_flags import FeatureFlagRegistry, PipelineMode
        registry = FeatureFlagRegistry()
        snapshot = registry.snapshot()
        assert "risk_adjustment" in snapshot

    def test_feature_flag_mode_switching(self) -> None:
        from config.feature_flags import FeatureFlagRegistry, PipelineMode
        registry = FeatureFlagRegistry()

        registry.apply_mode(PipelineMode.RISK_ONLY)
        snap = registry.snapshot()
        assert snap["risk_adjustment"] is True
        assert snap["hedis"] is False

        registry.apply_mode(PipelineMode.HEDIS_ONLY)
        snap = registry.snapshot()
        assert snap["risk_adjustment"] is False
        assert snap["hedis"] is True

    def test_pipeline_config(self) -> None:
        from config.pipeline_config import PipelineRunConfig
        config = PipelineRunConfig()
        assert config.chunking.chunk_size > 0
        assert config.quality.quality_threshold > 0
