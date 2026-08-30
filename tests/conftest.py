"""Shared test fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def isolated_app_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point RASTER2SVG_DATA_DIR at a per-test temp dir.

    Keeps tests hermetic: a developer's real user-level config file
    (config.toml in the app data directory) can never leak into a test.
    """
    data = tmp_path / "raster2svg-data"
    data.mkdir()
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(data))
    return data


@pytest.fixture()
def fixtures_dir() -> Path:
    return FIXTURES
