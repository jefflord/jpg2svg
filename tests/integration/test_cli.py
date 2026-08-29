"""CLI tests: command surface, shorthand, and error exit codes (PRD section 6)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

from raster2svg.cli.app import app, main

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def test_convert_command(tmp_path: Path) -> None:
    out = tmp_path / "cli.svg"
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(out),
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_named_input_output_flags(tmp_path: Path) -> None:
    out = tmp_path / "named.svg"
    result = runner.invoke(
        app,
        [
            "convert",
            "--input",
            str(FIXTURES / "fixture_photo.jpg"),
            "--output",
            str(out),
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_missing_input_is_a_clean_error() -> None:
    result = runner.invoke(app, ["convert"])
    assert result.exit_code == 2
    assert "Missing input" in result.output


def test_shorthand_invocation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "short.svg"
    monkeypatch.setattr(
        sys,
        "argv",
        ["raster2svg", str(FIXTURES / "fixture_photo.jpg"), str(out)],
    )
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert out.exists()


def test_help_documents_options() -> None:
    result = runner.invoke(app, ["convert", "--help"])
    assert result.exit_code == 0
    for flag in (
        "--preset",
        "--clustering",
        "--hierarchical",
        "--mode",
        "--filter-speckle",
        "--color-precision",
        "--layer-difference",
        "--length-threshold",
        "--binary-threshold",
        "--simplify",
        "--overwrite",
        "--dry-run",
        "--show-config",
    ):
        assert flag in result.output


def test_cli_aliases_work(tmp_path: Path) -> None:
    """Secondary option names (--gradient-step, --segment-length) are accepted."""
    out = tmp_path / "alias.svg"
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(out),
            "--gradient-step",
            "16",
            "--segment-length",
            "5",
            "--overwrite",
        ],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()


def test_version_command() -> None:
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "raster2svg" in result.output
    assert "vtracer" in result.output


def test_engine_capabilities_command() -> None:
    result = runner.invoke(app, ["engine", "capabilities"])
    assert result.exit_code == 0
    assert "vtracer" in result.output
    assert "colormode" in result.output


def test_show_config_prints_resolved_values() -> None:
    result = runner.invoke(
        app, ["convert", str(FIXTURES / "fixture_photo.jpg"), "--preset", "bw", "--show-config"]
    )
    assert result.exit_code == 0
    assert "clustering" in result.output
    assert "bw" in result.output


def test_invalid_option_value_exits_2() -> None:
    result = runner.invoke(
        app,
        ["convert", str(FIXTURES / "fixture_photo.jpg"), "--color-precision", "99"],
    )
    assert result.exit_code == 2
    assert "color_precision" in result.output or "Invalid" in result.output


def test_missing_input_exits_3(tmp_path: Path) -> None:
    result = runner.invoke(app, ["convert", str(tmp_path / "nope.jpg")])
    assert result.exit_code == 3
    assert "ERROR" in result.output


def test_unsupported_engine_feature_exits_2(tmp_path: Path) -> None:
    out = tmp_path / "out.svg"
    result = runner.invoke(
        app,
        ["convert", str(FIXTURES / "fixture_photo.jpg"), str(out), "--simplify", "1.5"],
    )
    assert result.exit_code == 2
    assert "does not support" in result.output
    assert not out.exists()


def test_report_file_is_written(tmp_path: Path) -> None:
    out = tmp_path / "out.svg"
    report = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(out),
            "--overwrite",
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == 0, result.output
    payload = report.read_text(encoding="utf-8")
    assert '"status": "success"' in payload
    assert "vtracer" in payload


def test_preset_list_shows_builtins() -> None:
    result = runner.invoke(app, ["preset", "list"])
    assert result.exit_code == 0, result.output
    for name in ("bw", "photo", "poster"):
        assert name in result.output


def test_preset_show_unknown_exits_2() -> None:
    result = runner.invoke(app, ["preset", "show", "does-not-exist"])
    assert result.exit_code == 2
    assert "Unknown preset" in result.output


def test_preset_save_list_show_and_use(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(tmp_path / "data"))
    source_cfg = tmp_path / "logo.toml"
    source_cfg.write_text(
        '[conversion]\npreset = "photo"\nmode = "polygon"\nfilter_speckle = 5\n',
        encoding="utf-8",
    )

    saved = runner.invoke(app, ["preset", "save", "my-logo", "--from-config", str(source_cfg)])
    assert saved.exit_code == 0, saved.output
    assert "my-logo" in saved.output

    listed = runner.invoke(app, ["preset", "list"])
    assert listed.exit_code == 0
    assert "my-logo" in listed.output
    assert "custom" in listed.output

    shown = runner.invoke(app, ["preset", "show", "my-logo"])
    assert shown.exit_code == 0, shown.output
    assert "filter_speckle" in shown.output
    # base chain applied: photo preset provides clustering
    assert "color-cluster" in shown.output

    out = tmp_path / "custom.svg"
    used = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(out),
            "--preset",
            "my-logo",
            "--overwrite",
        ],
    )
    assert used.exit_code == 0, used.output
    assert out.exists()


def test_preset_save_rejects_builtin_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(tmp_path / "data"))
    source_cfg = tmp_path / "c.toml"
    source_cfg.write_text('mode = "pixel"\n', encoding="utf-8")
    result = runner.invoke(app, ["preset", "save", "photo", "--from-config", str(source_cfg)])
    assert result.exit_code == 2
    assert "shadow" in result.output
