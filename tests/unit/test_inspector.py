"""Unit tests for the image inspection service (PRD section 15.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg import ImageInspection, inspect_image
from raster2svg.core.errors import InputError

FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_inspect_jpeg_reported_fields() -> None:
    result = inspect_image(FIXTURES / "fixture_photo.jpg")
    assert isinstance(result, ImageInspection)
    assert result.format == "JPEG"
    assert result.mode == "RGB"
    assert result.width == 96
    assert result.height == 96
    assert result.pixels == 96 * 96
    assert result.has_alpha is False
    assert result.exif_orientation is None
    assert result.size_bytes > 0
    assert result.estimated_memory_bytes == 96 * 96 * 3


def test_inspect_translucent_png_reports_alpha() -> None:
    result = inspect_image(FIXTURES / "fixture_logo.png")
    assert result.format == "PNG"
    assert result.has_alpha is True
    assert result.estimated_memory_bytes == 64 * 64 * 4


def test_inspect_exif_orientation() -> None:
    result = inspect_image(FIXTURES / "fixture_oriented.jpg")
    assert result.exif_orientation == 6


def test_inspect_missing_file_raises_input_error() -> None:
    with pytest.raises(InputError) as exc_info:
        inspect_image(FIXTURES / "missing.jpg")
    assert exc_info.value.exit_code == 3


def test_inspect_corrupt_file_raises_input_error() -> None:
    with pytest.raises(InputError) as exc_info:
        inspect_image(FIXTURES / "fixture_corrupt.jpg")
    assert exc_info.value.exit_code == 3


def test_inspect_to_dict() -> None:
    result = inspect_image(FIXTURES / "fixture_photo.jpg")
    data = result.to_dict()
    assert data["path"] == str(FIXTURES / "fixture_photo.jpg")
    assert data["format"] == "JPEG"
    assert data["pixels"] == result.pixels
    assert data["has_alpha"] is False
    assert set(data) == {
        "path",
        "format",
        "mode",
        "width",
        "height",
        "pixels",
        "has_alpha",
        "exif_orientation",
        "size_bytes",
        "estimated_memory_bytes",
    }
