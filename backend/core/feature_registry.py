"""Feature registry — thin wrapper that re-exports from config for convenience."""

from config.feature_flags import FeatureFlagRegistry, get_feature_flags

__all__ = ["FeatureFlagRegistry", "get_feature_flags"]
