"""Repository for system/runtime configuration entities."""

from __future__ import annotations

from typing import Any, Optional, Sequence

from sqlalchemy import select, func, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    HEDISMeasureDefinition,
    HEDISValueSet,
    LLMConfig,
    ModelVersion,
    PromptTemplate,
    SystemConfig,
)


class ConfigRepository:
    """Async CRUD for all configuration tables."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ---- SystemConfig ----

    async def get_config(self, key: str) -> Optional[SystemConfig]:
        stmt = select(SystemConfig).where(SystemConfig.config_key == key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_config(self) -> Sequence[SystemConfig]:
        stmt = select(SystemConfig).order_by(SystemConfig.config_key)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def set_config(self, key: str, value: Any, updated_by: str = "system") -> SystemConfig:
        existing = await self.get_config(key)
        if existing:
            existing.config_value = value
            existing.updated_by = updated_by
            await self.session.flush()
            return existing
        rec = SystemConfig(config_key=key, config_value=value, updated_by=updated_by)
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def delete_config(self, key: str) -> bool:
        stmt = delete(SystemConfig).where(SystemConfig.config_key == key)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    # ---- LLMConfig ----

    async def get_active_llm(self) -> Optional[LLMConfig]:
        stmt = select(LLMConfig).where(LLMConfig.is_active.is_(True)).limit(1)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_llm_configs(self) -> Sequence[LLMConfig]:
        stmt = select(LLMConfig).order_by(LLMConfig.provider, LLMConfig.model_name)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_llm_config(self, **kwargs: Any) -> LLMConfig:
        rec = LLMConfig(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    # ---- PromptTemplate ----

    async def get_active_prompt(self, pipeline_name: str) -> Optional[PromptTemplate]:
        stmt = (
            select(PromptTemplate)
            .where(PromptTemplate.pipeline_name == pipeline_name, PromptTemplate.is_active.is_(True))
            .order_by(PromptTemplate.version.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_prompts(self) -> Sequence[PromptTemplate]:
        stmt = select(PromptTemplate).order_by(PromptTemplate.pipeline_name, PromptTemplate.version.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_prompt(self, **kwargs: Any) -> PromptTemplate:
        rec = PromptTemplate(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    # ---- ModelVersion ----

    async def get_active_model(self, model_name: str) -> Optional[ModelVersion]:
        stmt = (
            select(ModelVersion)
            .where(ModelVersion.model_name == model_name, ModelVersion.is_active.is_(True))
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_model_versions(self) -> Sequence[ModelVersion]:
        stmt = select(ModelVersion).order_by(ModelVersion.model_name, ModelVersion.created_at.desc())
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create_model_version(self, **kwargs: Any) -> ModelVersion:
        rec = ModelVersion(**kwargs)
        self.session.add(rec)
        await self.session.flush()
        return rec

    # ---- HEDIS Measure Catalog ----

    async def get_hedis_measure_definition(self, measure_id: str) -> Optional[HEDISMeasureDefinition]:
        stmt = select(HEDISMeasureDefinition).where(HEDISMeasureDefinition.measure_id == measure_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_hedis_measure_definitions(self, active_only: bool = False) -> Sequence[HEDISMeasureDefinition]:
        stmt = select(HEDISMeasureDefinition).order_by(HEDISMeasureDefinition.measure_id)
        if active_only:
            stmt = stmt.where(HEDISMeasureDefinition.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_hedis_measure_definition(
        self,
        measure_id: str,
        definition_json: dict[str, Any],
        version: str = "2025",
        source: str = "db",
        checksum: Optional[str] = None,
        is_active: bool = True,
        updated_by: str = "system",
    ) -> HEDISMeasureDefinition:
        existing = await self.get_hedis_measure_definition(measure_id)
        if existing:
            existing.definition_json = definition_json
            existing.version = version
            existing.source = source
            existing.checksum = checksum
            existing.is_active = is_active
            existing.updated_by = updated_by
            await self.session.flush()
            return existing

        rec = HEDISMeasureDefinition(
            measure_id=measure_id,
            definition_json=definition_json,
            version=version,
            source=source,
            checksum=checksum,
            is_active=is_active,
            updated_by=updated_by,
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def delete_hedis_measure_definition(self, measure_id: str) -> bool:
        stmt = delete(HEDISMeasureDefinition).where(HEDISMeasureDefinition.measure_id == measure_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0

    # ---- HEDIS Value Sets ----

    async def get_hedis_valueset(self, valueset_id: str) -> Optional[HEDISValueSet]:
        stmt = select(HEDISValueSet).where(HEDISValueSet.valueset_id == valueset_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_hedis_valuesets(self, active_only: bool = False) -> Sequence[HEDISValueSet]:
        stmt = select(HEDISValueSet).order_by(HEDISValueSet.valueset_id)
        if active_only:
            stmt = stmt.where(HEDISValueSet.is_active.is_(True))
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def upsert_hedis_valueset(
        self,
        valueset_id: str,
        payload_json: dict[str, Any],
        code_system: Optional[str] = None,
        source: str = "db",
        checksum: Optional[str] = None,
        is_active: bool = True,
        updated_by: str = "system",
    ) -> HEDISValueSet:
        existing = await self.get_hedis_valueset(valueset_id)
        if existing:
            existing.payload_json = payload_json
            existing.code_system = code_system
            existing.source = source
            existing.checksum = checksum
            existing.is_active = is_active
            existing.updated_by = updated_by
            await self.session.flush()
            return existing

        rec = HEDISValueSet(
            valueset_id=valueset_id,
            payload_json=payload_json,
            code_system=code_system,
            source=source,
            checksum=checksum,
            is_active=is_active,
            updated_by=updated_by,
        )
        self.session.add(rec)
        await self.session.flush()
        return rec

    async def delete_hedis_valueset(self, valueset_id: str) -> bool:
        stmt = delete(HEDISValueSet).where(HEDISValueSet.valueset_id == valueset_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
