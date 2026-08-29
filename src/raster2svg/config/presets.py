"""Application-level presets (PRD section 16).

The installed VTracer 0.6.x Python API exposes no native preset objects, so
these presets are defined by raster2svg as named bundles of canonical
configuration values (PRD section 16.1). A preset establishes starting
values only: explicit config-file values and CLI options still override it
(PRD sections 8 and 9.1).
"""

from __future__ import annotations

from typing import Any

PRESETS: dict[str, dict[str, Any]] = {
    "bw": {
        "clustering": "bw",
        "hierarchical": "stacked",
        "mode": "spline",
        "filter_speckle": 2,
        "path_precision": 3,
    },
    "photo": {
        "clustering": "color-cluster",
        "hierarchical": "stacked",
        "mode": "spline",
        "color_precision": 6,
        "layer_difference": 12,
        "path_precision": 3,
    },
    "poster": {
        "clustering": "color-cluster",
        "hierarchical": "cutout",
        "mode": "spline",
        "color_precision": 4,
        "layer_difference": 24,
        "path_precision": 3,
    },
}

PRESET_NOTE = "application-level preset (the installed VTracer exposes no native preset API)"


class UnknownPresetError(ValueError):
    """Raised when a preset name is not known."""

    def __init__(self, name: str) -> None:
        super().__init__(f"unknown preset {name!r}")
        self.name = name
        self.available = sorted(PRESETS)


def available_presets() -> list[str]:
    """Names of the built-in presets, sorted."""
    return sorted(PRESETS)


def get_preset(name: str) -> dict[str, Any]:
    if name not in PRESETS:
        raise UnknownPresetError(name)
    return dict(PRESETS[name])
