"""SVG output checks (PRD section 5.4)."""

from __future__ import annotations

import xml.etree.ElementTree as ET

from raster2svg.core.errors import EngineError


def validate_svg(svg_text: str) -> str:
    """Parse generated SVG and return the local root tag (e.g. ``svg``)."""
    if not svg_text or not svg_text.strip():
        raise EngineError("The generated SVG document is empty.")
    try:
        root = ET.fromstring(svg_text)
    except ET.ParseError as exc:
        raise EngineError(f"Generated SVG is not well-formed XML: {exc}") from exc
    root_name = root.tag.rsplit("}", 1)[-1]
    if root_name != "svg":
        raise EngineError(f"Generated SVG root element is <{root_name}>, expected <svg>.")
    return root_name
