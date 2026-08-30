"""The preprocessing pipeline (PRD section 13).

Takes the raw image bytes plus a ``PreprocessConfig`` and returns the
bytes to hand to the tracing engine. When no operation is needed the
original bytes are returned untouched, so a default configuration never
re-encodes (and never loses quality).
"""

from __future__ import annotations

import io
from collections.abc import Callable
from dataclasses import dataclass

from PIL import Image, UnidentifiedImageError

from raster2svg.config.models import PreprocessConfig, parse_resize
from raster2svg.core.errors import InputError
from raster2svg.preprocess import operations as ops

JPEG_QUALITY = 95


@dataclass(frozen=True)
class PreprocessResult:
    """Outcome of running the pipeline over one image."""

    image_bytes: bytes
    image_format: str
    applied: tuple[str, ...] = ()


def apply_preprocessing(
    image_bytes: bytes,
    image_format: str,
    config: PreprocessConfig,
) -> PreprocessResult:
    """Run every enabled operation in a fixed, documented order.

    Operation order: auto-orientation, resize, max-width, max-height,
    scale, grayscale, denoise, contrast, brightness, sharpen,
    pre-max-colors (last, so the palette cap holds).
    """
    try:
        image: Image.Image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except (OSError, UnidentifiedImageError) as exc:
        raise InputError(
            "Cannot decode image for preprocessing.",
            hint="The file is corrupt or not a supported raster image.",
        ) from exc

    applied: list[str] = []

    def apply(name: str, transform: Callable[[], Image.Image]) -> None:
        """Run ``transform`` and record the operation only if it changed the image."""
        nonlocal image
        result = transform()
        if result is not image:
            image = result
            applied.append(name)

    if config.auto_orient:
        apply(
            "auto_orient",
            lambda: ops.auto_orient(image) if ops.has_exif_orientation(image) else image,
        )

    if config.resize is not None:
        width, height = parse_resize(config.resize)
        apply("resize", lambda: ops.fit_to_box(image, width, height))

    if config.max_width is not None:
        max_width = config.max_width
        apply("max_width", lambda: ops.limit_max_width(image, max_width))

    if config.max_height is not None:
        max_height = config.max_height
        apply("max_height", lambda: ops.limit_max_height(image, max_height))

    if config.scale is not None and config.scale != 1.0:
        scale = config.scale
        apply("scale", lambda: ops.scale_by(image, scale))

    if config.grayscale:
        apply("grayscale", lambda: ops.to_grayscale(image))

    if config.denoise:
        image = ops.denoise(image)
        applied.append("denoise")

    if config.contrast is not None and config.contrast != 1.0:
        image = ops.adjust_contrast(image, config.contrast)
        applied.append("contrast")

    if config.brightness is not None and config.brightness != 1.0:
        image = ops.adjust_brightness(image, config.brightness)
        applied.append("brightness")

    if config.sharpen:
        image = ops.sharpen(image)
        applied.append("sharpen")

    if config.pre_max_colors is not None:
        pre_max = config.pre_max_colors
        image = ops.crush_colors(image, pre_max)
        applied.append("pre_max_colors")

    if not applied:
        return PreprocessResult(image_bytes=image_bytes, image_format=image_format)

    # A palette cap must survive re-encoding, so force lossless output.
    lossless = config.pre_max_colors is not None
    encoded, format_hint = _encode(image, image_format, lossless=lossless)
    return PreprocessResult(image_bytes=encoded, image_format=format_hint, applied=tuple(applied))


def _encode(image: Image.Image, original_format: str, lossless: bool = False) -> tuple[bytes, str]:
    """Re-encode the processed image.

    JPEG inputs stay JPEG (lossless when the image is still RGB/L and the
    only change was e.g. a resize). Anything with an alpha channel or an
    exotic source format becomes PNG, which VTracer decodes reliably.
    When ``lossless`` is set (a palette cap was applied) always use PNG so
    the exact colors are preserved.
    """
    buffer = io.BytesIO()
    if (
        not lossless
        and original_format.lower() in ("jpg", "jpeg")
        and image.mode in ("RGB", "L")
    ):
        image.save(buffer, format="JPEG", quality=JPEG_QUALITY)
        return buffer.getvalue(), "jpg"
    image.save(buffer, format="PNG")
    return buffer.getvalue(), "png"
