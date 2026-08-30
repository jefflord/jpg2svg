"""End-to-end tests for the VTracer 1.0 CLI engine.

Tests that need the native binary are skipped when it is not detected
(``raster2svg engine capabilities`` shows which engines are available).
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from raster2svg import Converter
from raster2svg.config.models import ConversionConfig, OutputConfig
from raster2svg.engines.base import TracingEngine
from raster2svg.engines.vtracer_cli import detect_vtracer_cli_capabilities
from raster2svg.web.server import build_info_payload

FIXTURES = Path(__file__).parent.parent / "fixtures"

HAS_CLI_ENGINE = detect_vtracer_cli_capabilities() is not None

requires_cli_engine = pytest.mark.skipif(
    not HAS_CLI_ENGINE, reason="VTracer 1.0 binary not detected"
)


def _cli_engine(converter: Converter) -> TracingEngine:
    for engine in converter.engines:
        if engine.capabilities.origin == "cli":
            return engine
    raise AssertionError("no CLI engine available")


def _assert_valid_svg(text: str) -> None:
    root = ET.fromstring(text)
    assert root.tag.rsplit("}", 1)[-1] == "svg"
    assert any(el.tag.rsplit("}", 1)[-1] == "path" for el in root.iter())


@requires_cli_engine
def test_cli_engine_traces_photo() -> None:
    engine = _cli_engine(Converter())
    svg = engine.trace(
        image_bytes=(FIXTURES / "fixture_photo.jpg").read_bytes(),
        image_format="jpg",
        config=ConversionConfig(),
    )
    _assert_valid_svg(svg)


@requires_cli_engine
def test_default_converter_prefers_cli_engine() -> None:
    caps = Converter().capabilities
    assert caps.origin == "cli"
    assert caps.version.split(".")[0] == "1"


@requires_cli_engine
def test_simplify_runs_via_default_converter(tmp_path: Path) -> None:
    """A 1.0-only option works out of the box once the binary is detected."""
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_photo.jpg",
        tmp_path / "simplified.svg",
        config=ConversionConfig(simplify=1.5),
        output=OutputConfig(overwrite=True),
    )
    assert result.status == "success"
    assert result.engine_version == _cli_engine(converter).capabilities.version


def test_smart_fallback_to_python_engine(tmp_path: Path) -> None:
    """corner_threshold is 0.6-only, so the Python engine must handle it."""
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_photo.jpg",
        tmp_path / "fallback.svg",
        config=ConversionConfig(corner_threshold=90.0),
        output=OutputConfig(overwrite=True),
    )
    assert result.status == "success"
    if HAS_CLI_ENGINE:
        assert result.engine_version != _cli_engine(converter).capabilities.version


def test_info_payload_lists_all_engines() -> None:
    context = Converter()
    info = build_info_payload(
        context.capabilities,
        engines=[engine.capabilities for engine in context.engines],
    )
    origins = {entry["origin"] for entry in info["engines"]}
    assert "python" in origins
    if HAS_CLI_ENGINE:
        assert origins == {"cli", "python"}
        assert info["engines"][0]["origin"] == "cli"
        assert info["engines"][0]["binary"]
    # Option gating is on the union: corner_threshold + simplify are both
    # available whenever both engines are installed.
    by_name = {field["name"]: field for field in info["conversion_fields"]}
    if HAS_CLI_ENGINE:
        assert by_name["simplify"]["unavailable"] is False
    assert by_name["corner_threshold"]["unavailable"] is False
