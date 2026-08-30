"""Integration tests for the preprocessing CLI surface (PRD section 13)."""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from typer.testing import CliRunner

from raster2svg.cli.app import app

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def _svg_dimensions(path: Path) -> tuple[int, int]:
    root = ET.fromstring(path.read_text(encoding="utf-8"))
    width = root.get("width")
    height = root.get("height")
    assert width is not None and height is not None
    return int(width), int(height)


def test_convert_with_grayscale_and_scale(tmp_path: Path) -> None:
    target = tmp_path / "out.svg"
    report = tmp_path / "report.json"
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(target),
            "--grayscale",
            "--scale",
            "0.5",
            "--report",
            str(report),
        ],
    )
    assert result.exit_code == 0, result.output
    assert target.exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["preprocess_applied"] == ["scale", "grayscale"]
    assert payload["preprocess"]["grayscale"] is True
    assert payload["preprocess"]["scale"] == 0.5
    # 96x96 input scaled by 0.5 -> 48x48 SVG.
    assert _svg_dimensions(target) == (48, 48)


def test_auto_orient_is_on_by_default(tmp_path: Path) -> None:
    target = tmp_path / "oriented.svg"
    result = runner.invoke(app, ["convert", str(FIXTURES / "fixture_oriented.jpg"), str(target)])
    assert result.exit_code == 0, result.output
    assert _svg_dimensions(target) == (48, 96)


def test_auto_orient_can_be_disabled(tmp_path: Path) -> None:
    target = tmp_path / "raw.svg"
    result = runner.invoke(
        app,
        ["convert", str(FIXTURES / "fixture_oriented.jpg"), str(target), "--no-auto-orient"],
    )
    assert result.exit_code == 0, result.output
    assert _svg_dimensions(target) == (96, 48)


def test_resize_rejects_invalid_value() -> None:
    result = runner.invoke(
        app,
        ["convert", str(FIXTURES / "fixture_photo.jpg"), "unused.svg", "--resize", "abc"],
    )
    assert result.exit_code == 2
    combined = result.output + (result.stderr or "")
    assert "WIDTHxHEIGHT" in combined or "invalid resize size" in combined


def test_config_file_preprocess_section_is_respected(tmp_path: Path) -> None:
    target = tmp_path / "fromfile.svg"
    config = tmp_path / "cfg.toml"
    config.write_text(
        "[preprocess]\ngrayscale = true\nscale = 0.5\n",
        encoding="utf-8",
    )
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(target),
            "--config",
            str(config),
        ],
    )
    assert result.exit_code == 0, result.output
    assert _svg_dimensions(target) == (48, 48)


def test_cli_overrides_config_file_preprocess(tmp_path: Path) -> None:
    target = tmp_path / "cliwins.svg"
    config = tmp_path / "cfg.toml"
    config.write_text("[preprocess]\ngrayscale = true\nscale = 0.25\n", encoding="utf-8")
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            str(target),
            "--config",
            str(config),
            "--scale",
            "0.5",
        ],
    )
    assert result.exit_code == 0, result.output
    # grayscale from the file + 0.5 from the CLI -> 48x48 (not 24x24).
    assert _svg_dimensions(target) == (48, 48)


def test_show_config_includes_preprocessing(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_photo.jpg"),
            "unused.svg",
            "--show-config",
            "--grayscale",
            "--max-width",
            "512",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Resolved preprocessing" in result.output
    assert "grayscale" in result.output
    assert "max_width" in result.output


def test_batch_applies_preprocess_to_every_file(tmp_path: Path) -> None:
    work = tmp_path / "imgs"
    work.mkdir()
    for name in ("a.jpg", "b.jpg"):
        shutil.copyfile(FIXTURES / "fixture_photo.jpg", work / name)
    out_dir = tmp_path / "out"
    result = runner.invoke(
        app,
        [
            "batch",
            str(work),
            "--output-dir",
            str(out_dir),
            "--scale",
            "0.5",
            "--report",
            str(tmp_path / "batch.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "batch.json").read_text(encoding="utf-8"))
    assert report["totals"]["succeeded"] == 2
    for entry in report["results"]:
        assert "scale" in entry["preprocess_applied"]
        assert _svg_dimensions(Path(entry["output"])) == (48, 48)


def test_dry_run_reports_preprocess_without_writing(tmp_path: Path) -> None:
    target = tmp_path / "dry.svg"
    result = runner.invoke(
        app,
        [
            "convert",
            str(FIXTURES / "fixture_oriented.jpg"),
            str(target),
            "--dry-run",
            "--report",
            str(tmp_path / "dry.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    assert not target.exists()
    payload = json.loads((tmp_path / "dry.json").read_text(encoding="utf-8"))
    assert payload["status"] == "dry-run"
    assert payload["preprocess_applied"] == ["auto_orient"]
