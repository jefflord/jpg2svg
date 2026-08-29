"""Typer application root (PRD section 6).

`raster2svg` supports named commands plus the shorthand
`raster2svg input.jpg [output.svg]` which is equivalent to `convert`
(PRD section 6.1).
"""

from __future__ import annotations

import sys

import typer

from raster2svg._version import __version__
from raster2svg.cli.batch import batch_command
from raster2svg.cli.config import config_app
from raster2svg.cli.convert import convert_command
from raster2svg.cli.preset import preset_app
from raster2svg.core.capabilities import detect_vtracer_capabilities

app = typer.Typer(
    name="raster2svg",
    help="Convert raster images (JPG, PNG, ...) to SVG using VTracer.",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Extend when new top-level commands are added (inspect).
KNOWN_COMMANDS = {"batch", "convert", "config", "engine", "preset", "version", "help"}


def version_command() -> None:
    """Show the tool and tracing-engine versions."""
    caps = detect_vtracer_capabilities()
    typer.echo(f"raster2svg {__version__}")
    typer.echo(f"engine: {caps.name} {caps.version}")


def _list_caps_command() -> None:
    caps = detect_vtracer_capabilities()
    typer.echo(f"engine: {caps.name} {caps.version}")
    typer.echo(f"supported parameters: {', '.join(sorted(caps.supported_params))}")


engine_app = typer.Typer(
    help="Inspect the installed tracing engine.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@engine_app.command("capabilities")
def engine_capabilities_command() -> None:
    """Show what the installed tracing engine supports."""
    _list_caps_command()


app.command("version")(version_command)
app.command("batch")(batch_command)
app.command("convert")(convert_command)
app.add_typer(engine_app, name="engine")
app.add_typer(config_app, name="config")
app.add_typer(preset_app, name="preset")


def main() -> None:
    """Entry point for the `raster2svg` executable and `python -m raster2svg`."""
    argv = sys.argv[1:]
    if argv and argv[0] not in KNOWN_COMMANDS and not argv[0].startswith("-"):
        argv = ["convert", *argv]
    sys.argv = ["raster2svg", *argv]
    app()
