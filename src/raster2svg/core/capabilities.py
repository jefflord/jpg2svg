"""Runtime detection of what the installed tracing engine supports.

PRD section 21: the installed VTracer API is authoritative. Capabilities are
introspected from the actual function signature so newer VTracer releases that
add parameters are picked up automatically.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version


@dataclass(frozen=True)
class EngineCapabilities:
    """A snapshot of what a tracing engine exposes at runtime."""

    name: str
    version: str
    supported_params: frozenset[str] = field(default_factory=frozenset)

    def supports(self, param: str) -> bool:
        return param in self.supported_params


def _package_version(distribution: str) -> str:
    try:
        return version(distribution)
    except PackageNotFoundError:
        return "unknown"


def detect_vtracer_capabilities() -> EngineCapabilities:
    """Introspect the installed vtracer package."""
    import vtracer

    signature = inspect.signature(vtracer.convert_image_to_svg_py)
    params = frozenset(
        name for name in signature.parameters if name not in {"image_path", "out_path"}
    )
    return EngineCapabilities(
        name="vtracer",
        version=_package_version("vtracer"),
        supported_params=params,
    )
