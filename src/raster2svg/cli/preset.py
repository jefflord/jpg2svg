"""The `preset` command group (PRD section 16).

Built-in presets are application-level bundles of canonical values. Custom
presets (PRD 16.4) are user-saved TOML files that may derive from a base
preset; they are stored in the platform application directory.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from raster2svg.cli.convert import _fail
from raster2svg.cli.help import make_group_help_command
from raster2svg.config.loader import load_config_file
from raster2svg.config.presets import (
    PRESET_NOTE,
    UnknownPresetError,
    available_presets,
    preset_source,
    resolve_preset,
    save_custom_preset,
)
from raster2svg.core.errors import ConfigError

console = Console()


preset_app = typer.Typer(
    help="List, show, and save presets.",
    context_settings={"help_option_names": ["-h", "--help"]},
)

preset_app.command("help")(make_group_help_command("preset"))


@preset_app.callback(invoke_without_command=True)
def preset_callback(ctx: typer.Context) -> None:
    """List, show, and save presets."""
    if ctx.invoked_subcommand is None:
        console.print("Usage: raster2svg preset <list|show|save> --help")
        raise typer.Exit(2)


@preset_app.command("list")
def preset_list_command() -> None:
    """List the built-in and custom presets with their resolved values."""
    table = Table(title="Presets")
    table.add_column("preset", style="bold")
    table.add_column("source")
    table.add_column("values")
    for name in available_presets():
        source = preset_source(name)
        values = resolve_preset(name)
        summary = ", ".join(f"{key}={value}" for key, value in values.items())
        table.add_row(name, source, summary)
    console.print(table)
    console.print(PRESET_NOTE)


@preset_app.command("show")
def preset_show_command(
    name: Annotated[str, typer.Argument(help="Preset name, e.g. bw, photo, poster, my-logo.")],
) -> None:
    """Show all resolved values of one preset (base chain applied)."""
    try:
        values = resolve_preset(name)
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

    table = Table(title=f"Preset: {name} ({source})")
    table.add_column("setting", style="bold")
    table.add_column("value")
    for key, value in values.items():
        table.add_row(key, str(value))
    console.print(table)
    console.print(PRESET_NOTE)


@preset_app.command("save")
def preset_save_command(
    name: Annotated[str, typer.Argument(help="Name for the new custom preset, e.g. my-logo.")],
    from_config: Annotated[
        Path,
        typer.Option(
            "--from-config",
            help="Existing TOML/JSON config file to build the preset from.",
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
    values = dict(data["conversion"])
    file_preset = values.pop("preset", None)
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
