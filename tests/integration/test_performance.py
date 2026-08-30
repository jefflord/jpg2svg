"""Performance tracking tests (PRD section 25.4).

These are *tracking* tests: they run a representative image through the full
conversion and record duration, SVG size, and (as a practical proxy) peak
Python-heap memory. Bounds are intentionally generous so the tests stay green
across machines and engine versions, while still catching catastrophic
regressions (a hang, an empty output, or an exploding file).
"""

from __future__ import annotations

import time
import tracemalloc
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from raster2svg import Converter
from raster2svg.config.models import OutputConfig

SIZES: tuple[tuple[int, int], ...] = ((512, 512), (1920, 1080), (4000, 3000))


def _make_image(tmp_path: Path, width: int, height: int) -> Path:
    """A gradient background with a couple of shapes (deterministic, no network)."""
    grad = Image.linear_gradient("L").resize((width, height)).convert("RGB")
    draw = ImageDraw.Draw(grad)
    draw.ellipse([width // 4, height // 4, 3 * width // 4, 3 * height // 4], fill=(240, 240, 240))
    draw.rectangle([width // 8, height // 2, width // 2, 3 * height // 4], fill=(30, 90, 200))
    src = tmp_path / f"perf_{width}x{height}.jpg"
    grad.save(src, quality=88)
    return src


@pytest.mark.parametrize("width,height", SIZES)
def test_conversion_performance(tmp_path: Path, width: int, height: int) -> None:
    src = _make_image(tmp_path, width, height)
    out = tmp_path / "out.svg"

    tracemalloc.start()
    started = time.perf_counter()
    result = Converter().convert(src, out, output=OutputConfig(overwrite=True))
    elapsed = time.perf_counter() - started
    _, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    svg_bytes = out.stat().st_size if out.is_file() else 0
    report = (
        f"{width}x{height}: {elapsed:.2f}s, svg={svg_bytes / 1024:.0f} KiB, "
        f"peak_py_heap={peak_bytes / (1024 * 1024):.0f} MiB"
    )

    assert result.status == "success", report
    assert out.is_file() and svg_bytes > 0, report
    assert elapsed < 60.0, report
    assert svg_bytes < 50 * 1024 * 1024, report
    print(report)
