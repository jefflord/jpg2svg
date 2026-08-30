"""Adapter for the VTracer 1.0 native executable (PRD sections 9, 21, 35).

VTracer 1.0 ships as a standalone binary (no Python bindings yet). On
Windows it is discovered from, in order:

1. ``RASTER2SVG_VTRACER_BIN`` (environment variable, full path)
2. ``vtracer`` on ``PATH``
3. ``.venv/Bin/vtracer.exe`` relative to the working directory (this repo's
   layout: the staged release binary lives in the virtualenv's ``Bin`` dir)

The first candidate that reports a 1.x version wins. The 1.0 CLI honours
the full option surface (``--simplify``, ``--palette``, ``--adaptive`` ...)
but not the four legacy smoothing thresholds the 0.6.x Python API takes
(``corner_threshold``, ``length_threshold``, ``max_iterations``,
``splice_threshold``), so the converter prefers this engine and falls back
to the Python engine for configs that use those legacy options.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from raster2svg.config.models import ConversionConfig
from raster2svg.core.capabilities import EngineCapabilities
from raster2svg.core.errors import EngineError, UnsupportedFeatureError
from raster2svg.engines.base import unsupported_fields

logger = logging.getLogger("raster2svg")

#: Environment variable that pins a specific VTracer 1.x binary.
VTRACER_BIN_ENV = "RASTER2SVG_VTRACER_BIN"

#: Canonical parameters the VTracer 1.0 CLI honours (from its --help
#: surface). Everything else in the shared namespace (the four legacy
#: smoothing thresholds) is a 0.6.x-only option.
VTRACER1_PARAMS: frozenset[str] = frozenset(
    {
        "colormode",
        "hierarchical",
        "mode",
        "filter_speckle",
        "color_precision",
        "layer_difference",
        "path_precision",
        "simplify",
        "palette",
        "max_colors",
        "optimize",
        "binary_threshold",
        "adaptive",
        "adaptive_window",
        "adaptive_t",
        "watershed_detail",
    }
)

#: How long a `--version` probe may take before it is dropped.
_PROBE_TIMEOUT_S = 10.0
#: How long a full conversion may take before it is aborted.
_DEFAULT_TRACE_TIMEOUT_S = 120.0

_VERSION_RE = re.compile(r"\bvtracer\s+(\d+(?:\.\d+)*(?:[-+][0-9A-Za-z.]+)?)", re.IGNORECASE)

_version_cache: dict[str, str | None] = {}


def parse_vtracer_version(text: str) -> str | None:
    """Extract a 1.x VTracer version from `--version` output, else None."""
    match = _VERSION_RE.search(text or "")
    if not match:
        return None
    version = match.group(1)
    try:
        major = int(version.split(".", 1)[0])
    except ValueError:
        return None
    return version if major >= 1 else None


def probe_vtracer_version(exe: Path) -> str | None:
    """Run `exe --version` and return the version if it reports 1.x."""
    key = os.path.realpath(exe)
    if key in _version_cache:
        return _version_cache[key]
    version: str | None = None
    try:
        completed = subprocess.run(
            [str(exe), "--version"],
            capture_output=True,
            text=True,
            timeout=_PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        logger.debug("VTracer probe failed for %s: %s", exe, exc)
    else:
        if completed.returncode == 0:
            version = parse_vtracer_version(completed.stdout or "")
            if version is None:
                version = parse_vtracer_version(completed.stderr or "")
    _version_cache[key] = version
    return version


def find_vtracer_binary() -> Path | None:
    """Locate a VTracer 1.x executable, or None when none is available.

    Windows-only: the staged 1.0 release binaries are Windows builds.
    """
    if sys.platform != "win32":
        return None
    candidates: list[Path] = []
    env_value = os.environ.get(VTRACER_BIN_ENV)
    if env_value:
        env_path = Path(env_value).expanduser()
        if env_path.is_file():
            candidates.append(env_path)
        else:
            logger.warning("%s=%s does not exist; ignoring it.", VTRACER_BIN_ENV, env_path)
    on_path = shutil.which("vtracer")
    if on_path:
        candidates.append(Path(on_path))
    candidates.append(Path.cwd() / ".venv" / "Bin" / "vtracer.exe")
    for candidate in candidates:
        if probe_vtracer_version(candidate) is not None:
            return candidate
    return None


def detect_vtracer_cli_capabilities() -> EngineCapabilities | None:
    """Capabilities of the detected VTracer 1.0 binary, or None."""
    binary = find_vtracer_binary()
    if binary is None:
        return None
    version = probe_vtracer_version(binary)
    if version is None:
        return None
    return EngineCapabilities(
        name="vtracer",
        version=version,
        supported_params=VTRACER1_PARAMS,
        origin="cli",
        binary=str(binary),
    )


def build_cli_argv(caps: EngineCapabilities, config: ConversionConfig) -> list[str]:
    """Build the VTracer 1.0 CLI flags for a resolved config.

    Pure function of (capabilities, config): no subprocess, no I/O, so it
    is unit-testable without a binary. Only set fields are emitted; the
    engine supplies its own defaults for the rest.
    """
    unsupported = unsupported_fields(caps, config)
    if unsupported:
        raise UnsupportedFeatureError(
            f"VTracer {caps.version} (CLI) does not support: {', '.join(unsupported)}.",
            hint="Remove those options, or use a VTracer build that honours them.",
        )

    def value_of(field_name: str) -> object:
        value = getattr(config, field_name)
        return value.value if hasattr(value, "value") else value

    def add(flag: str, value: object) -> None:
        argv.extend((flag, str(value)))

    argv: list[str] = []
    if config.clustering is not None:
        add("--clustering", value_of("clustering"))
    if config.hierarchical is not None:
        add("--hierarchical", value_of("hierarchical"))
    if config.mode is not None:
        add("-m", value_of("mode"))
    if config.filter_speckle is not None:
        add("-f", config.filter_speckle)
    if config.color_precision is not None:
        add("-p", config.color_precision)
    if config.layer_difference is not None:
        add("-g", config.layer_difference)
    if config.path_precision is not None:
        add("--path-precision", config.path_precision)
    if config.simplify is not None:
        add("--simplify", config.simplify)
    if config.palette is not None:
        add("--palette", ",".join(config.palette))
    if config.palette_file is not None:
        add("--palette-file", str(config.palette_file))
    if config.max_colors is not None:
        add("--max-colors", config.max_colors)
    if config.optimize is not None:
        add("--optimize", config.optimize)
    if config.binary_threshold is not None:
        add("--threshold", config.binary_threshold)
    if config.adaptive is True:
        argv.append("--adaptive")
    if config.adaptive_window is not None:
        add("--adaptive-window", config.adaptive_window)
    if config.adaptive_t is not None:
        add("--adaptive-t", config.adaptive_t)
    if config.watershed_detail is not None:
        add("--watershed-detail", config.watershed_detail)
    return argv


def _input_suffix(image_format: str | None) -> str:
    fmt = (image_format or "").strip().upper()
    if fmt in {"JPG", "JPEG"}:
        return ".jpg"
    if fmt in {"TIF", "TIFF"}:
        return ".tif"
    if fmt and fmt.isalnum():
        return f".{fmt.lower()}"
    return ".png"


class VTracerCLIEngine:
    """Tracing engine backed by the VTracer 1.0 native executable."""

    def __init__(self, binary: Path, *, timeout: float = _DEFAULT_TRACE_TIMEOUT_S) -> None:
        version = probe_vtracer_version(binary)
        if version is None:
            raise EngineError(
                f"Not a VTracer 1.x binary: {binary}",
                hint="Point RASTER2SVG_VTRACER_BIN at a VTracer 1.x executable.",
            )
        self.binary = binary
        self.timeout = timeout
        self.capabilities = EngineCapabilities(
            name="vtracer",
            version=version,
            supported_params=VTRACER1_PARAMS,
            origin="cli",
            binary=str(binary),
        )

    def trace(
        self,
        *,
        image_bytes: bytes,
        image_format: str | None,
        config: ConversionConfig,
    ) -> str:
        flags = build_cli_argv(self.capabilities, config)
        with tempfile.TemporaryDirectory(prefix="raster2svg-") as workdir:
            work = Path(workdir)
            input_path = work / f"input{_input_suffix(image_format)}"
            input_path.write_bytes(image_bytes)
            output_path = work / "output.svg"
            command = [str(self.binary), str(input_path), str(output_path), *flags]
            logger.debug("vtracer CLI: %s", " ".join(command))
            try:
                completed = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise EngineError(
                    f"VTracer {self.capabilities.version} timed out after "
                    f"{self.timeout:.0f}s."
                ) from exc
            except OSError as exc:
                raise EngineError(f"Failed to run VTracer: {exc}") from exc
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout or "").strip()
                raise EngineError(
                    f"VTracer {self.capabilities.version} failed: {detail or 'no error output'}"
                )
            if not output_path.is_file():
                raise EngineError("VTracer did not write an output file.")
            svg = output_path.read_text(encoding="utf-8")
        if not svg or not svg.strip():
            raise EngineError("VTracer produced an empty SVG document.")
        return svg
