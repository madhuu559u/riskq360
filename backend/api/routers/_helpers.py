"""Shared helpers for API routers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config.settings import get_settings


def load_chart_output(chart_id: str, filename: str) -> Optional[Dict[str, Any]]:
    """Load a JSON output file for a chart."""
    settings = get_settings()
    filepath = settings.paths.output_dir / chart_id / filename
    if filepath.exists():
        return json.loads(filepath.read_text(encoding="utf-8"))
    return None
