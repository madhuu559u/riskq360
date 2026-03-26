"""Dynamic feature flag registry.

Allows runtime toggling of features via API/dashboard without restart.
Falls back to environment-based defaults from settings.
"""

from __future__ import annotations

import threading
from typing import Dict, Optional

from config.settings import FeatureFlags, PipelineMode, get_settings


class FeatureFlagRegistry:
    """Thread-safe, runtime-mutable feature flag store."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._overrides: Dict[str, bool] = {}
        self._defaults = get_settings().features

    # -- read -----------------------------------------------------------

    def is_enabled(self, flag: str) -> bool:
        """Check if a feature flag is enabled (override > env default)."""
        with self._lock:
            if flag in self._overrides:
                return self._overrides[flag]
        return getattr(self._defaults, flag, False)

    @property
    def risk_adjustment(self) -> bool:
        return self.is_enabled("risk_adjustment")

    @property
    def hedis(self) -> bool:
        return self.is_enabled("hedis")

    @property
    def ml_predictions(self) -> bool:
        return self.is_enabled("ml_predictions")

    @property
    def llm_verification(self) -> bool:
        return self.is_enabled("llm_verification")

    @property
    def ocr_fallback(self) -> bool:
        return self.is_enabled("ocr_fallback")

    @property
    def parallel_pipelines(self) -> bool:
        return self.is_enabled("parallel_pipelines")

    @property
    def audit_logging(self) -> bool:
        return self.is_enabled("audit_logging")

    # -- write ----------------------------------------------------------

    def set_flag(self, flag: str, value: bool) -> None:
        """Override a feature flag at runtime."""
        with self._lock:
            self._overrides[flag] = value

    def clear_override(self, flag: str) -> None:
        """Remove runtime override, reverting to env default."""
        with self._lock:
            self._overrides.pop(flag, None)

    def clear_all_overrides(self) -> None:
        with self._lock:
            self._overrides.clear()

    def apply_mode(self, mode: PipelineMode) -> None:
        """Apply a pipeline mode preset, toggling flags accordingly."""
        if mode == PipelineMode.RISK_ONLY:
            self.set_flag("risk_adjustment", True)
            self.set_flag("hedis", False)
            self.set_flag("ml_predictions", True)
            self.set_flag("llm_verification", True)
        elif mode == PipelineMode.HEDIS_ONLY:
            self.set_flag("risk_adjustment", False)
            self.set_flag("hedis", True)
            self.set_flag("ml_predictions", False)
            self.set_flag("llm_verification", False)
        elif mode == PipelineMode.HCC_PACK:
            self.set_flag("risk_adjustment", True)
            self.set_flag("hedis", False)
            self.set_flag("ml_predictions", True)
            self.set_flag("llm_verification", True)
        elif mode == PipelineMode.FULL:
            self.clear_all_overrides()

    # -- snapshot -------------------------------------------------------

    def snapshot(self) -> Dict[str, bool]:
        """Return current effective values for all flags."""
        flags = [
            "risk_adjustment", "hedis", "ml_predictions",
            "llm_verification", "ocr_fallback", "parallel_pipelines",
            "audit_logging",
        ]
        return {f: self.is_enabled(f) for f in flags}


# Module-level singleton
_registry: Optional[FeatureFlagRegistry] = None


def get_feature_flags() -> FeatureFlagRegistry:
    global _registry
    if _registry is None:
        _registry = FeatureFlagRegistry()
    return _registry
