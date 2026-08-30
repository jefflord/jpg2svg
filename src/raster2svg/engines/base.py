"""Engine interface shared by all tracing backends."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from raster2svg.config.models import ConversionConfig
from raster2svg.core.capabilities import EngineCapabilities


@runtime_checkable
class TracingEngine(Protocol):
    """A raster-to-vector tracing engine."""

    capabilities: EngineCapabilities

    def trace(
        self,
        *,
        image_bytes: bytes,
        image_format: str | None,
        config: ConversionConfig,
    ) -> str:
        """Trace raster pixels and return SVG markup."""
        ...


#: Canonical config field -> vtracer parameter name.
#:
#: The parameter namespace is shared by every engine (the 0.6.x Python API
#: and the 1.x CLI both honour the same canonical names), so capability
#: checks and option gating work uniformly. Each engine maps the canonical
#: names onto its own real API (e.g. the 1.0 CLI takes
#: ``--gradient-step`` for ``layer_difference`` and ``--threshold`` for
#: ``binary_threshold``).
PARAMETER_MAP: dict[str, str] = {
    "clustering": "colormode",
    "hierarchical": "hierarchical",
    "mode": "mode",
    "filter_speckle": "filter_speckle",
    "color_precision": "color_precision",
    "layer_difference": "layer_difference",
    "corner_threshold": "corner_threshold",
    "length_threshold": "length_threshold",
    "max_iterations": "max_iterations",
    "splice_threshold": "splice_threshold",
    "path_precision": "path_precision",
    "simplify": "simplify",
    "palette": "palette",
    "max_colors": "max_colors",
    "optimize": "optimize",
    "binary_threshold": "binary_threshold",
    "adaptive": "adaptive",
    "adaptive_window": "adaptive_window",
    "adaptive_t": "adaptive_t",
    "watershed_detail": "watershed_detail",
}


def unsupported_fields(
    caps: EngineCapabilities,
    config: ConversionConfig,
) -> list[str]:
    """Config fields the engine cannot honour.

    A field counts as "set" when it is neither ``None`` nor ``False`` (the
    engine defaults for optional booleans). Only fields that are part of
    the shared parameter namespace are considered; engines may extend it
    per-API.
    """
    unsupported: list[str] = []
    for field_name, param_name in PARAMETER_MAP.items():
        value: Any = getattr(config, field_name, None)
        if value is None or value is False:
            continue
        if param_name not in caps.supported_params:
            unsupported.append(field_name)
    return unsupported
