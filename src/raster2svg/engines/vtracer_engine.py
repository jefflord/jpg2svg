"""Adapter for the vtracer Python package (PRD sections 9, 21, and 35).

The canonical configuration keeps stable field names. The installed
vtracer 0.6.x API is narrower than the full PRD feature list, so this
adapter:

* maps canonical fields onto the installed function signature
* passes ``None`` (and ``False`` for optional booleans) through so the
  engine uses its own defaults
* raises UnsupportedFeatureError for explicitly requested settings the
  installed engine cannot accept (PRD section 33, rules 7 and 13)

Capability detection is dynamic (see core.capabilities), so a newer
VTracer that adds parameters starts working with the same config.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import vtracer

from raster2svg.config.models import Clustering, ConversionConfig, CurveMode
from raster2svg.core.capabilities import EngineCapabilities, detect_vtracer_capabilities
from raster2svg.core.errors import EngineError, UnsupportedFeatureError

#: Canonical config field -> vtracer parameter name (when present).
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

_COLORMODE_BY_CLUSTERING: dict[Clustering, str] = {
    Clustering.COLOR_CLUSTER: "color",
    Clustering.BW: "binary",
}

_MODE_BY_CURVE_MODE: dict[CurveMode, str] = {
    CurveMode.PIXEL: "none",
    CurveMode.POLYGON: "polygon",
    CurveMode.SPLINE: "spline",
}


class VTracerEngine:
    """Tracing engine backed by the installed vtracer package."""

    def __init__(self) -> None:
        self.capabilities: EngineCapabilities = detect_vtracer_capabilities()

    def trace(
        self,
        *,
        image_bytes: bytes,
        image_format: str | None,
        config: ConversionConfig,
    ) -> str:
        kwargs = self._build_kwargs(config)
        try:
            svg = vtracer.convert_raw_image_to_svg(image_bytes, img_format=image_format, **kwargs)
        except Exception as exc:
            raise EngineError(
                f"VTracer {self.capabilities.version} failed to trace the image: {exc}"
            ) from exc
        if not svg or not svg.strip():
            raise EngineError("VTracer produced an empty SVG document.")
        return str(svg)

    def _build_kwargs(self, config: ConversionConfig) -> dict[str, Any]:
        supported = self.capabilities.supported_params
        unsupported: list[str] = []
        kwargs: dict[str, Any] = {}
        for field_name, param_name in PARAMETER_MAP.items():
            value: Any = getattr(config, field_name)
            if value is None or value is False:
                continue
            if param_name not in supported:
                unsupported.append(field_name)
                continue
            kwargs[param_name] = self._translate(field_name, value)
        if unsupported:
            raise UnsupportedFeatureError(
                "Installed VTracer "
                f"{self.capabilities.version} does not support: "
                f"{', '.join(unsupported)}.",
                hint=(
                    "These options need VTracer 1.0 (not yet on PyPI). Remove "
                    "them, or upgrade once 1.0 is released. Run "
                    "`raster2svg engine capabilities` to see what the "
                    "installed engine supports."
                ),
            )
        return kwargs

    @staticmethod
    def _translate(field_name: str, value: Any) -> Any:
        if field_name == "clustering" and isinstance(value, Clustering):
            return _COLORMODE_BY_CLUSTERING[value]
        if field_name == "mode" and isinstance(value, CurveMode):
            return _MODE_BY_CURVE_MODE[value]
        if isinstance(value, Enum):
            return value.value
        return value
