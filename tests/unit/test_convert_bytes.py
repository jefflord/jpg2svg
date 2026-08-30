"""Tests for Converter.convert_bytes, the in-memory API used by the web UI."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from raster2svg.config.models import ConversionConfig, PreprocessConfig
from raster2svg.core.capabilities import detect_vtracer_capabilities
from raster2svg.core.errors import UnsupportedFeatureError
from raster2svg.services.converter import Converter


def _jpeg_bytes(
    width: int = 64,
    height: int = 64,
    color: tuple[int, int, int] = (200, 30, 30),
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def test_convert_bytes_returns_svg_and_no_ops_by_default() -> None:
    svg, applied = Converter().convert_bytes(_jpeg_bytes(), "jpg")
    assert svg.lstrip().startswith("<?xml")
    assert applied == []


def test_convert_bytes_applies_preprocessing() -> None:
    svg, applied = Converter().convert_bytes(
        _jpeg_bytes(), "jpg", preprocess=PreprocessConfig(grayscale=True)
    )
    assert "<svg" in svg
    assert "grayscale" in applied


def test_convert_bytes_applies_pre_max_colors() -> None:
    _, applied = Converter().convert_bytes(
        _jpeg_bytes(), "jpg", preprocess=PreprocessConfig(pre_max_colors=6)
    )
    assert "pre_max_colors" in applied


def test_convert_bytes_expands_preset() -> None:
    svg, applied = Converter().convert_bytes(
        _jpeg_bytes(), "jpg", config=ConversionConfig(preset="photo")
    )
    assert "<svg" in svg
    assert applied == []


def test_convert_bytes_rejects_unsupported_engine_feature() -> None:
    if not detect_vtracer_capabilities().supports("adaptive"):
        with pytest.raises(UnsupportedFeatureError) as exc_info:
            Converter().convert_bytes(
                _jpeg_bytes(), "jpg", config=ConversionConfig.from_dict({"adaptive": True})
            )
        assert "VTracer 1.0" in (exc_info.value.hint or "")
