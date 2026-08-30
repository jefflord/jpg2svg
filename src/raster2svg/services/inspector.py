"""Image inspection service (PRD section 15.4).

A thin, reusable layer over Pillow so the CLI (and any future GUI) can
report what it is about to convert without running the tracing engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, UnidentifiedImageError

from raster2svg.core.errors import InputError
from raster2svg.utils.paths import validate_input_path

_EXIF_ORIENTATION_TAG = 0x0112

_BANDS_BY_MODE = {
    "1": 1,
    "L": 1,
    "LA": 2,
    "I": 4,
    "I;16": 2,
    "P": 1,
    "RGB": 3,
    "RGBA": 4,
    "RGBX": 4,
    "CMYK": 4,
    "YCbCr": 3,
    "LAB": 3,
    "HSV": 3,
}


@dataclass(frozen=True)
class ImageInspection:
    """Facts about a raster image, captured without a full decode."""

    path: Path
    format: str
    mode: str
    width: int
    height: int
    has_alpha: bool
    exif_orientation: int | None
    size_bytes: int
    estimated_memory_bytes: int

    @property
    def pixels(self) -> int:
        """Total pixel count (width * height)."""
        return self.width * self.height

    def to_dict(self) -> dict[str, object]:
        """JSON-ready representation (PRD 15.4)."""
        return {
            "path": str(self.path),
            "format": self.format,
            "mode": self.mode,
            "width": self.width,
            "height": self.height,
            "pixels": self.pixels,
            "has_alpha": self.has_alpha,
            "exif_orientation": self.exif_orientation,
            "size_bytes": self.size_bytes,
            "estimated_memory_bytes": self.estimated_memory_bytes,
        }


def inspect_image(path: str | Path) -> ImageInspection:
    """Inspect a raster image (PRD 5.3/15.4).

    Raises:
        InputError: if the file is missing, unreadable, corrupt, or invalid.
    """
    input_path = validate_input_path(Path(path))
    try:
        with Image.open(input_path) as image:
            image.load()
            width, height = image.size
            fmt = (image.format or "UNKNOWN").upper()
            mode = image.mode
            has_alpha = mode in ("RGBA", "LA", "PA") or "transparency" in image.info
            orientation = _exif_orientation(image)
    except (OSError, UnidentifiedImageError) as exc:
        raise InputError(
            f"Cannot decode image: {input_path}",
            hint="The file is corrupt or not a supported raster image.",
        ) from exc
    if width <= 0 or height <= 0:
        raise InputError(f"Image has invalid dimensions {width}x{height}: {input_path}")
    bands = _BANDS_BY_MODE.get(mode, 3)
    return ImageInspection(
        path=input_path,
        format=fmt,
        mode=mode,
        width=width,
        height=height,
        has_alpha=has_alpha,
        exif_orientation=orientation,
        size_bytes=input_path.stat().st_size,
        estimated_memory_bytes=width * height * bands,
    )


def _exif_orientation(image: Image.Image) -> int | None:
    try:
        exif = image.getexif()
    except (OSError, ValueError):
        return None
    value = exif.get(_EXIF_ORIENTATION_TAG)
    return int(value) if isinstance(value, int) else None
