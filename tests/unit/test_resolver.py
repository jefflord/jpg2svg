"""Unit tests for configuration precedence (PRD sections 8 and 9.1)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.core.errors import ConfigError


def test_preset_applies_values() -> None:
    cfg = resolve_conversion_config(preset="photo")
    assert cfg.clustering == "color-cluster"
    assert cfg.hierarchical == "stacked"
    assert cfg.mode == "spline"
    assert cfg.layer_difference == 12


def test_cli_overrides_preset() -> None:
    cfg = resolve_conversion_config(preset="poster", cli_values={"hierarchical": "stacked"})
    assert cfg.hierarchical == "stacked"
    assert cfg.clustering == "color-cluster"  # still from the preset


def test_config_file_overrides_preset_and_cli_wins() -> None:
    cfg = resolve_conversion_config(
        preset="bw",
        config_file_values={"mode": "polygon"},
        cli_values={"mode": "spline"},
    )
    assert cfg.mode == "spline"
    assert cfg.clustering == "bw"  # preset value untouched


def test_unknown_preset_is_an_actionable_error() -> None:
    with pytest.raises(ConfigError, match="Unknown preset"):
        resolve_conversion_config(preset="nope")


def test_adaptive_implies_bw_clustering() -> None:
    cfg = resolve_conversion_config(cli_values={"adaptive": True})
    assert cfg.clustering == "bw"


def test_adaptive_conflicts_with_explicit_cli_clustering() -> None:
    with pytest.raises(ConfigError, match="--clustering bw"):
        resolve_conversion_config(cli_values={"adaptive": True, "clustering": "color-cluster"})


def test_palette_file_is_materialized(tmp_path: Path) -> None:
    palette_file = tmp_path / "palette.txt"
    palette_file.write_text("#1b1b1b\n\n#e0c088\n", encoding="utf-8")
    cfg = resolve_conversion_config(cli_values={"palette_file": palette_file})
    assert cfg.palette == ["#1b1b1b", "#e0c088"]
    assert cfg.palette_file is None


def test_missing_palette_file_fails_cleanly(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="Palette file not found"):
        resolve_conversion_config(cli_values={"palette_file": tmp_path / "missing.txt"})
