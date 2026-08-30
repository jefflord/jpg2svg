"""Typer application root (PRD section 6).

`raster2svg` supports named commands plus the shorthand
`raster2svg input.jpg [output.svg]` which is equivalent to `convert`
(PRD section 6.1). Global options (PRD section 18) are shared by all
commands.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

import typer

from raster2svg._version import __version__
from raster2svg.cli.batch import batch_command
from raster2svg.cli.config import config_app
from raster2svg.cli.convert import convert_command
from raster2svg.cli.help import make_group_help_command, show_help_for
from raster2svg.cli.inspect import inspect_command
from raster2svg.cli.preset import preset_app
from raster2svg.core.capabilities import detect_vtracer_capabilities, split_engine_dependent
from raster2svg.core.errors import Raster2SvgError
from raster2svg.utils.logging import configure_logging
from raster2svg.web.cli import web_command

app = typer.Typer(
    name="raster2svg",
    help="Convert raster images (JPG, PNG, ...) to SVG using VTracer.",
    add_completion=False,
    context_settings={"help_option_names": ["-h", "--help"]},
)

# Extend when new top-level commands are added.
KNOWN_COMMANDS = {
    "batch",
    "convert",
    "config",
    "engine",
    "inspect",
    "preset",
    "version",
    "web",
    "help",
}

# Global options that take a value (PRD section 18).
_GLOBAL_VALUE_OPTIONS = {"--log-level", "--log-file"}
_GLOBAL_FLAG_OPTIONS = {"--verbose", "--quiet"}


@app.callback()
def root_callback(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Enable debug logging (PRD 18.1)."),
    ] = False,
    quiet: Annotated[
        bool,
        typer.Option("--quiet", help="Only show warnings and errors (PRD 18.1)."),
    ] = False,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="Log level: debug, info, warning, or error (overrides --verbose/--quiet).",
        ),
    ] = None,
    log_file: Annotated[
        Path | None,
        typer.Option("--log-file", help="Also write log messages to this file (PRD 18.2)."),
    ] = None,
) -> None:
    """Global options shared by all commands (PRD section 18)."""
    try:
        configure_logging(verbose=verbose, quiet=quiet, log_level=log_level, log_file=log_file)
    except Raster2SvgError as exc:
        typer.echo(f"ERROR: {exc.message}", err=True)
        if exc.hint:
            typer.echo(exc.hint, err=True)
        raise typer.Exit(exc.exit_code) from exc


def version_command() -> None:
    """Show the tool and tracing-engine versions."""
    caps = detect_vtracer_capabilities()
    typer.echo(f"raster2svg {__version__}")
    typer.echo(f"engine: {caps.name} {caps.version}")


def _list_caps_command() -> None:
    caps = detect_vtracer_capabilities()
    available, unavailable = split_engine_dependent(caps)
    typer.echo(f"engine: {caps.name} {caps.version}")
    typer.echo(f"supported parameters: {', '.join(sorted(caps.supported_params))}")
    if unavailable:
        typer.echo()
        typer.echo("Advanced options NOT available on this engine (needs VTracer 1.0):")
        for option in unavailable:
            typer.echo(f"  {option}")
    if available:
        typer.echo()
        typer.echo("Advanced options available on this engine:")
        for option in available:
            typer.echo(f"  {option}")


engine_app = typer.Typer(
    help="Inspect the installed tracing engine.",
    context_settings={"help_option_names": ["-h", "--help"]},
)


@engine_app.command("capabilities")
def engine_capabilities_command() -> None:
    """Show what the installed tracing engine supports."""
    _list_caps_command()


def help_command(
    command: Annotated[
        str | None,
        typer.Argument(help="Command to show help for, e.g. convert."),
    ] = None,
    subcommand: Annotated[
        str | None,
        typer.Argument(help="Subcommand to show help for, e.g. show."),
    ] = None,
) -> None:
    """Show help for raster2svg or one of its commands.

    Examples: `raster2svg help`, `raster2svg help convert`, `raster2svg help config show`.
    """
    if command is None:
        show_help_for()
    if subcommand is None:
        show_help_for(command)
    show_help_for(command, subcommand)


app.command("version")(version_command)
app.command("help")(help_command)
app.command("batch")(batch_command)
app.command("convert")(convert_command)
app.command("inspect")(inspect_command)
app.command("web")(web_command)
engine_app.command("help")(make_group_help_command("engine"))
app.add_typer(engine_app, name="engine")
app.add_typer(config_app, name="config")
app.add_typer(preset_app, name="preset")


def _first_positional(argv: list[str]) -> str | None:
    """Return the first token that is not a global option or its value."""
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in _GLOBAL_VALUE_OPTIONS:
            index += 2
            continue
        if token.startswith("-"):
            index += 1
            continue
        return token
    return None


def _move_global_options(argv: list[str]) -> list[str]:
    """Move leading global options ahead of an implicit `convert` (PRD 6.1/18)."""
    globals_: list[str] = []
    rest: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if not rest and token.startswith("-"):
            if token in _GLOBAL_VALUE_OPTIONS and index + 1 < len(argv):
                globals_.extend((token, argv[index + 1]))
                index += 2
                continue
            if token in _GLOBAL_FLAG_OPTIONS:
                globals_.append(token)
                index += 1
                continue
        rest.append(token)
        index += 1
    return [*globals_, "convert", *rest]


def main() -> None:
    """Entry point for the `raster2svg` executable and `python -m raster2svg`."""
    argv = sys.argv[1:]
    first = _first_positional(argv)
    if first is not None and first not in KNOWN_COMMANDS:
        argv = _move_global_options(argv)
    sys.argv = ["raster2svg", *argv]
    app()
