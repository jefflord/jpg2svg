"""Integration tests for the `inspect` command (PRD section 15.4)."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from raster2svg.cli.app import app

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def test_inspect_text_output() -> None:
    result = runner.invoke(app, ["inspect", str(FIXTURES / "fixture_photo.jpg")])
    assert result.exit_code == 0, result.output
    assert "Path:" in result.output
    assert "Format: JPEG" in result.output
    assert "Width: 96" in result.output
    assert "Height: 96" in result.output
    assert "Pixels: 9,216" in result.output
    assert "Has alpha: false" in result.output
    assert "EXIF orientation: none" in result.output
    assert "Estimated memory:" in result.output


def test_inspect_json_output() -> None:
    result = runner.invoke(
        app,
        ["inspect", "--format", "json", str(FIXTURES / "fixture_photo.jpg")],
    )
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["format"] == "JPEG"
    assert data["width"] == 96
    assert data["height"] == 96
    assert data["pixels"] == 9216
    assert data["has_alpha"] is False
    assert data["estimated_memory_bytes"] == 96 * 96 * 3


def test_inspect_named_input_flag() -> None:
    result = runner.invoke(app, ["inspect", "--input", str(FIXTURES / "fixture_logo.png")])
    assert result.exit_code == 0, result.output
    assert "Has alpha: true" in result.output


def test_inspect_exif_orientation_shown() -> None:
    result = runner.invoke(app, ["inspect", str(FIXTURES / "fixture_oriented.jpg")])
    assert result.exit_code == 0, result.output
    assert "EXIF orientation: 6" in result.output


def test_inspect_missing_input_exits_2() -> None:
    result = runner.invoke(app, ["inspect"])
    assert result.exit_code == 2
    assert "Missing input" in result.output


def test_inspect_missing_file_exits_3() -> None:
    result = runner.invoke(app, ["inspect", "does-not-exist.jpg"])
    assert result.exit_code == 3
    assert "does not exist" in result.output


def test_inspect_corrupt_file_exits_3() -> None:
    result = runner.invoke(app, ["inspect", str(FIXTURES / "fixture_corrupt.jpg")])
    assert result.exit_code == 3
    assert "Cannot decode" in result.output


def test_inspect_invalid_format_exits_2() -> None:
    result = runner.invoke(
        app,
        ["inspect", "--format", "xml", str(FIXTURES / "fixture_photo.jpg")],
    )
    assert result.exit_code == 2
    assert "Invalid --format" in result.output
