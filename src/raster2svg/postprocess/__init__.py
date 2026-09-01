"""SVG output post-processing (final pipeline stage)."""

from __future__ import annotations

from raster2svg.postprocess.svg import PostprocessResult, apply_postprocessing, invert_svg

__all__ = ["PostprocessResult", "apply_postprocessing", "invert_svg"]
