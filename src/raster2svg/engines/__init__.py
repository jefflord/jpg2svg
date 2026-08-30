"""Tracing engine backends (PRD section 22).

Engines are discovered at construction time, in preference order:

1. The VTracer 1.0 native executable (Windows; lookup order in
   `raster2svg.engines.vtracer_cli`).
2. The vtracer Python package (0.6.x today).

`discover_engines()` returns both when available; the converter prefers the
first engine and falls back to the older one for configs that use options
only it honours.
"""

from __future__ import annotations

from raster2svg.engines.base import PARAMETER_MAP, TracingEngine, unsupported_fields
from raster2svg.engines.vtracer_cli import (
    VTRACER1_PARAMS,
    VTRACER_BIN_ENV,
    VTracerCLIEngine,
    build_cli_argv,
    detect_vtracer_cli_capabilities,
    find_vtracer_binary,
)
from raster2svg.engines.vtracer_engine import VTracerEngine

__all__ = [
    "PARAMETER_MAP",
    "TracingEngine",
    "VTRACER_BIN_ENV",
    "VTRACER1_PARAMS",
    "VTracerCLIEngine",
    "VTracerEngine",
    "build_cli_argv",
    "detect_vtracer_cli_capabilities",
    "discover_engines",
    "find_vtracer_binary",
    "unsupported_fields",
]


def discover_engines() -> list[TracingEngine]:
    """Return the available engines, most preferred first."""
    engines: list[TracingEngine] = []
    binary = find_vtracer_binary()
    if binary is not None:
        engines.append(VTracerCLIEngine(binary))
    engines.append(VTracerEngine())
    return engines
