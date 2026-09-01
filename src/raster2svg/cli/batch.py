"""The `batch` command (PRD section 12)."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from raster2svg.cli.convert import _fail, _print_resolved_config
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
from raster2svg.core.errors import ConfigError, Raster2SvgError
from raster2svg.core.models import (
    STATUS_DRY_RUN,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    ConversionResult,
)
from raster2svg.output.reports import render_jsonl_line, write_batch_report
from raster2svg.services.batch_converter import (
    BatchConverter,
    build_entries,
    collect_inputs,
    resolve_jobs,
)

console = Console()
err_console = Console(stderr=True)

_STATUS_STYLES = {
    STATUS_SUCCESS: "green",
    STATUS_DRY_RUN: "cyan",
    STATUS_FAILED: "red",
    STATUS_SKIPPED: "yellow",
}


def _print_batch_summary(results: list[ConversionResult]) -> None:
    table = Table(title="Batch results")
    table.add_column("status")
    table.add_column("input")
    table.add_column("output")
    table.add_column("ms", justify="right")
    table.add_column("size", justify="right")
    for result in results:
        style = _STATUS_STYLES.get(result.status, "")
        table.add_row(
            f"[{style}]{result.status}[/{style}]",
            str(result.input_path),
            str(result.output_path),
            str(result.duration_ms),
            f"{(result.output_bytes or 0) // 1024} KiB" if result.output_bytes else "-",
        )
        if result.error:
            table.add_row("", f"[red]{result.error}[/red]", "", "", "")
    console.print(table)


def batch_command(
    input_dir: Annotated[
        Path,
        typer.Argument(help="Input image file, or a directory of images."),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            help="Directory for .svg output (default: the input directory).",
        ),
    ] = None,
    recursive: Annotated[
        bool,
        typer.Option(
            "--recursive/--no-recursive",
            help="Recurse into subdirectories and preserve their structure.",
        ),
    ] = False,
    include: Annotated[
        list[str] | None,
        typer.Option("--include", help="Only process files matching this glob (repeatable)."),
    ] = None,
    exclude: Annotated[
        list[str] | None,
        typer.Option("--exclude", help="Skip files matching this glob (repeatable)."),
    ] = None,
    jobs: Annotated[
        str | None,
        typer.Option("--jobs", help="Worker count, or 'auto' (default: conservative)."),
    ] = None,
    fail_fast: Annotated[
        bool,
        typer.Option("--fail-fast", help="Stop the batch at the first failed file."),
    ] = False,
    jsonl: Annotated[
        bool,
        typer.Option("--jsonl", help="Emit one JSON object per result on stdout (PRD 17.2)."),
    ] = False,
    show_config: Annotated[
        bool,
        typer.Option("--show-config", help="Print the resolved configuration and exit."),
    ] = False,
    report: ReportPathOption = None,
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
) -> None:
    """Convert a file or directory of raster images to SVG (PRD 12)."""
    if str(input_dir) == "help" and output_dir is None:
        show_help_for("batch")

    include_patterns = tuple(include or ())
    exclude_patterns = tuple(exclude or ())

    try:
        paths = collect_inputs(
            input_dir, recursive=recursive, include=include_patterns, exclude=exclude_patterns
        )
    except Raster2SvgError as exc:
        _fail(exc)

    if not paths:
        _fail(
            ConfigError(
                f"No supported images found in {input_dir}.",
                hint="Supported extensions: jpg, jpeg, png. Use --include to widen the filter.",
            )
        )

    target_dir = output_dir or (input_dir if input_dir.is_dir() else input_dir.parent)

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
        worker_count = resolve_jobs(jobs, len(paths))
        entries = build_entries(input_dir, paths, target_dir)
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

    stream: list[ConversionResult] = []

    def on_result(result: ConversionResult) -> None:
        stream.append(result)
        if jsonl:
            typer.echo(render_jsonl_line(result))
        if progress_task is not None:
            progress.advance(progress_task)

    use_progress = not jsonl and console.is_terminal
    if use_progress:
        with Progress("Converting {task.description}", transient=True) as progress:
            progress_task = progress.add_task("images", total=len(entries))
            results = BatchConverter().convert_many(
                entries,
                config=config,
                output=output_cfg,
                preprocess=preprocess_cfg,
                postprocess=postprocess_cfg,
                jobs=worker_count,
                fail_fast=fail_fast,
                dry_run=dry_run,
                on_result=on_result,
            )
    else:
        progress_task = None
        results = BatchConverter().convert_many(
            entries,
            config=config,
            output=output_cfg,
            preprocess=preprocess_cfg,
            postprocess=postprocess_cfg,
            jobs=worker_count,
            fail_fast=fail_fast,
            dry_run=dry_run,
            on_result=on_result,
        )

    if jsonl:
        err_console.print(
            f"batch: {len(results)} file(s), "
            f"{sum(1 for r in results if r.status == STATUS_SUCCESS)} ok, "
            f"{sum(1 for r in results if r.status == STATUS_FAILED)} failed"
        )
    else:
        _print_batch_summary(results)

    if report is not None:
        try:
            write_batch_report(report, results, input_source=str(input_dir))
        except OSError as exc:
            _fail(ConfigError(f"Could not write report file: {exc}"))

    if any(r.status in (STATUS_FAILED, STATUS_SKIPPED) for r in results):
        raise typer.Exit(1)
