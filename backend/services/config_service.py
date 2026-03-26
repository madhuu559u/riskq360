"""Config service - system config, LLM config, prompts, model versions."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from database.repositories.config_repo import ConfigRepository
from hedis.hedis_engine.measure_def import load_all_measures, parse_measure_dict

HEDIS_PROFILE_CONFIG_KEY = "hedis.measure_profile"


class ConfigService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ConfigRepository(session)

    # ---- System Config ----

    async def get_config(self, key: str) -> Optional[Any]:
        rec = await self.repo.get_config(key)
        return rec.config_value if rec else None

    async def get_all_config(self) -> dict:
        records = await self.repo.get_all_config()
        return {r.config_key: r.config_value for r in records}

    async def set_config(self, key: str, value: Any, updated_by: str = "system") -> dict:
        rec = await self.repo.set_config(key, value, updated_by)
        return {"key": rec.config_key, "value": rec.config_value}

    # ---- LLM Config ----

    async def get_active_llm(self) -> Optional[dict]:
        llm = await self.repo.get_active_llm()
        if not llm:
            return None
        return {
            "id": llm.id,
            "provider": llm.provider,
            "model_name": llm.model_name,
            "temperature": llm.temperature,
            "max_tokens": llm.max_tokens,
        }

    async def get_all_llm_configs(self) -> list[dict]:
        configs = await self.repo.get_all_llm_configs()
        return [
            {
                "id": c.id,
                "provider": c.provider,
                "model_name": c.model_name,
                "temperature": c.temperature,
                "max_tokens": c.max_tokens,
                "is_active": c.is_active,
            }
            for c in configs
        ]

    # ---- Prompts ----

    async def get_active_prompt(self, pipeline_name: str) -> Optional[dict]:
        p = await self.repo.get_active_prompt(pipeline_name)
        if not p:
            return None
        return {
            "pipeline_name": p.pipeline_name,
            "version": p.version,
            "system_prompt": p.system_prompt,
        }

    async def get_all_prompts(self) -> list[dict]:
        prompts = await self.repo.get_all_prompts()
        return [
            {
                "id": p.id,
                "pipeline_name": p.pipeline_name,
                "version": p.version,
                "is_active": p.is_active,
                "notes": p.notes,
            }
            for p in prompts
        ]

    async def create_prompt(self, pipeline_name: str, system_prompt: str, **kwargs: Any) -> dict:
        p = await self.repo.create_prompt(
            pipeline_name=pipeline_name,
            system_prompt=system_prompt,
            **kwargs,
        )
        return {"id": p.id, "pipeline_name": p.pipeline_name, "version": p.version}

    # ---- Model Versions ----

    async def get_model_versions(self) -> list[dict]:
        versions = await self.repo.get_all_model_versions()
        return [
            {
                "id": v.id,
                "model_name": v.model_name,
                "version": v.version,
                "model_type": v.model_type,
                "is_active": v.is_active,
                "f1_score": v.f1_score,
                "precision": v.precision,
                "recall": v.recall,
            }
            for v in versions
        ]

    # ---- HEDIS Measure Management ----

    def _hedis_catalog_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "hedis" / "hedis_engine" / "catalog"

    def _hedis_valuesets_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent / "hedis" / "hedis_engine" / "valuesets"

    @staticmethod
    def _checksum_payload(payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _normalize_measure_id(measure_id: str) -> str:
        return (measure_id or "").strip().upper().replace("_", "-")

    @staticmethod
    def _measure_rules_summary(measure: Any) -> list[str]:
        summary: list[str] = []
        if measure.age:
            summary.append(f"Age {measure.age.min_age}-{measure.age.max_age}")
        if measure.gender:
            summary.append(f"Gender: {', '.join(measure.gender)}")
        if measure.continuous_enrollment:
            summary.append("Continuous enrollment required")
        if measure.denominator_diagnosis:
            summary.append(
                f"Denominator diagnosis: {measure.denominator_diagnosis.valueset or 'coded list'}"
            )
        if measure.denominator_procedure:
            summary.append(
                f"Denominator procedure: {measure.denominator_procedure.valueset or 'coded list'}"
            )
        if measure.denominator_encounter:
            summary.append("Denominator encounter required")
        if measure.denominator_medication:
            summary.append(
                "Denominator medication: "
                f"{measure.denominator_medication.medication_class or measure.denominator_medication.valueset}"
            )
        if measure.exclusions:
            summary.append(f"Exclusions: {len(measure.exclusions)}")
        if measure.numerator:
            if measure.numerator.any_of:
                summary.append(f"Numerator ANY of {len(measure.numerator.any_of)} criteria")
            if measure.numerator.all_of:
                summary.append(f"Numerator ALL of {len(measure.numerator.all_of)} criteria")
        if measure.inverse:
            summary.append("Inverse measure")
        return summary

    async def get_hedis_profile(self) -> dict[str, Any]:
        value = await self.get_config(HEDIS_PROFILE_CONFIG_KEY)
        if not isinstance(value, dict):
            return {"profile_id": "default_all", "active_measure_ids": []}
        active_ids = [self._normalize_measure_id(v) for v in value.get("active_measure_ids", []) if v]
        return {
            "profile_id": str(value.get("profile_id") or "custom"),
            "active_measure_ids": active_ids,
            "updated_at": value.get("updated_at"),
            "updated_by": value.get("updated_by"),
        }

    async def set_hedis_profile(
        self,
        active_measure_ids: list[str],
        profile_id: str = "custom",
        updated_by: str = "system",
    ) -> dict[str, Any]:
        payload = {
            "profile_id": profile_id,
            "active_measure_ids": sorted({self._normalize_measure_id(i) for i in active_measure_ids if i}),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "updated_by": updated_by,
        }
        rec = await self.repo.set_config(HEDIS_PROFILE_CONFIG_KEY, payload, updated_by)
        return rec.config_value

    async def get_hedis_measure_catalog(self) -> dict[str, Any]:
        db_defs = await self.repo.list_hedis_measure_definitions(active_only=False)
        measures = []
        source = "db"
        if db_defs:
            for rec in db_defs:
                payload = rec.definition_json if isinstance(rec.definition_json, dict) else {}
                if not payload:
                    continue
                try:
                    measures.append(parse_measure_dict(payload))
                except Exception:
                    continue
        else:
            source = "file"
            measures = load_all_measures(self._hedis_catalog_dir())

        all_ids = sorted({self._normalize_measure_id(m.id) for m in measures if m.id})

        profile = await self.get_hedis_profile()
        active_ids = profile.get("active_measure_ids", [])
        if not active_ids:
            active_ids = all_ids
        active_set = set(active_ids)

        rows: list[dict[str, Any]] = []
        for measure in measures:
            mid = self._normalize_measure_id(measure.id)
            rows.append(
                {
                    "measure_id": mid,
                    "name": measure.name or mid,
                    "description": measure.description or "",
                    "domain": measure.domain or "",
                    "version": measure.version or "",
                    "active": mid in active_set,
                    "rules_summary": self._measure_rules_summary(measure),
                    "valuesets_needed": measure.valuesets_needed or [],
                    "data_sources": measure.data_sources or [],
                }
            )

        rows.sort(key=lambda r: (0 if r["active"] else 1, r["measure_id"]))
        return {
            "source": source,
            "profile": profile,
            "total_measures": len(rows),
            "active_count": sum(1 for r in rows if r["active"]),
            "inactive_count": sum(1 for r in rows if not r["active"]),
            "measures": rows,
        }

    async def get_hedis_measure_definition(self, measure_id: str) -> dict[str, Any]:
        mid = self._normalize_measure_id(measure_id)
        rec = await self.repo.get_hedis_measure_definition(mid)
        if rec and isinstance(rec.definition_json, dict):
            return {"measure_id": mid, "source": "db", "definition": rec.definition_json}

        catalog = self._hedis_catalog_dir()
        path = catalog / f"{mid.replace('-', '_')}.yaml"
        if not path.exists():
            path = catalog / f"{mid}.yaml"
        if not path.exists():
            raise FileNotFoundError(f"Measure YAML not found for {mid}")
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        return {"measure_id": mid, "source": "file", "path": str(path), "definition": data}

    async def upsert_hedis_measure_definition(
        self,
        measure_id: str,
        definition: dict[str, Any],
        updated_by: str = "system",
    ) -> dict[str, Any]:
        mid = self._normalize_measure_id(measure_id)
        payload = dict(definition)
        payload["id"] = mid
        parse_measure_dict(payload)  # validation

        checksum = self._checksum_payload(payload)
        await self.repo.upsert_hedis_measure_definition(
            measure_id=mid,
            definition_json=payload,
            version=str(payload.get("version", "2025")),
            source="db",
            checksum=checksum,
            is_active=True,
            updated_by=updated_by,
        )

        # Disk mirror for transparency/editability.
        path = self._hedis_catalog_dir() / f"{mid.replace('-', '_')}.yaml"
        path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

        profile = await self.get_hedis_profile()
        active_ids = profile.get("active_measure_ids", [])
        if active_ids and mid not in active_ids:
            active_ids.append(mid)
            await self.set_hedis_profile(active_ids, profile.get("profile_id", "custom"), updated_by)

        return {"measure_id": mid, "source": "db", "path": str(path), "checksum": checksum, "status": "saved"}

    async def delete_hedis_measure_definition(self, measure_id: str, updated_by: str = "system") -> dict[str, Any]:
        mid = self._normalize_measure_id(measure_id)
        await self.repo.delete_hedis_measure_definition(mid)

        catalog = self._hedis_catalog_dir()
        path = catalog / f"{mid.replace('-', '_')}.yaml"
        if not path.exists():
            path = catalog / f"{mid}.yaml"
        if path.exists():
            path.unlink()

        profile = await self.get_hedis_profile()
        active_ids = [m for m in profile.get("active_measure_ids", []) if self._normalize_measure_id(m) != mid]
        await self.set_hedis_profile(active_ids, profile.get("profile_id", "custom"), updated_by)

        return {"measure_id": mid, "status": "deleted"}

    async def get_hedis_valueset_catalog(self) -> dict[str, Any]:
        rows = await self.repo.list_hedis_valuesets(active_only=False)
        if rows:
            valuesets = [
                {
                    "valueset_id": r.valueset_id,
                    "code_system": r.code_system,
                    "code_count": len((r.payload_json or {}).get("codes", [])),
                    "is_active": bool(r.is_active),
                    "source": r.source or "db",
                    "updated_by": r.updated_by,
                    "updated_at": str(r.updated_at) if r.updated_at else None,
                }
                for r in rows
            ]
            return {
                "source": "db",
                "total_valuesets": len(valuesets),
                "active_count": sum(1 for v in valuesets if v["is_active"]),
                "valuesets": valuesets,
            }

        valuesets_dir = self._hedis_valuesets_dir()
        valuesets = []
        for path in sorted(valuesets_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            valuesets.append(
                {
                    "valueset_id": payload.get("id") or path.stem,
                    "code_system": payload.get("code_system"),
                    "code_count": len(payload.get("codes", [])),
                    "is_active": True,
                    "source": "file",
                    "path": str(path),
                }
            )
        return {
            "source": "file",
            "total_valuesets": len(valuesets),
            "active_count": len(valuesets),
            "valuesets": valuesets,
        }

    async def get_hedis_valueset_definition(self, valueset_id: str) -> dict[str, Any]:
        vid = valueset_id.strip()
        rec = await self.repo.get_hedis_valueset(vid)
        if rec and isinstance(rec.payload_json, dict):
            return {"valueset_id": vid, "source": "db", "definition": rec.payload_json}

        path = self._hedis_valuesets_dir() / f"{vid}.json"
        if not path.exists():
            raise FileNotFoundError(f"Valueset JSON not found for {vid}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {"valueset_id": vid, "source": "file", "path": str(path), "definition": payload}

    async def upsert_hedis_valueset_definition(
        self,
        valueset_id: str,
        definition: dict[str, Any],
        updated_by: str = "system",
    ) -> dict[str, Any]:
        vid = valueset_id.strip()
        payload = dict(definition)
        payload["id"] = vid
        if not isinstance(payload.get("codes", []), list):
            raise ValueError("valueset definition must include a list field `codes`")

        checksum = self._checksum_payload(payload)
        await self.repo.upsert_hedis_valueset(
            valueset_id=vid,
            payload_json=payload,
            code_system=str(payload.get("code_system", "")) or None,
            source="db",
            checksum=checksum,
            is_active=True,
            updated_by=updated_by,
        )

        path = self._hedis_valuesets_dir() / f"{vid}.json"
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"valueset_id": vid, "source": "db", "path": str(path), "checksum": checksum, "status": "saved"}

    async def delete_hedis_valueset_definition(self, valueset_id: str) -> dict[str, Any]:
        vid = valueset_id.strip()
        await self.repo.delete_hedis_valueset(vid)
        path = self._hedis_valuesets_dir() / f"{vid}.json"
        if path.exists():
            path.unlink()
        return {"valueset_id": vid, "status": "deleted"}

    async def bootstrap_hedis_registry_from_files(self, updated_by: str = "system") -> dict[str, Any]:
        measure_count = 0
        valueset_count = 0

        for path in sorted(self._hedis_catalog_dir().glob("*.yaml")):
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            if not payload.get("id"):
                continue
            mid = self._normalize_measure_id(str(payload["id"]))
            payload["id"] = mid
            parse_measure_dict(payload)
            checksum = self._checksum_payload(payload)
            await self.repo.upsert_hedis_measure_definition(
                measure_id=mid,
                definition_json=payload,
                version=str(payload.get("version", "2025")),
                source="imported",
                checksum=checksum,
                is_active=True,
                updated_by=updated_by,
            )
            measure_count += 1

        for path in sorted(self._hedis_valuesets_dir().glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            vid = str(payload.get("id") or path.stem)
            payload["id"] = vid
            if not isinstance(payload.get("codes", []), list):
                continue
            checksum = self._checksum_payload(payload)
            await self.repo.upsert_hedis_valueset(
                valueset_id=vid,
                payload_json=payload,
                code_system=str(payload.get("code_system", "")) or None,
                source="imported",
                checksum=checksum,
                is_active=True,
                updated_by=updated_by,
            )
            valueset_count += 1

        return {
            "status": "ok",
            "measure_definitions_synced": measure_count,
            "valuesets_synced": valueset_count,
        }
