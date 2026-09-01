"""Tests for Converter.convert_bytes, the in-memory API used by the web UI."""

from __future__ import annotations

import io

import pytest
from PIL import Image

from raster2svg.config.models import ConversionConfig, PostprocessConfig, PreprocessConfig
from raster2svg.core.errors import UnsupportedFeatureError
from raster2svg.services.converter import Converter

_BACKGROUND = '<rect width="100%" height="100%" fill="#000000"/>'


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
    # The photo preset's preprocess base applies when no explicit preprocess is given.
    assert applied == ["denoise"]


def test_convert_bytes_rejects_unsupported_engine_feature() -> None:
    # No installed engine honours both options: `adaptive` needs a 1.0 build
    # while `corner_threshold` is a 0.6 Python-only parameter, so the
    # combination is rejected regardless of which engines are present.
    config = ConversionConfig.from_dict({"adaptive": True, "corner_threshold": 90.0})
    with pytest.raises(UnsupportedFeatureError) as exc_info:
        Converter().convert_bytes(_jpeg_bytes(), "jpg", config=config)
    assert "VTracer 1.0" in (exc_info.value.hint or "")
    assert "does not support" in exc_info.value.message


def test_convert_bytes_invert_adds_dark_background() -> None:
    svg, _ = Converter().convert_bytes(
        _jpeg_bytes(), "jpg", postprocess=PostprocessConfig(invert=True)
    )
    assert _BACKGROUND in svg


def test_convert_bytes_invert_default_is_off() -> None:
    svg, _ = Converter().convert_bytes(_jpeg_bytes(), "jpg")
    assert _BACKGROUND not in svg


def test_convert_bytes_expands_inverted_preset() -> None:
    svg, _ = Converter().convert_bytes(
        _jpeg_bytes(), "jpg", config=ConversionConfig(preset="line-art-inverted")
    )
    assert _BACKGROUND in svg


def test_convert_bytes_explicit_postprocess_beats_inverted_preset() -> None:
    svg, _ = Converter().convert_bytes(
        _jpeg_bytes(),
        "jpg",
        config=ConversionConfig(preset="silhouette-inverted"),
        postprocess=PostprocessConfig(invert=False),
    )
    assert _BACKGROUND not in svg
