"""The `preset` command group (PRD section 16).

Lists and shows the built-in VTracer presets. Custom presets (PRD 16.4) are a
later milestone.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from raster2svg.cli.convert import _fail
from raster2svg.config.presets import PRESET_NOTE, PRESETS, UnknownPresetError, get_preset
from raster2svg.core.errors import ConfigError

console = Console()


preset_app = typer.Typer(
    help="List and show presets.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@preset_app.callback(invoke_without_command=True)
def preset_callback(ctx: typer.Context) -> None:
    """List and show presets."""
    if ctx.invoked_subcommand is None:
        console.print("Usage: raster2svg preset <list|show> --help")
        raise typer.Exit(2)


@preset_app.command("list")
def preset_list_command() -> None:
    """List the built-in presets."""
    table = Table(title="Built-in presets")
    table.add_column("preset", style="bold")
    table.add_column("values")
    for name in sorted(PRESETS):
        values = PRESETS[name]
        summary = ", ".join(f"{key}={value}" for key, value in values.items())
        table.add_row(name, summary)
    console.print(table)
    console.print(PRESET_NOTE)


@preset_app.command("show")
def preset_show_command(
    name: Annotated[str, typer.Argument(help="Preset name: bw, photo, poster.")],
) -> None:
    """Show all values of one preset."""
    try:
        values = get_preset(name)
    except UnknownPresetError as exc:
        _fail(
            ConfigError(
                f"Unknown preset: {exc.name}",
                hint=f"Available presets: {', '.join(exc.available)}.",
            )
        )

    table = Table(title=f"Preset: {name}")
    table.add_column("setting", style="bold")
    table.add_column("value")
    for key, value in values.items():
        table.add_row(key, str(value))
    console.print(table)
    console.print(PRESET_NOTE)
