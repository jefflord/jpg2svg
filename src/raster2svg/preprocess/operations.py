"""Individual image operations (PRD section 13).

Each function takes a Pillow image and returns the transformed image
(same object when nothing changed). All operations are pure and
deterministic so results are reproducible across runs.
"""

from __future__ import annotations

from typing import cast

from PIL import Image, ImageEnhance, ImageFilter, ImageOps

_EXIF_ORIENTATION_TAG = 0x0112


def has_exif_orientation(image: Image.Image) -> bool:
    """True when the image carries a non-trivial EXIF orientation tag."""
    try:
        orientation = image.getexif().get(_EXIF_ORIENTATION_TAG)
    except (AttributeError, KeyError, ValueError):
        return False
    return orientation not in (None, 1)


def auto_orient(image: Image.Image) -> Image.Image:
    """Rotate the image according to its EXIF orientation tag."""
    transposed = ImageOps.exif_transpose(image)
    return transposed if transposed is not None else image


def fit_to_box(image: Image.Image, width: int, height: int) -> Image.Image:
    """Scale the image to fit within ``width x height``.

    The aspect ratio is preserved and both up- and down-scaling are
    allowed (ImageMagick ``-resize`` semantics). A no-op when the image
    already fits inside the box.
    """
    img_width, img_height = image.size
    factor = min(width / img_width, height / img_height)
    if factor == 1.0:
        return image
    return _scaled(image, img_width * factor, img_height * factor)


def limit_max_width(image: Image.Image, max_width: int) -> Image.Image:
    """Shrink the image so its width is at most ``max_width`` (aspect preserved)."""
    img_width, img_height = image.size
    if img_width <= max_width:
        return image
    factor = max_width / img_width
    return _scaled(image, img_width * factor, img_height * factor)


def limit_max_height(image: Image.Image, max_height: int) -> Image.Image:
    """Shrink the image so its height is at most ``max_height`` (aspect preserved)."""
    img_width, img_height = image.size
    if img_height <= max_height:
        return image
    factor = max_height / img_height
    return _scaled(image, img_width * factor, img_height * factor)


def scale_by(image: Image.Image, factor: float) -> Image.Image:
    """Scale both dimensions by ``factor`` (e.g. 0.5 halves the image)."""
    if factor == 1.0:
        return image
    img_width, img_height = image.size
    return _scaled(image, img_width * factor, img_height * factor)


def to_grayscale(image: Image.Image) -> Image.Image:
    """Convert to grayscale (L mode). Already-gray images pass through."""
    if image.mode in ("L", "1"):
        return image
    return image.convert("L")


def denoise(image: Image.Image) -> Image.Image:
    """Conservative speckle removal (3x3 median filter)."""
    return image.filter(ImageFilter.MedianFilter(3))


def sharpen(image: Image.Image) -> Image.Image:
    """Conservative sharpening (unsharp mask that ignores near-identical pixels)."""
    return image.filter(ImageFilter.UnsharpMask(radius=1.5, percent=75, threshold=3))


def blur(image: Image.Image) -> Image.Image:
    """Smooth photographic texture (Gaussian blur, radius 1.0)."""
    return cast("Image.Image", image.filter(ImageFilter.GaussianBlur(radius=1.0)))


def posterize(image: Image.Image, bits: int) -> Image.Image:
    """Flatten every channel to ``2 ** bits`` levels (1-8 bits kept).

    ``ImageOps.posterize`` does not accept alpha modes, so images with an
    alpha channel are processed in RGB and the original alpha restored.
    """
    if image.mode in ("RGBA", "LA"):
        alpha = image.getchannel("A")
        result = ImageOps.posterize(image.convert("RGB"), bits)
        result.putalpha(alpha)
        return result
    return ImageOps.posterize(image, bits)


def autocontrast(image: Image.Image) -> Image.Image:
    """Stretch the histogram to the full range. Alpha channels are left untouched."""
    if image.mode in ("RGBA", "LA"):
        alpha = image.getchannel("A")
        result = ImageOps.autocontrast(image.convert("RGB"))
        result.putalpha(alpha)
        return result
    return ImageOps.autocontrast(image)


def crush_colors(image: Image.Image, n: int) -> Image.Image:
    """Reduce the image to at most ``n`` distinct colors, without dithering.

    Uses a flat (no dither) palette reduction so the result is clean,
    posterized regions rather than a speckled pattern. The color count is
    capped at ``n`` (Pillow palette limit is 256). Alpha, when present, is
    quantized on the color channels and the original alpha is restored.
    """
    alpha = image.getchannel("A") if image.mode in ("RGBA", "LA") else None
    base = image if image.mode == "RGB" else image.convert("RGB")
    quantized = base.quantize(
        colors=n,
        method=Image.Quantize.MEDIANCUT,
        dither=Image.Dither.NONE,
    ).convert("RGB")
    if alpha is not None:
        quantized.putalpha(alpha)
    return quantized


def adjust_contrast(image: Image.Image, factor: float) -> Image.Image:
    """Adjust contrast (1.0 = unchanged). Alpha channels are left untouched."""
    if factor == 1.0:
        return image
    return _enhance_alpha_safe(image, ImageEnhance.Contrast, factor)


def adjust_brightness(image: Image.Image, factor: float) -> Image.Image:
    """Adjust brightness (1.0 = unchanged). Alpha channels are left untouched."""
    if factor == 1.0:
        return image
    return _enhance_alpha_safe(image, ImageEnhance.Brightness, factor)


def _scaled(image: Image.Image, new_width: float, new_height: float) -> Image.Image:
    width = max(1, round(new_width))
    height = max(1, round(new_height))
    if (width, height) == image.size:
        return image
    return image.resize((width, height), Image.Resampling.LANCZOS)


def _enhance_alpha_safe(
    image: Image.Image,
    enhancer: type[ImageEnhance.Contrast] | type[ImageEnhance.Brightness],
    factor: float,
) -> Image.Image:
    """Apply an ImageEnhance filter to the color channels only.

    ``ImageEnhance`` would blend the alpha channel against a fully
    opaque baseline and silently destroy transparency, so images with an
    alpha channel are processed in RGB and the original alpha restored.
    """
    if image.mode in ("RGBA", "LA"):
        alpha = image.getchannel("A")
        enhanced = enhancer(image.convert("RGB")).enhance(factor)
        enhanced.putalpha(alpha)
        return enhanced
    return enhancer(image).enhance(factor)
