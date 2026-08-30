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


#: Advanced conversion options whose availability depends on the installed
#: tracing engine, each paired with the vtracer parameter it requires.
#: `--palette-file` and `--palette` both depend on the `palette` parameter.
#: The base options (clustering, hierarchical, mode, ...) work on every
#: supported engine and are intentionally not listed here.
ENGINE_DEPENDENT_OPTIONS: tuple[tuple[str, str], ...] = (
    ("--simplify", "simplify"),
    ("--palette", "palette"),
    ("--palette-file", "palette"),
    ("--max-colors", "max_colors"),
    ("--optimize", "optimize"),
    ("--binary-threshold", "binary_threshold"),
    ("--adaptive", "adaptive"),
    ("--adaptive-window", "adaptive_window"),
    ("--adaptive-t", "adaptive_t"),
    ("--watershed-detail", "watershed_detail"),
)


def split_engine_dependent(caps: EngineCapabilities) -> tuple[list[str], list[str]]:
    """Split the advanced options into (available, unavailable) for a given engine."""
    available: list[str] = []
    unavailable: list[str] = []
    for option, param in ENGINE_DEPENDENT_OPTIONS:
        (available if caps.supports(param) else unavailable).append(option)
    return available, unavailable
