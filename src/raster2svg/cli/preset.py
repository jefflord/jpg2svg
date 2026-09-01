"""The `preset` command group (PRD section 16).

Built-in presets are application-level bundles of canonical values with two
sections (``conversion`` and ``preprocess``) plus display metadata. Custom
presets (PRD 16.4) are user-saved TOML files that may derive from a base
preset; they are stored in the platform application directory.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table

from raster2svg.cli.convert import _fail
from raster2svg.cli.help import make_group_help_command
from raster2svg.config.loader import load_config_file
from raster2svg.config.models import (
    ConversionConfig,
    OutputConfig,
    PostprocessConfig,
    PreprocessConfig,
)
from raster2svg.config.presets import (
    PRESET_NOTE,
    PRESETS,
    UnknownPresetError,
    available_presets,
    get_preset,
    preset_source,
    resolve_preset,
    save_custom_preset,
)
from raster2svg.core.errors import ConfigError, Raster2SvgError
from raster2svg.services.converter import Converter

console = Console()

preset_app = typer.Typer(
    help="List, show, save, and compare presets.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

preset_app.command("help")(make_group_help_command("preset"))


@preset_app.callback(invoke_without_command=True)
def preset_callback(ctx: typer.Context) -> None:
    """List, show, save, and compare presets."""
    if ctx.invoked_subcommand is None:
        console.print("Usage: raster2svg preset <list|show|save|compare> --help")
        raise typer.Exit(2)


@preset_app.command("list")
def preset_list_command() -> None:
    """List all presets with their description and recommended inputs."""
    table = Table(title="Presets")
    table.add_column("preset", style="bold")
    table.add_column("source")
    table.add_column("description")
    table.add_column("best for")
    for name in available_presets():
        source = preset_source(name)
        preset = get_preset(name)
        table.add_row(
            name,
            source,
            preset.description or "",
            ", ".join(preset.recommended_for) or "",
        )
    console.print(table)
    console.print(PRESET_NOTE)


@preset_app.command("show")
def preset_show_command(
    name: Annotated[str, typer.Argument(help="Preset name, e.g. bw, clip-art, my-logo.")],
) -> None:
    """Show one preset: metadata plus its resolved conversion/preprocess/postprocess values."""
    try:
        preset = resolve_preset(name)
        source = preset_source(name)
    except UnknownPresetError as exc:
        _fail(
            ConfigError(
                f"Unknown preset: {exc.name}",
                hint=f"Available presets: {', '.join(exc.available)}.",
            )
        )
    except ConfigError as exc:
        _fail(exc)

    console.print(f"[bold]Preset:[/bold] {name}  [dim]({source})[/dim]")
    if preset.description:
        console.print(f"  description: {preset.description}")
    if preset.recommended_for:
        console.print(f"  best for:    {', '.join(preset.recommended_for)}")
    if preset.notes:
        console.print(f"  notes:       {preset.notes}")

    _print_section("conversion", preset.conversion)
    _print_section("preprocess", preset.preprocess)
    _print_section("postprocess", preset.postprocess)
    console.print(PRESET_NOTE)


def _print_section(title: str, values: dict[str, Any]) -> None:
    if not values:
        return
    table = Table(title=f"Preset section: {title}")
    table.add_column("setting", style="bold")
    table.add_column("value")
    for key, value in values.items():
        table.add_row(key, str(value))
    console.print(table)


@preset_app.command("save")
def preset_save_command(
    name: Annotated[str, typer.Argument(help="Name for the new custom preset, e.g. my-logo.")],
    from_config: Annotated[
        Path,
        typer.Option(
            "--from-config",
            help="Existing TOML/JSON config file to build the preset from "
            "(its [conversion], [preprocess], and [postprocess] sections).",
        ),
    ],
    base: Annotated[
        str | None,
        typer.Option(
            "--base",
            help="Preset name this preset derives from. Defaults to the config "
            "file's own preset, if any.",
        ),
    ] = None,
) -> None:
    """Save a custom preset from an existing config file (PRD 16.4)."""
    data = load_config_file(from_config)
    conversion = dict(data.get("conversion") or {})
    file_preset = conversion.pop("preset", None)
    conversion = {key: value for key, value in conversion.items() if value is not None}
    preprocess = {
        key: value
        for key, value in dict(data.get("preprocess") or {}).items()
        if value is not None
    }
    postprocess = {
        key: value
        for key, value in dict(data.get("postprocess") or {}).items()
        if value is not None
    }
    values: dict[str, Any] = {"conversion": conversion}
    if preprocess:
        values["preprocess"] = preprocess
    if postprocess:
        values["postprocess"] = postprocess
    resolved_base = base or file_preset
    if resolved_base is not None:
        values["base"] = resolved_base
    try:
        path = save_custom_preset(name, values)
    except ConfigError as exc:
        _fail(exc)
    console.print(f"Saved custom preset {name!r} to {path}")
    if resolved_base is not None:
        console.print(f"Derives from base preset: {resolved_base}")


@preset_app.command("compare")
def preset_compare_command(
    input_path: Annotated[
        Path,
        typer.Argument(help="Input image to convert once per preset."),
    ],
    output_dir: Annotated[
        Path | None,
        typer.Option(
            "--output-dir",
            help="Where to write the SVGs and report.json (default: preset-test).",
        ),
    ] = None,
    presets: Annotated[
        list[str] | None,
        typer.Option(
            "--presets",
            help="Preset names, comma-separated (default: all built-in presets).",
        ),
    ] = None,
) -> None:
    """Convert one image with each preset and write report.json for comparison.

    Each preset runs its full recipe (preprocessing + conversion +
    post-processing); the report records status, duration, output size, and
    path count per preset so you can tune values quickly.
    """
    if presets is None:
        names = sorted(PRESETS)
    else:
        names = [part.strip() for part in ",".join(presets).split(",") if part.strip()]

    try:
        for name in names:
            get_preset(name)
    except UnknownPresetError as exc:
        _fail(
            ConfigError(
                f"Unknown preset: {exc.name}",
                hint=f"Available presets: {', '.join(exc.available)}.",
            )
        )

    target_dir = output_dir or Path("preset-test")
    results: list[dict[str, Any]] = []
    for name in names:
        resolved = resolve_preset(name)
        out_path = target_dir / f"{input_path.stem}-{name}.svg"
        entry: dict[str, Any] = {
            "preset": name,
            "status": "failed",
            "duration_ms": None,
            "output_bytes": None,
            "svg_path": str(out_path),
            "path_count": None,
            "conversion": resolved.conversion,
            "preprocess": resolved.preprocess,
            "postprocess": resolved.postprocess,
        }
        try:
            result = Converter().convert(
                input_path,
                out_path,
                config=ConversionConfig(preset=name),
                output=OutputConfig(overwrite=True, validate_svg=False),
                preprocess=PreprocessConfig.from_dict(resolved.preprocess),
                postprocess=PostprocessConfig.from_dict(resolved.postprocess),
            )
            entry["status"] = result.status
            entry["duration_ms"] = result.duration_ms
            entry["output_bytes"] = result.output_bytes
            entry["path_count"] = len(re.findall(r"<path", out_path.read_text(encoding="utf-8")))
        except Raster2SvgError as exc:
            entry["error"] = exc.message
        results.append(entry)

    report = {
        "input": str(input_path),
        "generated_at": datetime.now(UTC).isoformat(),
        "results": results,
    }
    report_path = target_dir / "report.json"
    target_dir.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    table = Table(title=f"Preset comparison: {input_path.name}")
    table.add_column("preset", style="bold")
    table.add_column("status")
    table.add_column("ms", justify="right")
    table.add_column("size", justify="right")
    table.add_column("paths", justify="right")
    for entry in results:
        size = f"{entry['output_bytes'] // 1024} KiB" if entry["output_bytes"] else "-"
        style = "green" if entry["status"] == "success" else "red"
        table.add_row(
            entry["preset"],
            f"[{style}]{entry['status']}[/{style}]",
            str(entry["duration_ms"]) if entry["duration_ms"] is not None else "-",
            size,
            str(entry["path_count"]) if entry["path_count"] is not None else "-",
        )
    console.print(table)
    console.print(f"Report: [bold]{report_path}[/bold]  ·  SVGs in: {target_dir}")
