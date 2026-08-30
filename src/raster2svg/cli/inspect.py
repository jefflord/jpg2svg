"""The `inspect` command (PRD section 15.4)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console

from raster2svg.cli.help import show_help_for
from raster2svg.core.errors import ConfigError, Raster2SvgError
from raster2svg.services.inspector import ImageInspection, inspect_image

err_console = Console(stderr=True)


def _fail(exc: Raster2SvgError) -> NoReturn:
    err_console.print(f"[bold red]ERROR:[/bold red] {exc.message}")
    if exc.hint:
        err_console.print(f"[yellow]{exc.hint}[/yellow]")
    raise typer.Exit(exc.exit_code)


def _human_bytes(size: int) -> str:
    value = float(size)
    unit = "B"
    for candidate in ("KiB", "MiB", "GiB"):
        if value < 1024:
            break
        value /= 1024
        unit = candidate
    if unit == "B":
        return f"{size} B"
    return f"{value:.1f} {unit}"


def _render_text(inspection: ImageInspection) -> str:
    orientation = (
        str(inspection.exif_orientation) if inspection.exif_orientation is not None else "none"
    )
    return "\n".join(
        [
            f"Path: {inspection.path}",
            f"Format: {inspection.format}",
            f"Mode: {inspection.mode}",
            f"Width: {inspection.width}",
            f"Height: {inspection.height}",
            f"Pixels: {inspection.pixels:,}",
            f"Has alpha: {'true' if inspection.has_alpha else 'false'}",
            f"EXIF orientation: {orientation}",
            f"Size: {inspection.size_bytes:,} bytes",
            f"Estimated memory: {_human_bytes(inspection.estimated_memory_bytes)}",
        ]
    )


def inspect_command(
    input: Annotated[
        Path | None,
        typer.Argument(help="Input image (.jpg, .jpeg, .png, ...)."),
    ] = None,
    input_flag: Annotated[
        Path | None,
        typer.Option("--input", help="Input image (alternative to the positional)."),
    ] = None,
    out_format: Annotated[
        str,
        typer.Option("--format", help="Output format: text or json."),
    ] = "text",
) -> None:
    """Inspect a raster image without converting it."""
    input_path = input_flag or input
    if input_path is not None and str(input_path) == "help":
        show_help_for("inspect")
    if input_path is None:
        _fail(ConfigError("Missing input image.", hint="Usage: raster2svg inspect INPUT."))
    if out_format not in ("text", "json"):
        _fail(
            ConfigError(
                f"Invalid --format: {out_format}",
                hint="Expected 'text' or 'json'.",
            )
        )
    try:
        inspection = inspect_image(input_path)
    except Raster2SvgError as exc:
        _fail(exc)
    if out_format == "json":
        typer.echo(json.dumps(inspection.to_dict(), indent=2, ensure_ascii=False))
        return
    typer.echo(_render_text(inspection))
