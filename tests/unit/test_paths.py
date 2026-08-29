"""Unit tests for path handling and input validation (PRD sections 5.3, 7.4)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg.core.errors import InputError
from raster2svg.utils.paths import (
    default_output_path,
    image_format_hint,
    validate_input_path,
)


def test_default_output_name() -> None:
    assert default_output_path(Path("dir/photo.jpg")) == Path("dir/photo.svg")


def test_default_output_name_jpeg() -> None:
    assert default_output_path(Path("photo.jpeg")) == Path("photo.svg")


def test_missing_input_fails() -> None:
    with pytest.raises(InputError, match="does not exist"):
        validate_input_path(Path("does-not-exist.jpg"))


def test_directory_input_fails(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="not a file"):
        validate_input_path(tmp_path)


def test_unsupported_extension_fails(tmp_path: Path) -> None:
    target = tmp_path / "file.txt"
    target.write_text("x", encoding="utf-8")
    with pytest.raises(InputError, match="Unsupported input extension"):
        validate_input_path(target)


def test_format_hint() -> None:
    assert image_format_hint(Path("a.jpg")) == "jpg"
    assert image_format_hint(Path("a.JPEG")) == "jpg"
    assert image_format_hint(Path("a.xyz")) is None
