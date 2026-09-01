"""The reusable conversion service used by the CLI and any future GUI.

Pipeline (PRD section 4.1):

    input -> validation -> configuration resolution -> VTracer
         -> SVG validation -> atomic output -> result
"""

from __future__ import annotations

import hashlib
import logging
import time
from pathlib import Path
from typing import Any

from PIL import Image, UnidentifiedImageError

from raster2svg._version import __version__
from raster2svg.config.models import (
    ConversionConfig,
    OutputConfig,
    PostprocessConfig,
    PreprocessConfig,
)
from raster2svg.config.presets import resolve_preset
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.core.capabilities import EngineCapabilities, merge_capabilities
from raster2svg.core.errors import InputError, OutputError, UnsupportedFeatureError
from raster2svg.core.models import STATUS_DRY_RUN, STATUS_SUCCESS, ConversionResult
from raster2svg.engines import discover_engines
from raster2svg.engines.base import TracingEngine, unsupported_fields
from raster2svg.output.atomic_write import atomic_write_text
from raster2svg.output.svg import validate_svg
from raster2svg.postprocess.svg import apply_postprocessing
from raster2svg.preprocess.image import apply_preprocessing
from raster2svg.utils.paths import default_output_path, image_format_hint, validate_input_path

logger = logging.getLogger("raster2svg")


class Converter:
    """Public library API (PRD section 23).

    Example:
        >>> from raster2svg import Converter, ConversionConfig
        >>> result = Converter().convert(
        ...     input_path="photo.jpg",
        ...     output_path="photo.svg",
        ...     config=ConversionConfig(preset="photo"),
        ... )
    """

    def __init__(self, engine: TracingEngine | None = None) -> None:
        self._engines = [engine] if engine is not None else discover_engines()

    @property
    def engines(self) -> list[TracingEngine]:
        """All available engines, most preferred first."""
        return list(self._engines)

    @property
    def capabilities(self) -> EngineCapabilities:
        """Capabilities of the preferred engine (first in `engines`)."""
        return self._engines[0].capabilities

    @property
    def capabilities_union(self) -> EngineCapabilities:
        """Union of what every available engine honours (option gating)."""
        return merge_capabilities([engine.capabilities for engine in self._engines])

    def _select_engine(self, config: ConversionConfig) -> TracingEngine:
        """Pick the best engine for this config.

        The preferred engine is used unless the config sets options it
        cannot honour; then the first engine with full support wins
        (smart fallback). Raises UnsupportedFeatureError when no engine
        can handle the config.
        """
        for engine in self._engines:
            if not unsupported_fields(engine.capabilities, config):
                return engine
        missing: set[str] = set()
        for engine in self._engines:
            missing.update(unsupported_fields(engine.capabilities, config))
        raise UnsupportedFeatureError(
            f"Installed VTracer does not support: {', '.join(sorted(missing))}.",
            hint=(
                "These options need VTracer 1.0. Run "
                "`raster2svg engine capabilities` to see what the installed "
                "engines support."
            ),
        )

    def convert(
        self,
        input_path: str | Path,
        output_path: str | Path | None = None,
        *,
        config: ConversionConfig | None = None,
        output: OutputConfig | None = None,
        preprocess: PreprocessConfig | None = None,
        postprocess: PostprocessConfig | None = None,
        dry_run: bool = False,
    ) -> ConversionResult:
        """Convert one raster image to SVG.

        Raises a subclass of Raster2SvgError on any failure; the CLI maps
        these to exit codes and actionable messages.
        """
        input_path = Path(input_path)
        output_cfg = output or OutputConfig()
        conversion_cfg = _apply_preset(config or ConversionConfig())
        preprocess_cfg = preprocess or _preset_preprocess(conversion_cfg)
        postprocess_cfg = postprocess or _preset_postprocess(conversion_cfg)

        input_path = validate_input_path(input_path)
        target = Path(output_path) if output_path is not None else default_output_path(input_path)
        width, height, fmt = self._inspect_input(input_path)
        logger.debug("input: %s (%s %dx%d)", input_path, fmt, width, height)
        self._check_output_path(target, output_cfg)
        engine = self._select_engine(conversion_cfg)
        image_bytes = input_path.read_bytes()

        prepared = apply_preprocessing(
            image_bytes,
            image_format_hint(input_path) or "unknown",
            preprocess_cfg,
        )
        logger.debug(
            "preprocessing: %s",
            ", ".join(prepared.applied) if prepared.applied else "none",
        )

        if dry_run:
            return ConversionResult(
                status=STATUS_DRY_RUN,
                input_path=input_path,
                output_path=target,
                tool_version=__version__,
                engine_name=engine.capabilities.name,
                engine_version=engine.capabilities.version,
                duration_ms=0,
                config=_config_dict(conversion_cfg),
                input_format=fmt,
                input_width=width,
                input_height=height,
                preprocess=_preprocess_dict(preprocess_cfg),
                preprocess_applied=list(prepared.applied),
                postprocess=_postprocess_dict(postprocess_cfg),
                postprocess_applied=[],
            )

        started = time.perf_counter()
        svg = engine.trace(
            image_bytes=prepared.image_bytes,
            image_format=prepared.image_format,
            config=conversion_cfg,
        )
        post_result = apply_postprocessing(svg, postprocess_cfg)
        svg = post_result.svg
        if post_result.applied:
            logger.debug("postprocessing: %s", ", ".join(post_result.applied))
        svg_bytes = svg.encode("utf-8")
        logger.debug("traced: %d bytes of SVG", len(svg))
        if output_cfg.validate_svg:
            validate_svg(svg)
        atomic_write_text(
            target,
            svg,
            overwrite=output_cfg.overwrite,
            create_directories=output_cfg.create_directories,
        )
        logger.debug("wrote: %s", target)
        duration_ms = int((time.perf_counter() - started) * 1000)
        return ConversionResult(
            status=STATUS_SUCCESS,
            input_path=input_path,
            output_path=target,
            tool_version=__version__,
            engine_name=engine.capabilities.name,
            engine_version=engine.capabilities.version,
            duration_ms=duration_ms,
            config=_config_dict(conversion_cfg),
            output_bytes=len(svg_bytes),
            output_sha256=hashlib.sha256(svg_bytes).hexdigest(),
            input_format=fmt,
            input_width=width,
            input_height=height,
            preprocess=_preprocess_dict(preprocess_cfg),
            preprocess_applied=list(prepared.applied),
            postprocess=_postprocess_dict(postprocess_cfg),
            postprocess_applied=list(post_result.applied),
        )

    def convert_bytes(
        self,
        image_bytes: bytes,
        image_format: str,
        *,
        config: ConversionConfig | None = None,
        preprocess: PreprocessConfig | None = None,
        postprocess: PostprocessConfig | None = None,
    ) -> tuple[str, list[str]]:
        """Convert in-memory image bytes to an SVG string without touching disk.

        Reuses the exact preprocessing + tracing + post-processing pipeline of
        :meth:`convert`, but takes raw bytes and returns the SVG text plus the
        list of preprocessing operations that were applied. Used by the web
        interface for real-time preview; the file-based :meth:`convert` stays
        untouched.

        Raises a subclass of Raster2SvgError on any failure.
        """
        conversion_cfg = _apply_preset(config or ConversionConfig())
        preprocess_cfg = preprocess or _preset_preprocess(conversion_cfg)
        postprocess_cfg = postprocess or _preset_postprocess(conversion_cfg)
        prepared = apply_preprocessing(image_bytes, image_format, preprocess_cfg)
        engine = self._select_engine(conversion_cfg)
        svg = engine.trace(
            image_bytes=prepared.image_bytes,
            image_format=prepared.image_format,
            config=conversion_cfg,
        )
        svg = apply_postprocessing(svg, postprocess_cfg).svg
        return svg, list(prepared.applied)

    @staticmethod
    def _inspect_input(path: Path) -> tuple[int, int, str]:
        """Decode the image to verify it and read dimensions (PRD 5.3)."""
        try:
            with Image.open(path) as image:
                image.load()
                width, height = image.size
                fmt = (image.format or "UNKNOWN").upper()
        except (OSError, UnidentifiedImageError) as exc:
            raise InputError(
                f"Cannot decode image: {path}",
                hint="The file is corrupt or not a supported raster image.",
            ) from exc
        if width <= 0 or height <= 0:
            raise InputError(f"Image has invalid dimensions {width}x{height}: {path}")
        return width, height, fmt

    @staticmethod
    def _check_output_path(target: Path, output_cfg: OutputConfig) -> None:
        if target.exists() and not output_cfg.overwrite:
            raise OutputError(
                f"Output file already exists: {target}",
                hint="Use --overwrite to replace it.",
            )
        if not target.parent.exists() and not output_cfg.create_directories:
            raise OutputError(
                f"Output directory does not exist: {target.parent}",
                hint="Omit --no-mkdir to allow creating it.",
            )


def _apply_preset(config: ConversionConfig) -> ConversionConfig:
    """Expand a preset named in the config (library API, PRD 23).

    The CLI resolves presets itself; library callers pass
    ``ConversionConfig(preset="photo", ...)`` and expect the same
    semantics: the preset supplies initial values and any other field set
    on the config wins (PRD 8, 16).
    """
    if config.preset is None:
        return config
    other = {key: value for key, value in config.model_dump().items() if key != "preset"}
    return resolve_conversion_config(preset=config.preset, config_file_values=other)


def _preset_preprocess(config: ConversionConfig) -> PreprocessConfig:
    """The preset's [preprocess] section, used when none was passed explicitly.

    Library callers pass ``ConversionConfig(preset="clip-art")`` and expect
    the preset to supply *both* the tracing and the preprocessing starting
    values; an explicit ``PreprocessConfig`` always wins as-is.
    """
    if config.preset is None:
        return PreprocessConfig()
    return PreprocessConfig.from_dict(resolve_preset(config.preset).preprocess)


def _preset_postprocess(config: ConversionConfig) -> PostprocessConfig:
    """The preset's [postprocess] section, used when none was passed explicitly.

    Library callers pass ``ConversionConfig(preset="line-art-inverted")`` and
    expect the preset to supply the post-processing starting values; an
    explicit ``PostprocessConfig`` always wins as-is.
    """
    if config.preset is None:
        return PostprocessConfig()
    return PostprocessConfig.from_dict(resolve_preset(config.preset).postprocess)


def _config_dict(config: ConversionConfig) -> dict[str, Any]:
    return config.model_dump(mode="json")


def _preprocess_dict(config: PreprocessConfig) -> dict[str, Any]:
    return config.model_dump(mode="json")


def _postprocess_dict(config: PostprocessConfig) -> dict[str, Any]:
    return config.model_dump(mode="json")
