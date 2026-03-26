"""Value set loader with DB-first fallback support."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from ..db_registry import load_valueset_payload_from_db

_VALUESET_DIR = Path(__file__).parent
_cache: dict[str, set[str]] = {}


def _normalize_code(code: str) -> str:
    """Normalize a code for comparison."""
    return code.strip().upper().replace(".", "")


def load_valueset(valueset_id: str, base_dir: Optional[Path] = None) -> set[str]:
    """Load a value set by ID and return normalized codes.

    Source order is controlled by env var ``HEDIS_VALUESET_SOURCE``:
    - ``db_first`` (default)
    - ``file_first``
    - ``db_only``
    - ``file_only``
    """
    if valueset_id in _cache:
        return _cache[valueset_id]

    source_mode = (os.getenv("HEDIS_VALUESET_SOURCE") or "db_first").strip().lower()
    if source_mode not in {"db_first", "file_first", "db_only", "file_only"}:
        source_mode = "db_first"

    if source_mode in {"db_first", "db_only"}:
        db_codes = _load_from_db(valueset_id)
        if db_codes is not None:
            return db_codes
        if source_mode == "db_only":
            _cache[valueset_id] = set()
            return set()

    file_codes = _load_from_files(valueset_id, base_dir)
    if file_codes is not None:
        return file_codes

    if source_mode == "file_first":
        db_codes = _load_from_db(valueset_id)
        if db_codes is not None:
            return db_codes

    _cache[valueset_id] = set()
    return set()


def _load_from_files(valueset_id: str, base_dir: Optional[Path] = None) -> Optional[set[str]]:
    search_dir = base_dir or _VALUESET_DIR
    candidates = [
        search_dir / f"{valueset_id}.json",
        search_dir / f"{valueset_id.lower()}.json",
    ]

    for path in candidates:
        if path.exists():
            return _load_from_file(valueset_id, path)

    for path in search_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if data.get("id") == valueset_id:
                return _load_from_file(valueset_id, path)
        except (json.JSONDecodeError, KeyError):
            continue
    return None


def _load_from_file(valueset_id: str, path: Path) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    codes: set[str] = set()
    for entry in data.get("codes", []):
        code = entry if isinstance(entry, str) else entry.get("code", "")
        if code:
            codes.add(_normalize_code(code))
    _cache[valueset_id] = codes
    return codes


def _load_from_db(valueset_id: str) -> Optional[set[str]]:
    payload = load_valueset_payload_from_db(valueset_id)
    if not isinstance(payload, dict):
        return None
    codes: set[str] = set()
    for entry in payload.get("codes", []):
        code = entry if isinstance(entry, str) else entry.get("code", "")
        if code:
            codes.add(_normalize_code(code))
    _cache[valueset_id] = codes
    return codes


def clear_cache() -> None:
    _cache.clear()


def code_in_valueset(code: str, valueset_id: str, base_dir: Optional[Path] = None) -> bool:
    vs = load_valueset(valueset_id, base_dir)
    return _normalize_code(code) in vs

