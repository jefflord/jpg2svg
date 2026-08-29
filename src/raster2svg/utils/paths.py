"""Path helpers and input validation (PRD sections 5.3 and 14)."""

from __future__ import annotations

from pathlib import Path

from raster2svg.core.errors import InputError

#: Extensions accepted as input. More formats may work when the decoder
#: supports them (PRD section 5.1).
SUPPORTED_INPUT_EXTENSIONS = {
    ".bmp",
    ".gif",
    ".jpeg",
    ".jpg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}

_IMAGE_FORMAT_BY_EXTENSION = {
    ".bmp": "bmp",
    ".gif": "gif",
    ".jpeg": "jpg",
    ".jpg": "jpg",
    ".png": "png",
    ".tif": "tiff",
    ".tiff": "tiff",
    ".webp": "webp",
}


def default_output_path(input_path: Path) -> Path:
    """Default output: same stem, ``.svg`` suffix (PRD section 7.4)."""
    return input_path.with_suffix(".svg")


def validate_input_path(input_path: Path) -> Path:
    """Apply PRD section 5.3 checks and return the normalized path."""
    path = Path(input_path)
    if not path.exists():
        raise InputError(
            f"Input file does not exist: {path}",
            hint="Check the path and try again.",
        )
    if not path.is_file():
        raise InputError(f"Input path is not a file: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_INPUT_EXTENSIONS:
        raise InputError(
            f"Unsupported input extension: {suffix or '(none)'}",
            hint=f"Supported: {', '.join(sorted(SUPPORTED_INPUT_EXTENSIONS))}",
        )
    return path


def image_format_hint(input_path: Path) -> str | None:
    """Best-effort image format name for the engine, or None to guess."""
    return _IMAGE_FORMAT_BY_EXTENSION.get(input_path.suffix.lower())
