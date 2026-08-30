"""Unit tests for the image preprocessing pipeline (PRD section 13)."""

from __future__ import annotations

import io
import random
from pathlib import Path

import pytest
from PIL import Image

from raster2svg.config.models import PreprocessConfig
from raster2svg.core.errors import ConfigError, InputError
from raster2svg.preprocess.image import apply_preprocessing

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _jpeg_bytes(width: int, height: int, color: tuple[int, int, int] = (200, 30, 30)) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _png_bytes(
    width: int, height: int, color: tuple[int, int, int, int] = (200, 30, 30, 128)
) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGBA", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def _decoded_size(data: bytes) -> tuple[int, int]:
    with Image.open(io.BytesIO(data)) as image:
        return image.size


def _colorful_jpeg(seed: int = 1) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGB", (32, 32))
    px = img.load()
    assert px is not None
    for y in range(32):
        for x in range(32):
            px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _colorful_rgba(seed: int = 2) -> bytes:
    rng = random.Random(seed)
    img = Image.new("RGBA", (32, 32))
    px = img.load()
    assert px is not None
    for y in range(32):
        for x in range(32):
            px[x, y] = (rng.randrange(256), rng.randrange(256), rng.randrange(256), 128)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def _distinct_colors(data: bytes) -> int:
    with Image.open(io.BytesIO(data)) as image:
        colors = image.getcolors(maxcolors=100000)
        assert colors is not None
        return len(colors)


def test_parse_resize_accepts_common_forms() -> None:
    from raster2svg.config.models import parse_resize

    assert parse_resize("1920x1080") == (1920, 1080)
    assert parse_resize(" 1920X1080 ") == (1920, 1080)


@pytest.mark.parametrize("value", ["abc", "1920", "1920x", "x1080", "0x1080", "1920x0", "-1x10"])
def test_parse_resize_rejects_invalid_sizes(value: str) -> None:
    with pytest.raises(ConfigError) as exc_info:
        PreprocessConfig.from_dict({"resize": value})
    assert "invalid resize size" in (exc_info.value.hint or "")


def test_default_config_is_a_noop_and_keeps_original_bytes() -> None:
    data = _jpeg_bytes(200, 100)
    result = apply_preprocessing(data, "jpg", PreprocessConfig())
    assert result.applied == ()
    assert result.image_bytes == data
    assert result.image_format == "jpg"


def test_auto_orient_applies_exif_rotation() -> None:
    data = (FIXTURES / "fixture_oriented.jpg").read_bytes()
    result = apply_preprocessing(data, "jpg", PreprocessConfig(auto_orient=True))
    assert "auto_orient" in result.applied
    assert _decoded_size(result.image_bytes) == (48, 96)


def test_auto_orient_can_be_disabled() -> None:
    data = (FIXTURES / "fixture_oriented.jpg").read_bytes()
    result = apply_preprocessing(data, "jpg", PreprocessConfig(auto_orient=False))
    assert result.applied == ()
    assert _decoded_size(result.image_bytes) == (96, 48)


def test_resize_fits_within_box_preserving_aspect() -> None:
    result = apply_preprocessing(_jpeg_bytes(200, 100), "jpg", PreprocessConfig(resize="50x50"))
    assert result.applied == ("resize",)
    assert _decoded_size(result.image_bytes) == (50, 25)


def test_resize_uses_height_when_it_is_the_constraint() -> None:
    result = apply_preprocessing(_jpeg_bytes(100, 200), "jpg", PreprocessConfig(resize="50x50"))
    assert _decoded_size(result.image_bytes) == (25, 50)


def test_resize_allows_upscaling() -> None:
    result = apply_preprocessing(_jpeg_bytes(10, 5), "jpg", PreprocessConfig(resize="20x20"))
    assert _decoded_size(result.image_bytes) == (20, 10)


def test_resize_is_a_noop_when_dimensions_already_match() -> None:
    data = _jpeg_bytes(50, 25)
    result = apply_preprocessing(data, "jpg", PreprocessConfig(resize="50x50"))
    assert result.applied == ()
    assert result.image_bytes == data


def test_max_width_shrinks_and_preserves_aspect() -> None:
    result = apply_preprocessing(_jpeg_bytes(200, 100), "jpg", PreprocessConfig(max_width=50))
    assert result.applied == ("max_width",)
    assert _decoded_size(result.image_bytes) == (50, 25)


def test_max_width_is_a_noop_when_smaller() -> None:
    result = apply_preprocessing(_jpeg_bytes(40, 100), "jpg", PreprocessConfig(max_width=50))
    assert result.applied == ()


def test_max_height_shrinks_and_preserves_aspect() -> None:
    result = apply_preprocessing(_jpeg_bytes(100, 200), "jpg", PreprocessConfig(max_height=50))
    assert result.applied == ("max_height",)
    assert _decoded_size(result.image_bytes) == (25, 50)


def test_scale_halves_both_dimensions() -> None:
    result = apply_preprocessing(_jpeg_bytes(200, 100), "jpg", PreprocessConfig(scale=0.5))
    assert result.applied == ("scale",)
    assert _decoded_size(result.image_bytes) == (100, 50)


def test_scale_of_one_is_a_noop() -> None:
    data = _jpeg_bytes(200, 100)
    result = apply_preprocessing(data, "jpg", PreprocessConfig(scale=1.0))
    assert result.applied == ()
    assert result.image_bytes == data


def test_grayscale_produces_l_mode() -> None:
    result = apply_preprocessing(_jpeg_bytes(64, 32), "jpg", PreprocessConfig(grayscale=True))
    assert "grayscale" in result.applied
    with Image.open(io.BytesIO(result.image_bytes)) as image:
        assert image.mode == "L"


def test_denoise_and_sharpen_apply_and_preserve_size() -> None:
    result = apply_preprocessing(
        _jpeg_bytes(64, 32), "jpg", PreprocessConfig(denoise=True, sharpen=True)
    )
    assert result.applied == ("denoise", "sharpen")
    assert _decoded_size(result.image_bytes) == (64, 32)


def test_contrast_and_brightness_identity_factors_are_noops() -> None:
    data = _jpeg_bytes(64, 32)
    result = apply_preprocessing(data, "jpg", PreprocessConfig(contrast=1.0, brightness=1.0))
    assert result.applied == ()
    assert result.image_bytes == data


def test_contrast_and_brightness_change_pixels() -> None:
    data = _jpeg_bytes(64, 32, (128, 128, 128))
    result = apply_preprocessing(data, "jpg", PreprocessConfig(contrast=1.5, brightness=0.8))
    assert result.applied == ("contrast", "brightness")
    assert result.image_bytes != data


def test_contrast_preserves_alpha_channel() -> None:
    data = _png_bytes(32, 32, (200, 30, 30, 128))
    result = apply_preprocessing(data, "png", PreprocessConfig(contrast=1.5))
    assert "contrast" in result.applied
    with Image.open(io.BytesIO(result.image_bytes)) as image:
        assert image.mode == "RGBA"
        # Alpha must be untouched (128), even though the color changed.
        pixel = image.getpixel((16, 16))
        assert isinstance(pixel, tuple)
        assert pixel[3] == 128


def test_operations_apply_in_documented_order() -> None:
    result = apply_preprocessing(
        _jpeg_bytes(200, 100),
        "jpg",
        PreprocessConfig(resize="50x50", scale=2.0, grayscale=True),
    )
    assert result.applied == ("resize", "scale", "grayscale")
    # 200x100 -> fit 50x50 -> 50x25 -> scale x2 -> 100x50
    assert _decoded_size(result.image_bytes) == (100, 50)


def test_jpeg_input_stays_jpeg_after_resize() -> None:
    result = apply_preprocessing(_jpeg_bytes(200, 100), "jpg", PreprocessConfig(resize="50x50"))
    assert result.image_format == "jpg"


def test_rgba_input_reencodes_as_png() -> None:
    result = apply_preprocessing(_png_bytes(64, 32), "png", PreprocessConfig(contrast=1.2))
    assert result.image_format == "png"


def test_grayscale_of_rgba_reencodes_as_png() -> None:
    result = apply_preprocessing(_png_bytes(64, 32), "png", PreprocessConfig(grayscale=True))
    assert result.image_format == "png"
    with Image.open(io.BytesIO(result.image_bytes)) as image:
        assert image.mode == "L"


def test_pre_max_colors_crushes_to_n_colors() -> None:
    result = apply_preprocessing(_colorful_jpeg(), "jpg", PreprocessConfig(pre_max_colors=6))
    assert result.applied == ("pre_max_colors",)
    assert _distinct_colors(result.image_bytes) <= 6


@pytest.mark.parametrize("n", [1, 2, 4, 8, 16, 32, 64, 128, 256])
def test_pre_max_colors_bounds(n: int) -> None:
    result = apply_preprocessing(_colorful_jpeg(), "jpg", PreprocessConfig(pre_max_colors=n))
    assert 1 <= _distinct_colors(result.image_bytes) <= n


def test_pre_max_colors_forces_lossless_png() -> None:
    result = apply_preprocessing(_colorful_jpeg(), "jpg", PreprocessConfig(pre_max_colors=8))
    assert result.image_format == "png"
    assert _distinct_colors(result.image_bytes) <= 8


def test_pre_max_colors_runs_last_so_cap_holds_with_sharpen() -> None:
    result = apply_preprocessing(
        _colorful_jpeg(), "jpg", PreprocessConfig(sharpen=True, pre_max_colors=5)
    )
    assert result.applied == ("sharpen", "pre_max_colors")
    assert _distinct_colors(result.image_bytes) <= 5


def test_pre_max_colors_preserves_alpha() -> None:
    result = apply_preprocessing(_colorful_rgba(), "png", PreprocessConfig(pre_max_colors=6))
    with Image.open(io.BytesIO(result.image_bytes)) as image:
        assert image.mode == "RGBA"
        pixel = image.getpixel((16, 16))
        assert isinstance(pixel, tuple)
        assert pixel[3] == 128
        colors = image.convert("RGB").getcolors(maxcolors=100000)
        assert colors is not None
        assert len(colors) <= 6


def test_pre_max_colors_out_of_range_is_rejected() -> None:
    with pytest.raises(ConfigError) as low:
        PreprocessConfig.from_dict({"pre_max_colors": 0})
    assert "pre_max_colors" in (low.value.hint or "")
    with pytest.raises(ConfigError) as high:
        PreprocessConfig.from_dict({"pre_max_colors": 257})
    assert "pre_max_colors" in (high.value.hint or "")


def test_uncodeable_input_is_an_input_error() -> None:
    with pytest.raises(InputError, match="Cannot decode"):
        apply_preprocessing(b"not an image", "jpg", PreprocessConfig())


def test_out_of_range_factor_is_rejected() -> None:
    with pytest.raises(ConfigError) as contrast:
        PreprocessConfig.from_dict({"contrast": 11})
    assert "contrast" in (contrast.value.hint or "")
    with pytest.raises(ConfigError) as scale:
        PreprocessConfig.from_dict({"scale": 0})
    assert "scale" in (scale.value.hint or "")
