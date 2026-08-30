"""Shared CLI option definitions and resolution (PRD sections 8, 9, 11).

``convert`` and ``batch`` expose the same conversion settings. Defining each
option once here keeps the two command surfaces in sync (single source of
truth for names, aliases, and help text).
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any

import typer

from raster2svg.config.loader import load_config_file
from raster2svg.config.models import ConversionConfig, OutputConfig, PreprocessConfig
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.config.user_config import load_user_config

PresetOption = Annotated[
    str | None,
    typer.Option(
        "--preset",
        help="Starting preset: bw, photo, poster, or a saved custom preset.",
    ),
]

ConfigPathOption = Annotated[
    Path | None,
    typer.Option(
        "--config",
        help="Config file (.toml or .json) with conversion and output settings. "
        "CLI options still override it.",
    ),
]

ClusteringOption = Annotated[
    str | None,
    typer.Option("--clustering", help="color-cluster, bw, or watershed."),
]

HierarchicalOption = Annotated[
    str | None,
    typer.Option("--hierarchical", help="stacked or cutout."),
]

ModeOption = Annotated[
    str | None,
    typer.Option("--mode", help="pixel, polygon, or spline."),
]

FilterSpeckleOption = Annotated[
    int | None,
    typer.Option("--filter-speckle", help="Speckle filter size, 1-100."),
]

ColorPrecisionOption = Annotated[
    int | None,
    typer.Option("--color-precision", help="Bits per RGB channel, 1-8."),
]

LayerDifferenceOption = Annotated[
    int | None,
    typer.Option(
        "--layer-difference",
        "--gradient-step",
        help="Color difference between layers, 1-255.",
    ),
]

CornerThresholdOption = Annotated[
    float | None,
    typer.Option("--corner-threshold", help="Corner angle in degrees, 0-180."),
]

LengthThresholdOption = Annotated[
    float | None,
    typer.Option(
        "--length-threshold",
        "--segment-length",
        help="Segment length, 3.5-10.",
    ),
]

MaxIterationsOption = Annotated[
    int | None,
    typer.Option("--max-iterations", help="Curve-fitting iterations, 1-100."),
]

SpliceThresholdOption = Annotated[
    float | None,
    typer.Option("--splice-threshold", help="Splice angle in degrees, 0-180."),
]

PathPrecisionOption = Annotated[
    int | None,
    typer.Option("--path-precision", help="Decimal places in path data, 0-8."),
]

SimplifyOption = Annotated[
    float | None,
    typer.Option(
        "--simplify",
        help="Curve simplification tolerance (>0). May be unsupported by the installed engine.",
    ),
]

PaletteOption = Annotated[
    str | None,
    typer.Option(
        "--palette",
        help="Comma-separated hex colors, e.g. '#111,#eee'. "
        "May be unsupported by the installed engine.",
    ),
]

PaletteFileOption = Annotated[
    Path | None,
    typer.Option(
        "--palette-file",
        help="File with one hex color per line. May be unsupported by the installed engine.",
    ),
]

MaxColorsOption = Annotated[
    int | None,
    typer.Option(
        "--max-colors",
        help="Quantize to N colors. May be unsupported by the installed engine.",
    ),
]

OptimizeOption = Annotated[
    int | None,
    typer.Option(
        "--optimize",
        help="Optimization level 0-2. May be unsupported by the installed engine.",
    ),
]

BinaryThresholdOption = Annotated[
    int | None,
    typer.Option(
        "--binary-threshold",
        "--threshold",
        help="Binary threshold 0-255. May be unsupported by the installed engine.",
    ),
]

AdaptiveOption = Annotated[
    bool | None,
    typer.Option(
        "--adaptive/--no-adaptive",
        help="Adaptive thresholding; implies --clustering bw. "
        "May be unsupported by the installed engine.",
    ),
]

AdaptiveWindowOption = Annotated[
    int | None,
    typer.Option(
        "--adaptive-window",
        help="Adaptive window size (>=3). May be unsupported by the installed engine.",
    ),
]

AdaptiveTOption = Annotated[
    int | None,
    typer.Option(
        "--adaptive-t",
        help="Adaptive threshold constant (>=0). May be unsupported by the installed engine.",
    ),
]

WatershedDetailOption = Annotated[
    int | None,
    typer.Option(
        "--watershed-detail",
        help="Watershed detail 0-255. May be unsupported by the installed engine.",
    ),
]

AutoOrientOption = Annotated[
    bool | None,
    typer.Option(
        "--auto-orient/--no-auto-orient",
        help="Apply EXIF orientation before tracing (default: on).",
    ),
]

ResizeOption = Annotated[
    str | None,
    typer.Option(
        "--resize",
        help="Resize to fit within WxH, preserving aspect (e.g. 1920x1080).",
    ),
]

MaxWidthOption = Annotated[
    int | None,
    typer.Option("--max-width", help="Shrink so the width is at most N pixels."),
]

MaxHeightOption = Annotated[
    int | None,
    typer.Option("--max-height", help="Shrink so the height is at most N pixels."),
]

ScaleOption = Annotated[
    float | None,
    typer.Option("--scale", help="Scale both dimensions by a factor (e.g. 0.5)."),
]

GrayscaleOption = Annotated[
    bool | None,
    typer.Option("--grayscale/--color", help="Convert the image to grayscale."),
]

DenoiseOption = Annotated[
    bool | None,
    typer.Option("--denoise/--no-denoise", help="Apply a conservative speckle denoiser."),
]

ContrastOption = Annotated[
    float | None,
    typer.Option("--contrast", help="Contrast factor, 1.0 = unchanged, 0-10."),
]

BrightnessOption = Annotated[
    float | None,
    typer.Option("--brightness", help="Brightness factor, 1.0 = unchanged, 0-10."),
]

SharpenOption = Annotated[
    bool | None,
    typer.Option("--sharpen/--no-sharpen", help="Apply a conservative unsharp-mask."),
]

OverwriteOption = Annotated[
    bool | None,
    typer.Option(
        "--overwrite/--no-overwrite",
        help="Replace an existing output file (default: refuse).",
    ),
]

NoMkdirOption = Annotated[
    bool | None,
    typer.Option(
        "--no-mkdir/--mkdir",
        help="Do not create the output directory (default: create).",
    ),
]

ValidateSvgOption = Annotated[
    bool | None,
    typer.Option(
        "--validate-svg/--no-validate-svg",
        help="Validate generated SVG as XML (default on).",
    ),
]

DryRunOption = Annotated[
    bool,
    typer.Option("--dry-run", help="Validate everything but do not write output."),
]

ReportPathOption = Annotated[
    Path | None,
    typer.Option("--report", help="Write a JSON report to this path."),
]


def build_cli_values(
    *,
    clustering: str | None = None,
    hierarchical: str | None = None,
    mode: str | None = None,
    filter_speckle: int | None = None,
    color_precision: int | None = None,
    layer_difference: int | None = None,
    corner_threshold: float | None = None,
    length_threshold: float | None = None,
    max_iterations: int | None = None,
    splice_threshold: float | None = None,
    path_precision: int | None = None,
    simplify: float | None = None,
    palette: str | None = None,
    palette_file: Path | None = None,
    max_colors: int | None = None,
    optimize: int | None = None,
    binary_threshold: int | None = None,
    adaptive: bool | None = None,
    adaptive_window: int | None = None,
    adaptive_t: int | None = None,
    watershed_detail: int | None = None,
) -> dict[str, object]:
    """Assemble the CLI value dict consumed by the resolver (PRD section 11)."""
    palette_list: list[str] | None = None
    if palette is not None:
        palette_list = [part.strip() for part in palette.split(",") if part.strip()]
    return {
        "clustering": clustering,
        "hierarchical": hierarchical,
        "mode": mode,
        "filter_speckle": filter_speckle,
        "color_precision": color_precision,
        "layer_difference": layer_difference,
        "corner_threshold": corner_threshold,
        "length_threshold": length_threshold,
        "max_iterations": max_iterations,
        "splice_threshold": splice_threshold,
        "path_precision": path_precision,
        "simplify": simplify,
        "palette": palette_list,
        "palette_file": palette_file,
        "max_colors": max_colors,
        "optimize": optimize,
        "binary_threshold": binary_threshold,
        "adaptive": adaptive,
        "adaptive_window": adaptive_window,
        "adaptive_t": adaptive_t,
        "watershed_detail": watershed_detail,
    }


def resolve_output(
    overwrite: bool | None,
    validate_svg: bool | None,
    no_mkdir: bool | None,
    file_values: dict[str, Any],
) -> OutputConfig:
    """Resolve output settings: CLI flag > config file [output] > default (PRD 8, 14)."""

    def pick(cli_value: bool | None, key: str, default: bool) -> bool:
        if cli_value is not None:
            return cli_value
        return bool(file_values.get(key, default))

    if no_mkdir is not None:
        create_directories = not no_mkdir
    else:
        create_directories = bool(file_values.get("create_directories", True))

    return OutputConfig(
        overwrite=pick(overwrite, "overwrite", False),
        validate_svg=pick(validate_svg, "validate_svg", True),
        create_directories=create_directories,
    )


def resolve_preprocess(
    *,
    auto_orient: bool | None = None,
    resize: str | None = None,
    max_width: int | None = None,
    max_height: int | None = None,
    scale: float | None = None,
    grayscale: bool | None = None,
    denoise: bool | None = None,
    contrast: float | None = None,
    brightness: float | None = None,
    sharpen: bool | None = None,
    file_values: dict[str, Any] | None = None,
) -> PreprocessConfig:
    """Resolve preprocessing: CLI flag > config file [preprocess] > default (PRD 8, 13)."""
    file_values = file_values or {}

    def pick(cli_value: Any, key: str, default: Any) -> Any:
        if cli_value is not None:
            return cli_value
        return file_values.get(key, default)

    data = {
        "auto_orient": bool(pick(auto_orient, "auto_orient", True)),
        "resize": pick(resize, "resize", None),
        "max_width": pick(max_width, "max_width", None),
        "max_height": pick(max_height, "max_height", None),
        "scale": pick(scale, "scale", None),
        "grayscale": bool(pick(grayscale, "grayscale", False)),
        "denoise": bool(pick(denoise, "denoise", False)),
        "contrast": pick(contrast, "contrast", None),
        "brightness": pick(brightness, "brightness", None),
        "sharpen": bool(pick(sharpen, "sharpen", False)),
    }
    # from_dict translates validation errors into a ConfigError (exit code 2).
    return PreprocessConfig.from_dict(data)


def resolve_cli_options(
    *,
    preset: str | None,
    config_path: Path | None,
    cli_values: dict[str, object],
    overwrite: bool | None,
    validate_svg: bool | None,
    no_mkdir: bool | None,
    preprocess_kwargs: dict[str, Any] | None = None,
) -> tuple[ConversionConfig, OutputConfig, PreprocessConfig]:
    """Apply PRD section 8 precedence for one CLI invocation.

    Raises Raster2SvgError subclasses (ConfigError, UnknownPresetError, ...)
    for invalid input.
    """
    file_cfg: dict[str, Any] = {"conversion": {}, "preprocess": {}, "output": {}}
    if config_path is not None:
        file_cfg = load_config_file(config_path)

    # PRD 8: the user-level config file (level 3) sits below the explicit
    # --config file (level 4). Merge per section so the file overrides key
    # by key while user values fill the gaps.
    user_cfg = load_user_config()
    file_cfg = {
        section: {**user_cfg[section], **file_cfg[section]}
        for section in ("conversion", "preprocess", "output")
    }

    config = resolve_conversion_config(
        preset=preset,
        config_file_values=file_cfg.get("conversion"),
        cli_values=cli_values,
    )
    output_cfg = resolve_output(overwrite, validate_svg, no_mkdir, file_cfg.get("output") or {})
    preprocess_cfg = resolve_preprocess(
        **(preprocess_kwargs or {}),
        file_values=file_cfg.get("preprocess") or {},
    )
    return config, output_cfg, preprocess_cfg
