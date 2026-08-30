"""Shared `help` subcommand plumbing.

`raster2svg help [COMMAND [SUBCOMMAND]]` (and the trailing forms such as
`raster2svg convert help`) render the real `--help` output by re-entering
the CLI in-process, so the text is exactly what the `--help` flag prints.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from typing import Annotated, NoReturn

import typer


def show_help_for(*names: str) -> NoReturn:
    """Print the real `--help` output for a command path, e.g. ("config", "show")."""
    # Deferred import: cli.app imports the command modules that use this helper.
    from raster2svg.cli.app import app

    old_argv = sys.argv
    sys.argv = ["raster2svg", *names, "--help"]
    try:
        app()
    finally:
        sys.argv = old_argv
    raise typer.Exit(0)


def make_group_help_command(group: str) -> Callable[..., None]:
    """Build a `help` subcommand for a Typer group, e.g. `config help show`."""

    def help_command(
        subcommand: Annotated[
            str | None,
            typer.Argument(help="Subcommand to show help for, e.g. show."),
        ] = None,
    ) -> None:
        """Show help for this command group or one of its subcommands."""
        if subcommand is None:
            show_help_for(group)
        show_help_for(group, subcommand)

    help_command.__name__ = f"{group}_help_command"
    return help_command
