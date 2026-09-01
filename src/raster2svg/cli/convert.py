"""The `convert` command (PRD sections 7, 9, 11).

Both positional and named input/output are supported (PRD 7.2/7.3); when both
are given, the named flag wins.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from raster2svg.cli.help import show_help_for
from raster2svg.cli.options import (
    AdaptiveOption,
    AdaptiveTOption,
    AdaptiveWindowOption,
    AutocontrastOption,
    AutoOrientOption,
    BinaryThresholdOption,
    BlurOption,
    BrightnessOption,
    ClusteringOption,
    ColorPrecisionOption,
    ConfigPathOption,
    ContrastOption,
    CornerThresholdOption,
    DenoiseOption,
    DryRunOption,
    FilterSpeckleOption,
    GrayscaleOption,
    HierarchicalOption,
    InvertOption,
    LayerDifferenceOption,
    LengthThresholdOption,
    MaxColorsOption,
    MaxHeightOption,
    MaxIterationsOption,
    MaxWidthOption,
    ModeOption,
    NoMkdirOption,
    OptimizeOption,
    OverwriteOption,
    PaletteFileOption,
    PaletteOption,
    PathPrecisionOption,
    PosterizeOption,
    PreMaxColorsOption,
    PresetOption,
    ReportPathOption,
    ResizeOption,
    ScaleOption,
    SharpenOption,
    SimplifyOption,
    SpliceThresholdOption,
    ValidateSvgOption,
    WatershedDetailOption,
    build_cli_values,
    resolve_cli_options,
)
from raster2svg.config.models import (
    ConversionConfig,
    OutputConfig,
    PostprocessConfig,
    PreprocessConfig,
)
from raster2svg.core.errors import ConfigError, Raster2SvgError
from raster2svg.core.models import STATUS_DRY_RUN
from raster2svg.output.reports import write_report
from raster2svg.services.converter import Converter

console = Console()
err_console = Console(stderr=True)


def _fail(exc: Raster2SvgError) -> NoReturn:
    err_console.print(f"[bold red]ERROR:[/bold red] {exc.message}")
    if exc.hint:
        err_console.print(f"[yellow]{exc.hint}[/yellow]")
    raise typer.Exit(exc.exit_code)


def _print_resolved_config(
    config: ConversionConfig,
    output: OutputConfig | None = None,
    preprocess: PreprocessConfig | None = None,
    postprocess: PostprocessConfig | None = None,
) -> None:
    data = config.model_dump(mode="json")
    table = Table(title="Resolved configuration")
    table.add_column("setting")
    table.add_column("value")
    for key, value in data.items():
        if value is not None:
            table.add_row(key, str(value))
    if all(value is None for value in data.values()):
        table.add_row("(none)", "all engine defaults")
    console.print(table)

    if preprocess is not None:
        pre_table = Table(title="Resolved preprocessing")
        pre_table.add_column("setting")
        pre_table.add_column("value")
        for key, value in preprocess.model_dump().items():
            pre_table.add_row(key, str(value))
        console.print(pre_table)

    if postprocess is not None:
        post_table = Table(title="Resolved post-processing")
        post_table.add_column("setting")
        post_table.add_column("value")
        for key, value in postprocess.model_dump().items():
            post_table.add_row(key, str(value))
        console.print(post_table)

    if output is not None:
        out_table = Table(title="Resolved output settings")
        out_table.add_column("setting")
        out_table.add_column("value")
        for key, value in output.model_dump().items():
            out_table.add_row(key, str(value))
        console.print(out_table)


def convert_command(
    input: Annotated[
        Path | None,
        typer.Argument(help="Input image (.jpg, .jpeg, .png, ...)."),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Argument(help="Output .svg path (default: input file stem with .svg)."),
    ] = None,
    input_flag: Annotated[
        Path | None,
        typer.Option("--input", help="Input image (alternative to the positional)."),
    ] = None,
    output_flag: Annotated[
        Path | None,
        typer.Option("--output", help="Output .svg path (alternative to the positional)."),
    ] = None,
    preset: PresetOption = None,
    config_path: ConfigPathOption = None,
    clustering: ClusteringOption = None,
    hierarchical: HierarchicalOption = None,
    mode: ModeOption = None,
    filter_speckle: FilterSpeckleOption = None,
    color_precision: ColorPrecisionOption = None,
    layer_difference: LayerDifferenceOption = None,
    corner_threshold: CornerThresholdOption = None,
    length_threshold: LengthThresholdOption = None,
    max_iterations: MaxIterationsOption = None,
    splice_threshold: SpliceThresholdOption = None,
    path_precision: PathPrecisionOption = None,
    simplify: SimplifyOption = None,
    palette: PaletteOption = None,
    palette_file: PaletteFileOption = None,
    max_colors: MaxColorsOption = None,
    optimize: OptimizeOption = None,
    binary_threshold: BinaryThresholdOption = None,
    adaptive: AdaptiveOption = None,
    adaptive_window: AdaptiveWindowOption = None,
    adaptive_t: AdaptiveTOption = None,
    watershed_detail: WatershedDetailOption = None,
    auto_orient: AutoOrientOption = None,
    resize: ResizeOption = None,
    max_width: MaxWidthOption = None,
    max_height: MaxHeightOption = None,
    scale: ScaleOption = None,
    grayscale: GrayscaleOption = None,
    denoise: DenoiseOption = None,
    blur: BlurOption = None,
    posterize: PosterizeOption = None,
    autocontrast: AutocontrastOption = None,
    contrast: ContrastOption = None,
    brightness: BrightnessOption = None,
    sharpen: SharpenOption = None,
    pre_max_colors: PreMaxColorsOption = None,
    invert: InvertOption = None,
    overwrite: OverwriteOption = None,
    no_mkdir: NoMkdirOption = None,
    validate_svg: ValidateSvgOption = None,
    dry_run: DryRunOption = False,
    show_config: Annotated[
        bool,
        typer.Option("--show-config", help="Print the resolved configuration and exit."),
    ] = False,
    report: ReportPathOption = None,
) -> None:
    """Convert one raster image to SVG."""
    input_path = input_flag or input
    output_path = output_flag or output
    if input_path is not None and str(input_path) == "help" and output_path is None:
        show_help_for("convert")
    if input_path is None:
        _fail(
            ConfigError(
                "Missing input image.",
                hint="Usage: raster2svg convert INPUT [OUTPUT] (or --input/--output).",
            )
        )

    cli_values = build_cli_values(
        clustering=clustering,
        hierarchical=hierarchical,
        mode=mode,
        filter_speckle=filter_speckle,
        color_precision=color_precision,
        layer_difference=layer_difference,
        corner_threshold=corner_threshold,
        length_threshold=length_threshold,
        max_iterations=max_iterations,
        splice_threshold=splice_threshold,
        path_precision=path_precision,
        simplify=simplify,
        palette=palette,
        palette_file=palette_file,
        max_colors=max_colors,
        optimize=optimize,
        binary_threshold=binary_threshold,
        adaptive=adaptive,
        adaptive_window=adaptive_window,
        adaptive_t=adaptive_t,
        watershed_detail=watershed_detail,
    )

    preprocess_kwargs = {
        "auto_orient": auto_orient,
        "resize": resize,
        "max_width": max_width,
        "max_height": max_height,
        "scale": scale,
        "grayscale": grayscale,
        "denoise": denoise,
        "blur": blur,
        "posterize": posterize,
        "autocontrast": autocontrast,
        "contrast": contrast,
        "brightness": brightness,
        "sharpen": sharpen,
        "pre_max_colors": pre_max_colors,
    }

    postprocess_kwargs = {"invert": invert}

    try:
        config, output_cfg, preprocess_cfg, postprocess_cfg = resolve_cli_options(
            preset=preset,
            config_path=config_path,
            cli_values=cli_values,
            overwrite=overwrite,
            validate_svg=validate_svg,
            no_mkdir=no_mkdir,
            preprocess_kwargs=preprocess_kwargs,
            postprocess_kwargs=postprocess_kwargs,
        )
    except Raster2SvgError as exc:
        _fail(exc)

    if show_config:
        _print_resolved_config(config, output_cfg, preprocess_cfg, postprocess_cfg)
        raise typer.Exit(0)

    converter = Converter()
    try:
        result = converter.convert(
            input_path,
            output_path,
            config=config,
            output=output_cfg,
            preprocess=preprocess_cfg,
            postprocess=postprocess_cfg,
            dry_run=dry_run,
        )
    except Raster2SvgError as exc:
        _fail(exc)

    if report is not None:
        write_report(report, result)

    if result.status == STATUS_DRY_RUN:
        typer.echo(f"Dry run: would write {result.output_path}")
    else:
        size_kib = (result.output_bytes or 0) / 1024
        typer.echo(f"Wrote {result.output_path} ({size_kib:.1f} KiB) in {result.duration_ms} ms")
