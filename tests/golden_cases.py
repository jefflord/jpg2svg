"""Shared golden-test case definitions (PRD section 25.3).

Each case pins a deterministic input image and conversion config. The expected
SVG output is committed under ``tests/golden/<name>.svg`` and can be
regenerated with ``python tests/generate_golden.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from raster2svg.config.models import Clustering, ConversionConfig, CurveMode

TESTS_DIR = Path(__file__).resolve().parent
GOLDEN_DIR = TESTS_DIR / "golden"
FIXTURES_DIR = TESTS_DIR / "fixtures"


@dataclass(frozen=True)
class GoldenCase:
    """A deterministic input + config pair and its expected output location."""

    name: str
    fixture: Path
    config: ConversionConfig
    width: int
    height: int

    @property
    def golden_path(self) -> Path:
        return GOLDEN_DIR / f"{self.name}.svg"


GOLDEN_CASES: tuple[GoldenCase, ...] = (
    GoldenCase(
        name="photo_spline",
        fixture=FIXTURES_DIR / "fixture_photo.jpg",
        config=ConversionConfig(clustering=Clustering.COLOR_CLUSTER, mode=CurveMode.SPLINE),
        width=96,
        height=96,
    ),
    GoldenCase(
        name="photo_pixel",
        fixture=FIXTURES_DIR / "fixture_photo.jpg",
        config=ConversionConfig(clustering=Clustering.COLOR_CLUSTER, mode=CurveMode.PIXEL),
        width=96,
        height=96,
    ),
    GoldenCase(
        name="photo_polygon",
        fixture=FIXTURES_DIR / "fixture_photo.jpg",
        config=ConversionConfig(clustering=Clustering.COLOR_CLUSTER, mode=CurveMode.POLYGON),
        width=96,
        height=96,
    ),
    GoldenCase(
        name="bw_spline",
        fixture=FIXTURES_DIR / "fixture_bw.png",
        config=ConversionConfig(clustering=Clustering.BW, mode=CurveMode.SPLINE),
        width=48,
        height=48,
    ),
    GoldenCase(
        name="logo_spline",
        fixture=FIXTURES_DIR / "fixture_logo.png",
        config=ConversionConfig(clustering=Clustering.COLOR_CLUSTER, mode=CurveMode.SPLINE),
        width=64,
        height=64,
    ),
)
