"""The `config` command group (PRD sections 8, 10.5, 15.2).

`config show` prints the fully resolved configuration (defaults + preset +
config file). `config init` writes a commented TOML template.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console

from raster2svg.cli.convert import _fail, _print_resolved_config
from raster2svg.cli.options import resolve_output
from raster2svg.config.loader import load_config_file
from raster2svg.config.presets import available_presets, get_preset
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.core.errors import ConfigError, Raster2SvgError

console = Console()

FORMATS = ("text", "json")


config_app = typer.Typer(
    help="Inspect and generate configuration files.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@config_app.callback(invoke_without_command=True)
def config_callback(ctx: typer.Context) -> None:
    """Inspect and generate configuration files."""
    if ctx.invoked_subcommand is None:
        console.print("Usage: raster2svg config <show|init> --help")
        raise typer.Exit(2)


@config_app.command("show")
def config_show_command(
    config: Annotated[
        Path | None,
        typer.Option("--config", help="Config file to load (.toml or .json)."),
    ] = None,
    preset: Annotated[
        str | None,
        typer.Option(
            "--preset", help="Preset to apply: bw, photo, poster, or a saved custom preset."
        ),
    ] = None,
    out_format: Annotated[
        str,
        typer.Option("--format", help="Output format: text or json."),
    ] = "text",
) -> None:
    """Print the fully resolved configuration (defaults, preset, config file)."""
    if out_format not in FORMATS:
        _fail(
            ConfigError(
                f"Invalid --format: {out_format}",
                hint=f"Use one of: {', '.join(FORMATS)}.",
            )
        )

    file_cfg: dict[str, Any] | None = None
    if config is not None:
        try:
            file_cfg = load_config_file(config)
        except Raster2SvgError as exc:
            _fail(exc)

    try:
        resolved = resolve_conversion_config(
            preset=preset,
            config_file_values=(file_cfg or {}).get("conversion"),
        )
    except Raster2SvgError as exc:
        _fail(exc)

    if out_format == "json":
        payload: dict[str, object] = {"conversion": resolved.model_dump(mode="json")}
        if file_cfg is not None:
            payload["output"] = (file_cfg or {}).get("output")
        console.print(json.dumps(payload, indent=2))
        return

    output_cfg = None
    if file_cfg is not None:
        output_values = (file_cfg or {}).get("output")
        if output_values:
            output_cfg = resolve_output(None, None, None, dict(output_values))
    _print_resolved_config(resolved, output_cfg)


@config_app.command("init")
def config_init_command(
    output: Annotated[
        Path,
        typer.Option("--output", help="Destination file (default: raster2svg.toml)."),
    ] = Path("raster2svg.toml"),
    preset: Annotated[
        str | None,
        typer.Option("--preset", help="Preset whose values become the starting values."),
    ] = None,
    force: Annotated[
        bool,
        typer.Option("--force", help="Overwrite the destination file if it exists."),
    ] = False,
) -> None:
    """Write a commented default configuration file (TOML)."""
    if preset is not None and preset not in available_presets():
        _fail(
            ConfigError(
                f"Unknown preset: {preset}",
                hint=f"Available presets: {', '.join(sorted(available_presets()))}.",
            )
        )

    if output.exists() and not force:
        _fail(
            ConfigError(
                f"Refusing to overwrite {output}.",
                hint="Use --force to replace the existing file.",
            )
        )

    try:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(_render_toml(preset), encoding="utf-8")
    except OSError as exc:
        _fail(ConfigError(f"Cannot write {output}", hint=str(exc)))

    console.print(f"Wrote {output}")


# (field, example value, comment) - order matches the ConversionConfig fields.
_FIELD_DOCS: tuple[tuple[str, str, str], ...] = (
    ("clustering", '"color-cluster"', "color-cluster | bw | watershed"),
    ("hierarchical", '"stacked"', "stacked | cutout"),
    ("mode", '"spline"', "pixel | polygon | spline"),
    ("filter_speckle", "4", "1-100"),
    ("color_precision", "6", "1-8 bits per RGB channel"),
    ("layer_difference", "16", "1-255 (CLI alias: --gradient-step)"),
    ("corner_threshold", "60", "0-180 degrees"),
    ("length_threshold", "4.0", "3.5-10 (CLI alias: --segment-length)"),
    ("max_iterations", "10", "1-100"),
    ("splice_threshold", "45", "0-180 degrees"),
    ("path_precision", "2", "0-8 decimal places"),
    ("simplify", "1.5", ">0; engine-dependent"),
    ("palette", '["#1b1b1b", "#e0c088"]', "hex colors; engine-dependent"),
    ("palette_file", '"palette.txt"', "one hex color per line; engine-dependent"),
    ("max_colors", "16", "engine-dependent"),
    ("optimize", "2", "0-2; engine-dependent"),
    ("binary_threshold", "128", "0-255; engine-dependent"),
    ("adaptive", "true", 'engine-dependent; implies clustering = "bw"'),
    ("adaptive_window", "51", ">=3; engine-dependent"),
    ("adaptive_t", "15", "0-255; engine-dependent"),
    ("watershed_detail", "128", '0-255; use with clustering = "watershed"'),
)


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    return json.dumps(str(value))


def _render_toml(preset_name: str | None) -> str:
    preset_values = dict(get_preset(preset_name)) if preset_name else {}
    preset_note = f" --preset {preset_name}" if preset_name else ""
    lines: list[str] = [
        "# raster2svg configuration file",
        f"# Generated by: raster2svg config init{preset_note}",
        "#",
        "# Precedence (low to high): engine defaults < preset < this file < CLI options.",
        "# Commented lines are inactive. Omitted keys leave the engine default in place.",
        "",
        "[conversion]",
    ]

    if preset_name is not None:
        lines.append(f'preset = "{preset_name}"')
    else:
        lines.append('# preset = "photo"  # bw | photo | poster')

    for field, example, doc in _FIELD_DOCS:
        if field in preset_values:
            lines.append(f"{field} = {_toml_value(preset_values[field])}")
        else:
            lines.append(f"# {field} = {example}  # {doc}")

    lines += [
        "",
        "[output]",
        "# overwrite = false",
        "# validate_svg = true",
        "# create_directories = true",
        "",
    ]
    return "\n".join(lines)
