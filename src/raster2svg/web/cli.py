"""The `web` command: serve the live web interface (raster2svg_web_prd.md).

`raster2svg web` starts a local HTTP server that hosts a single-page app for
real-time raster -> SVG conversion: upload once, tweak options, preview the
rendered SVG live, and download it. No new runtime dependencies are added; the
server is stdlib `http.server`.
"""

from __future__ import annotations

import webbrowser
from typing import Annotated, NoReturn

import typer
from rich.console import Console

from raster2svg.core.errors import ConfigError, Raster2SvgError
from raster2svg.web.server import WebServer

err_console = Console(stderr=True)

#: Loopback bind targets that should be displayed as `localhost` in the URL.
_LOOPBACK = {"127.0.0.1", "0.0.0.0", "::", "localhost"}


def _fail(exc: Raster2SvgError) -> NoReturn:
    err_console.print(f"[bold red]ERROR:[/bold red] {exc.message}")
    if exc.hint:
        err_console.print(f"[yellow]{exc.hint}[/yellow]")
    raise typer.Exit(exc.exit_code)


def web_command(
    host: Annotated[
        str,
        typer.Option(
            "--host",
            help="Interface to bind (default: 127.0.0.1, loopback). Use 0.0.0.0 for other hosts.",
        ),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", help="Port to listen on (default: 9921)."),
    ] = 9921,
    open_browser: Annotated[
        bool,
        typer.Option("--open", help="Open the interface in your default browser on startup."),
    ] = False,
) -> None:
    """Serve the live web interface for real-time conversion and preview."""
    server = WebServer(host=host, port=port)
    try:
        server.bind()
    except OSError as exc:
        _fail(
            ConfigError(
                f"Could not start the web server on {host}:{port}.",
                hint=str(exc) or "That port may already be in use; try a different --port.",
            )
        )

    display_host = "localhost" if host in _LOOPBACK else host
    url = f"http://{display_host}:{server.bound_port}/"
    typer.echo(f"raster2svg web interface: {url}")
    typer.echo("Upload an image, tweak the options, and download the SVG. Press Ctrl+C to stop.")

    if open_browser:
        webbrowser.open(url)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.shutdown()
        typer.echo("Stopped.")
