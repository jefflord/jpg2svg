"""Integration tests for the `help` subcommand (PRD section 15)."""

from __future__ import annotations

import sys

import pytest
from typer.testing import CliRunner

from raster2svg.cli.app import app, main

runner = CliRunner()


def test_help_root() -> None:
    result = runner.invoke(app, ["help"])
    assert result.exit_code == 0, result.output
    assert "Usage" in result.output
    assert "convert" in result.output
    assert "batch" in result.output
    assert "inspect" in result.output


def test_help_convert() -> None:
    result = runner.invoke(app, ["help", "convert"])
    assert result.exit_code == 0, result.output
    assert "Convert one raster image to SVG" in result.output
    assert "--preset" in result.output
    assert "--invert" in result.output


def test_help_config_show() -> None:
    result = runner.invoke(app, ["help", "config", "show"])
    assert result.exit_code == 0, result.output
    assert "Print the fully resolved configuration" in result.output


def test_help_version() -> None:
    result = runner.invoke(app, ["help", "version"])
    assert result.exit_code == 0, result.output
    assert "Show the tool and tracing-engine versions" in result.output


def test_help_unknown_command() -> None:
    result = runner.invoke(app, ["help", "bogus"])
    assert result.exit_code == 2


def test_convert_trailing_help() -> None:
    result = runner.invoke(app, ["convert", "help"])
    assert result.exit_code == 0, result.output
    assert "Convert one raster image to SVG" in result.output


def test_batch_trailing_help() -> None:
    result = runner.invoke(app, ["batch", "help"])
    assert result.exit_code == 0, result.output
    assert "Convert a file or directory" in result.output


def test_inspect_trailing_help() -> None:
    result = runner.invoke(app, ["inspect", "help"])
    assert result.exit_code == 0, result.output
    assert "Inspect a raster image without converting it" in result.output


def test_config_help_group() -> None:
    result = runner.invoke(app, ["config", "help"])
    assert result.exit_code == 0, result.output
    assert "show" in result.output


def test_config_help_show() -> None:
    result = runner.invoke(app, ["config", "help", "show"])
    assert result.exit_code == 0, result.output
    assert "Print the fully resolved configuration" in result.output


def test_preset_help_list() -> None:
    result = runner.invoke(app, ["preset", "help", "list"])
    assert result.exit_code == 0, result.output
    assert "List all presets with their description and recommended inputs" in result.output


def test_engine_help() -> None:
    result = runner.invoke(app, ["engine", "help"])
    assert result.exit_code == 0, result.output
    assert "capabilities" in result.output


def test_convert_help_file_not_hijacked() -> None:
    result = runner.invoke(app, ["convert", "help.jpg"])
    assert result.exit_code == 3


def test_shorthand_help_file_not_hijacked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["raster2svg", "help.jpg"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 3
