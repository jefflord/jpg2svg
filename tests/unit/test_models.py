"""Unit tests for configuration models (PRD sections 9 and 20)."""

from __future__ import annotations

import pytest

from raster2svg.config.models import ConversionConfig, OutputConfig
from raster2svg.core.errors import ConfigError


def test_defaults_are_engine_defaults() -> None:
    cfg = ConversionConfig()
    assert cfg.preset is None
    assert cfg.clustering is None
    assert cfg.hierarchical is None
    assert cfg.mode is None
    assert cfg.color_precision is None
    assert cfg.simplify is None
    assert cfg.palette is None


def test_valid_values_are_accepted() -> None:
    cfg = ConversionConfig.from_dict(
        {
            "clustering": "bw",
            "hierarchical": "cutout",
            "mode": "polygon",
            "color_precision": 8,
            "length_threshold": 5.0,
            "corner_threshold": 90,
        }
    )
    assert cfg.clustering == "bw"
    assert cfg.hierarchical == "cutout"
    assert cfg.mode == "polygon"


@pytest.mark.parametrize("value", [0, 9, -1])
def test_color_precision_range(value: int) -> None:
    with pytest.raises(ConfigError):
        ConversionConfig.from_dict({"color_precision": value})


def test_invalid_enum_is_rejected() -> None:
    with pytest.raises(ConfigError):
        ConversionConfig.from_dict({"clustering": "nonsense"})


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ConfigError):
        ConversionConfig.from_dict({"no_such_option": 1})


def test_palette_validation_and_dedup() -> None:
    cfg = ConversionConfig.from_dict({"palette": ["#abc", "#1b1b1b", "#1b1b1b"]})
    assert cfg.palette == ["#abc", "#1b1b1b"]


def test_palette_rejects_garbage() -> None:
    with pytest.raises(ConfigError):
        ConversionConfig.from_dict({"palette": ["red"]})


def test_palette_and_file_are_mutually_exclusive() -> None:
    with pytest.raises(ConfigError):
        ConversionConfig.from_dict({"palette": ["#abc"], "palette_file": "p.txt"})


def test_output_config_defaults() -> None:
    out = OutputConfig()
    assert out.overwrite is False
    assert out.validate_svg is True
    assert out.create_directories is True
