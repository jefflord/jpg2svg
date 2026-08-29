"""Integration tests for the `batch` command (PRD sections 12 and 30.8)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from typer.testing import CliRunner

from raster2svg.cli.app import app

FIXTURES = Path(__file__).parent.parent / "fixtures"
runner = CliRunner()


def _seed(images: dict[str, Path], root: Path) -> None:
    for name, source in images.items():
        destination = root / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)


def test_batch_converts_directory(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "a.jpg": FIXTURES / "fixture_photo.jpg",
            "b.png": FIXTURES / "fixture_logo.png",
            "notes.txt": FIXTURES / "fixture_corrupt.jpg",
        },
        src,
    )
    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out)])
    assert result.exit_code == 0, result.output
    assert (out / "a.svg").exists()
    assert (out / "b.svg").exists()
    assert not (out / "notes.svg").exists()
    # The batch summary table lists each converted file with its status.
    assert result.output.count("success") >= 2


def test_batch_include_and_exclude(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "a.jpg": FIXTURES / "fixture_photo.jpg",
            "b.jpg": FIXTURES / "fixture_photo.jpg",
            "c.png": FIXTURES / "fixture_logo.png",
        },
        src,
    )
    result = runner.invoke(
        app,
        ["batch", str(src), "--output-dir", str(out), "--include", "*.jpg", "--exclude", "b.*"],
    )
    assert result.exit_code == 0, result.output
    assert (out / "a.svg").exists()
    assert not (out / "b.svg").exists()
    assert not (out / "c.svg").exists()


def test_batch_recursive_preserves_structure(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "top.jpg": FIXTURES / "fixture_photo.jpg",
            "products/a.jpg": FIXTURES / "fixture_photo.jpg",
            "icons/b.png": FIXTURES / "fixture_logo.png",
        },
        src,
    )
    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out), "--recursive"])
    assert result.exit_code == 0, result.output
    assert (out / "top.svg").exists()
    assert (out / "products" / "a.svg").exists()
    assert (out / "icons" / "b.svg").exists()


def test_batch_continues_after_failure(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "good.jpg": FIXTURES / "fixture_photo.jpg",
            "bad.jpg": FIXTURES / "fixture_corrupt.jpg",
        },
        src,
    )
    report = tmp_path / "batch-report.json"
    result = runner.invoke(
        app,
        ["batch", str(src), "--output-dir", str(out), "--report", str(report)],
    )
    assert result.exit_code == 1, result.output
    assert (out / "good.svg").exists()
    assert not (out / "bad.svg").exists()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["totals"]["succeeded"] == 1
    assert payload["totals"]["failed"] == 1
    failed_entry = next(entry for entry in payload["results"] if entry["status"] == "failed")
    assert "bad" in failed_entry["input"]
    assert failed_entry["error"]


def test_batch_fail_fast_stops_processing(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "a-bad.jpg": FIXTURES / "fixture_corrupt.jpg",
            "b-good.jpg": FIXTURES / "fixture_photo.jpg",
        },
        src,
    )
    # --jobs 1 forces serial execution so fail-fast is deterministic:
    # the second file is never started.
    result = runner.invoke(
        app, ["batch", str(src), "--output-dir", str(out), "--fail-fast", "--jobs", "1"]
    )
    assert result.exit_code == 1, result.output
    assert not (out / "b-good.svg").exists()
    assert "fail-fast" in result.output


def test_batch_overwrite_protection(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed({"a.jpg": FIXTURES / "fixture_photo.jpg"}, src)
    (out / "a.svg").parent.mkdir(parents=True, exist_ok=True)
    (out / "a.svg").write_text("existing", encoding="utf-8")

    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out)])
    assert result.exit_code == 1, result.output
    assert "existing" in (out / "a.svg").read_text(encoding="utf-8")

    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out), "--overwrite"])
    assert result.exit_code == 0, result.output
    assert "<svg" in (out / "a.svg").read_text(encoding="utf-8")


def test_batch_dry_run_writes_nothing(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed({"a.jpg": FIXTURES / "fixture_photo.jpg"}, src)
    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert not out.exists()


def test_batch_missing_directory(tmp_path: Path) -> None:
    result = runner.invoke(app, ["batch", str(tmp_path / "nope"), "--output-dir", "svg"])
    assert result.exit_code == 3
    assert "does not exist" in result.output


def test_batch_no_supported_files(tmp_path: Path) -> None:
    src = tmp_path / "images"
    src.mkdir()
    (src / "readme.txt").write_text("hello", encoding="utf-8")
    result = runner.invoke(app, ["batch", str(src), "--output-dir", "svg"])
    assert result.exit_code == 2
    assert "No supported images found" in result.output


def test_batch_jsonl_reports_one_line_per_file(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed(
        {
            "a.jpg": FIXTURES / "fixture_photo.jpg",
            "b.png": FIXTURES / "fixture_logo.png",
        },
        src,
    )
    result = runner.invoke(
        app,
        [
            "batch",
            str(src),
            "--output-dir",
            str(out),
            "--jsonl",
            "--report",
            str(tmp_path / "r.json"),
        ],
    )
    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "r.json").read_text(encoding="utf-8"))
    assert sorted(entry["status"] for entry in report["results"]) == ["success", "success"]


def test_batch_jobs_flag_accepted(tmp_path: Path) -> None:
    src = tmp_path / "images"
    out = tmp_path / "svg"
    _seed({"a.jpg": FIXTURES / "fixture_photo.jpg"}, src)
    result = runner.invoke(app, ["batch", str(src), "--output-dir", str(out), "--jobs", "2"])
    assert result.exit_code == 0, result.output
    assert (out / "a.svg").exists()


def test_batch_help_documents_options() -> None:
    result = runner.invoke(app, ["batch", "--help"])
    assert result.exit_code == 0
    for flag in (
        "--output-dir",
        "--recursive",
        "--include",
        "--exclude",
        "--jobs",
        "--fail-fast",
        "--overwrite",
        "--dry-run",
        "--report",
        "--jsonl",
        "--preset",
        "--config",
    ):
        assert flag in result.output
