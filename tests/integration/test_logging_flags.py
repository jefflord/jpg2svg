"""Integration tests for the global logging options (PRD section 18)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from raster2svg.cli.app import app, main

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def test_verbose_emits_debug_trace(tmp_path: Path) -> None:
    out = tmp_path / "out.svg"
    result = runner.invoke(
        app,
        ["--verbose", "convert", str(FIXTURES / "fixture_photo.jpg"), str(out)],
    )
    assert result.exit_code == 0, result.output
    assert "DEBUG" in result.output
    assert out.exists()


def test_quiet_suppresses_info_and_debug(tmp_path: Path) -> None:
    out = tmp_path / "out.svg"
    result = runner.invoke(
        app,
        ["--quiet", "convert", str(FIXTURES / "fixture_photo.jpg"), str(out)],
    )
    assert result.exit_code == 0, result.output
    assert "DEBUG" not in result.output
    assert "INFO" not in result.output
    assert out.exists()


def test_verbose_and_quiet_conflict_exits_2() -> None:
    result = runner.invoke(app, ["--verbose", "--quiet", "version"])
    assert result.exit_code == 2
    assert "mutually exclusive" in result.output


def test_invalid_log_level_exits_2() -> None:
    result = runner.invoke(app, ["--log-level", "chatty", "version"])
    assert result.exit_code == 2
    assert "Invalid --log-level" in result.output


def test_log_level_wins_over_verbose() -> None:
    result = runner.invoke(app, ["--verbose", "--log-level", "error", "version"])
    assert result.exit_code == 0, result.output
    assert "DEBUG" not in result.output


def test_log_file_captures_messages(tmp_path: Path) -> None:
    log_path = tmp_path / "sub" / "conversion.log"
    out = tmp_path / "out.svg"
    result = runner.invoke(
        app,
        [
            "--verbose",
            "--log-file",
            str(log_path),
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(out),
        ],
    )
    assert result.exit_code == 0, result.output
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "DEBUG" in content
    assert "raster2svg" in content


def test_shorthand_with_global_flags(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "short.svg"
    monkeypatch.setattr(
        sys,
        "argv",
        ["raster2svg", "--verbose", str(FIXTURES / "fixture_photo.jpg"), str(out)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert out.exists()
