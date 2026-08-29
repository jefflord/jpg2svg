"""Engine interface shared by all tracing backends."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

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
