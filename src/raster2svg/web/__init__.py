"""Local web interface for real-time raster-to-SVG conversion.

A single-user, stdlib-only HTTP server (no new dependencies) that lets a user
upload an image once and then tweak conversion options live, preview the SVG
in the browser, and download the result. See ``raster2svg_web_prd.md``.
"""

from __future__ import annotations

__all__ = ["session", "server", "cli"]
