"""Runtime configuration management endpoints."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config.feature_flags import get_feature_flags
from config.settings import get_settings
from database.session import DATABASE_URL
from database.session import get_db
from services.config_service import ConfigService

router = APIRouter()


class ConfigUpdate(BaseModel):
    key: str
    value: Any


class FeatureFlagUpdate(BaseModel):
    flag: str
    enabled: bool


class PromptUpdate(BaseModel):
    pipeline_name: str
    system_prompt: str
    notes: Optional[str] = None


class HedisProfileUpdate(BaseModel):
    active_measure_ids: list[str]
    profile_id: str = "custom"
    updated_by: str = "ui"


class HedisMeasureDefinitionUpdate(BaseModel):
    definition: dict[str, Any]
    updated_by: str = "ui"


class HedisValuesetDefinitionUpdate(BaseModel):
    definition: dict[str, Any]
    updated_by: str = "ui"


@router.get("")
async def get_config(db: AsyncSession = Depends(get_db)):
    """Get all current configuration (env + DB)."""
    settings = get_settings()
    flags = get_feature_flags()
    svc = ConfigService(db)
    db_config = await svc.get_all_config()
    active_llm = await svc.get_active_llm()

    return {
        "llm": active_llm or {
            "provider": settings.llm.active_llm_provider.value,
            "model": settings.llm.active_llm_model,
            "temperature": settings.llm.llm_temperature,
            "max_tokens": settings.llm.llm_max_tokens,
        },
        "pipeline": {
            "chunk_size": settings.pipeline.chunk_size,
            "chunk_overlap": settings.pipeline.chunk_overlap,
            "quality_threshold": settings.pipeline.quality_threshold,
            "measurement_year": settings.pipeline.measurement_year,
        },
        "ml": {
            "ml_confidence_threshold": settings.ml.ml_confidence_threshold,
            "tfidf_similarity_threshold": settings.ml.tfidf_similarity_threshold,
        },
        "feature_flags": flags.snapshot(),
        "db_config": db_config,
    }


@router.get("/runtime")
async def get_runtime_info():
    """Runtime diagnostics for DB backend wiring."""
    settings = get_settings()
    db_url = DATABASE_URL
    masked = db_url
    if "@" in db_url and "://" in db_url:
        prefix, rest = db_url.split("://", 1)
        if "@" in rest:
            creds, hostpart = rest.split("@", 1)
            if ":" in creds:
                user = creds.split(":", 1)[0]
                creds = f"{user}:***"
            masked = f"{prefix}://{creds}@{hostpart}"
    return {
        "db_backend": settings.db_backend,
        "database_url": masked,
        "measurement_year": settings.pipeline.measurement_year,
        "active_llm_model": settings.llm.active_llm_model,
    }


@router.put("")
async def update_config(update: dict[str, Any], db: AsyncSession = Depends(get_db)):
    """Update configuration values in the database.

    Supports:
    - legacy: {"key": "...", "value": ...}
    - bulk: {"llm": {...}, "pipeline": {...}, "ml": {...}}
    """
    svc = ConfigService(db)
    if "key" in update:
        key = str(update.get("key"))
        result = await svc.set_config(key, update.get("value"))
        return {"status": "updated", "updated_keys": [key], **result}

    updated_keys: list[str] = []
    for key in ("llm", "pipeline", "ml"):
        if key in update:
            await svc.set_config(key, update[key], updated_by="ui")
            updated_keys.append(key)
    if "feature_flags" in update:
        await svc.set_config("feature_flags", update["feature_flags"], updated_by="ui")
        updated_keys.append("feature_flags")
    return {"status": "updated", "updated_keys": updated_keys}


@router.get("/feature-flags")
async def get_feature_flags_endpoint():
    """Get all feature flags."""
    return get_feature_flags().snapshot()


@router.put("/feature-flags")
async def update_feature_flag(update: FeatureFlagUpdate | dict[str, bool], db: AsyncSession = Depends(get_db)):
    """Update a feature flag at runtime."""
    flags = get_feature_flags()
    if isinstance(update, dict):
        for flag, enabled in update.items():
            flags.set_flag(str(flag), bool(enabled))
        svc = ConfigService(db)
        await svc.set_config("feature_flags", {k: bool(v) for k, v in update.items()}, updated_by="ui")
        return {"status": "updated", "count": len(update)}
    flags.set_flag(update.flag, update.enabled)
    return {"status": "updated", "flag": update.flag, "enabled": update.enabled}


@router.get("/prompts")
async def get_prompts(db: AsyncSession = Depends(get_db)):
    """Get all prompt templates from DB + files."""
    svc = ConfigService(db)
    db_prompts = await svc.get_all_prompts()

    # Also load from file system
    from pathlib import Path
    file_prompts = {}
    prompts_dir = Path("config/prompts")
    if prompts_dir.exists():
        for f in prompts_dir.glob("*.txt"):
            file_prompts[f.stem] = f.read_text(encoding="utf-8")[:500] + "..."

    return {"db_prompts": db_prompts, "file_prompts": file_prompts}


@router.put("/prompts")
async def create_prompt(update: PromptUpdate, db: AsyncSession = Depends(get_db)):
    """Create a new prompt template version in the database."""
    svc = ConfigService(db)
    result = await svc.create_prompt(
        pipeline_name=update.pipeline_name,
        system_prompt=update.system_prompt,
        notes=update.notes,
    )
    return {"status": "created", **result}


@router.get("/model-versions")
async def get_model_versions(db: AsyncSession = Depends(get_db)):
    """Get ML model version information."""
    svc = ConfigService(db)
    return await svc.get_model_versions()


@router.get("/llm-configs")
async def get_llm_configs(db: AsyncSession = Depends(get_db)):
    """Get all LLM configurations."""
    svc = ConfigService(db)
    return await svc.get_all_llm_configs()


@router.get("/hedis/measures")
async def get_hedis_measure_catalog(db: AsyncSession = Depends(get_db)):
    """Get all HEDIS measures with active/inactive profile and rule summaries."""
    svc = ConfigService(db)
    return await svc.get_hedis_measure_catalog()


@router.put("/hedis/profile")
async def update_hedis_measure_profile(update: HedisProfileUpdate, db: AsyncSession = Depends(get_db)):
    """Persist active HEDIS measures used for processing/evaluation."""
    svc = ConfigService(db)
    profile = await svc.set_hedis_profile(
        active_measure_ids=update.active_measure_ids,
        profile_id=update.profile_id,
        updated_by=update.updated_by,
    )
    return {"status": "updated", "profile": profile}


@router.get("/hedis/measures/{measure_id}")
async def get_hedis_measure_definition(measure_id: str, db: AsyncSession = Depends(get_db)):
    """Get full YAML-backed measure definition for editing/review."""
    svc = ConfigService(db)
    return await svc.get_hedis_measure_definition(measure_id)


@router.put("/hedis/measures/{measure_id}")
async def upsert_hedis_measure_definition(
    measure_id: str,
    update: HedisMeasureDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a measure YAML definition."""
    svc = ConfigService(db)
    result = await svc.upsert_hedis_measure_definition(
        measure_id=measure_id,
        definition=update.definition,
        updated_by=update.updated_by,
    )
    return {"status": "saved", **result}


@router.delete("/hedis/measures/{measure_id}")
async def delete_hedis_measure_definition(
    measure_id: str,
    updated_by: str = "ui",
    db: AsyncSession = Depends(get_db),
):
    """Delete a measure YAML definition from catalog."""
    svc = ConfigService(db)
    result = await svc.delete_hedis_measure_definition(measure_id, updated_by=updated_by)
    return result


@router.get("/hedis/valuesets")
async def get_hedis_valueset_catalog(db: AsyncSession = Depends(get_db)):
    """List all HEDIS valuesets and code counts."""
    svc = ConfigService(db)
    return await svc.get_hedis_valueset_catalog()


@router.get("/hedis/valuesets/{valueset_id}")
async def get_hedis_valueset_definition(valueset_id: str, db: AsyncSession = Depends(get_db)):
    """Get full valueset definition."""
    svc = ConfigService(db)
    return await svc.get_hedis_valueset_definition(valueset_id)


@router.put("/hedis/valuesets/{valueset_id}")
async def upsert_hedis_valueset_definition(
    valueset_id: str,
    update: HedisValuesetDefinitionUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update a valueset definition."""
    svc = ConfigService(db)
    result = await svc.upsert_hedis_valueset_definition(
        valueset_id=valueset_id,
        definition=update.definition,
        updated_by=update.updated_by,
    )
    return {"status": "saved", **result}


@router.delete("/hedis/valuesets/{valueset_id}")
async def delete_hedis_valueset_definition(valueset_id: str, db: AsyncSession = Depends(get_db)):
    """Delete a valueset definition."""
    svc = ConfigService(db)
    return await svc.delete_hedis_valueset_definition(valueset_id)


@router.post("/hedis/bootstrap")
async def bootstrap_hedis_registry(updated_by: str = "system", db: AsyncSession = Depends(get_db)):
    """Sync file-based measure/value-set definitions into DB registry tables."""
    svc = ConfigService(db)
    result = await svc.bootstrap_hedis_registry_from_files(updated_by=updated_by)
    return result
