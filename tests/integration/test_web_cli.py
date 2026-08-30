"""CLI tests for the `web` command (raster2svg_web_prd.md)."""

from __future__ import annotations

import pytest
from typer.testing import CliRunner

import raster2svg.web.cli as webcli
from raster2svg.cli.app import KNOWN_COMMANDS, app

runner = CliRunner()


def test_web_is_a_known_command() -> None:
    assert "web" in KNOWN_COMMANDS


def test_web_appears_in_root_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "web" in result.output


def test_web_help_lists_options() -> None:
    result = runner.invoke(app, ["web", "--help"])
    assert result.exit_code == 0, result.output
    for flag in ("--host", "--port", "--open"):
        assert flag in result.output


def test_web_reports_bind_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def _bind_failure(_server: object) -> None:
        raise OSError("[Errno 98] Address already in use")

    monkeypatch.setattr(webcli.WebServer, "bind", _bind_failure)
    result = runner.invoke(app, ["web", "--host", "127.0.0.1", "--port", "9999"])
    assert result.exit_code == 2
    assert "Could not start" in result.output
    assert "9999" in result.output
