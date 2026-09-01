"""The post-processing pipeline (final stage of PRD section 4.1).

Takes the traced SVG text plus a ``PostprocessConfig`` and returns the
SVG to write. When no operation is enabled the original SVG is returned
untouched, so a default configuration is a no-op.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from raster2svg.config.models import PostprocessConfig

# An explicit fill value, e.g. fill="#000000".
_FILL_RE = re.compile(r'fill="([^"]*)"')
# A hex colour (3- or 6-digit) with a leading "#".
_HEX_RE = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")
# A shape opening tag with its attributes (e.g. <path d="..."/>).
_SHAPE_RE = re.compile(r"<(path|rect|circle|ellipse|polygon|polyline)\b([^<>]*?)(/?)>")


@dataclass(frozen=True)
class PostprocessResult:
    """Outcome of running the post-processing pipeline over one SVG."""

    svg: str
    applied: tuple[str, ...] = ()


def invert_svg(svg: str) -> str:
    """Render an SVG as a negative (light strokes on a dark background).

    Three steps, in this order:

    1. Invert every explicit ``#rrggbb`` fill to its complement.
    2. Force shapes with an implicit (unspecified) black fill to white, so
       line art that traced as "no fill" stays visible on a dark ground.
    3. Insert a dark background rect as the first child of ``<svg>`` so the
       result reads as light-on-dark. Done last so its own fill is never
       inverted by step 1.
    """
    svg = _FILL_RE.sub(_invert_hex, svg)
    svg = _SHAPE_RE.sub(_add_white_fill, svg)
    return _insert_background(svg)


def _invert_hex(match: re.Match[str]) -> str:
    """Invert a single ``fill="..."`` value when it is a hex colour."""
    value = match.group(1)
    hex_match = _HEX_RE.match(value)
    if hex_match is None:
        return match.group(0)
    digits = hex_match.group(1)
    if len(digits) == 3:
        digits = "".join(ch * 2 for ch in digits)
    red = 255 - int(digits[0:2], 16)
    green = 255 - int(digits[2:4], 16)
    blue = 255 - int(digits[4:6], 16)
    return f'fill="#{red:02x}{green:02x}{blue:02x}"'


def _add_white_fill(match: re.Match[str]) -> str:
    """Give a shape with no explicit fill a white fill."""
    tag = match.group(1)
    attrs = match.group(2) or ""
    close = match.group(3)
    if re.search(r"\bfill\s*=", attrs):
        return match.group(0)
    return f'<{tag} fill="#ffffff"{attrs}{close}>'


def _insert_background(svg: str) -> str:
    """Add a dark background rect as the first child of ``<svg>``."""
    return re.sub(
        r"(<svg[^>]*>)",
        r'\1<rect width="100%" height="100%" fill="#000000"/>',
        svg,
        count=1,
    )


def apply_postprocessing(
    svg: str,
    config: PostprocessConfig,
) -> PostprocessResult:
    """Run every enabled post-processing operation in a fixed order."""
    applied: list[str] = []
    if config.invert:
        svg = invert_svg(svg)
        applied.append("invert")
    return PostprocessResult(svg=svg, applied=tuple(applied))
