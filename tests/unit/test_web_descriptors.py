"""Tests for the web /api/info option descriptors."""

from __future__ import annotations

from typing import Any

from raster2svg.core.capabilities import EngineCapabilities, detect_vtracer_capabilities
from raster2svg.web.server import build_info_payload

#: Conversion options that require VTracer 1.0.
ADVANCED = {
    "simplify",
    "palette",
    "max_colors",
    "optimize",
    "binary_threshold",
    "adaptive",
    "adaptive_window",
    "adaptive_t",
    "watershed_detail",
}

#: Every parameter a VTracer 1.0 would expose.
ALL_PARAMS = frozenset(
    {
        "colormode",
        "hierarchical",
        "mode",
        "filter_speckle",
        "color_precision",
        "layer_difference",
        "corner_threshold",
        "length_threshold",
        "max_iterations",
        "splice_threshold",
        "path_precision",
        "simplify",
        "palette",
        "max_colors",
        "optimize",
        "binary_threshold",
        "adaptive",
        "adaptive_window",
        "adaptive_t",
        "watershed_detail",
    }
)


def _by_name(fields: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {f["name"]: f for f in fields}


def test_info_payload_shape() -> None:
    info = build_info_payload(detect_vtracer_capabilities())
    for key in (
        "version",
        "engine",
        "supported_params",
        "available_advanced",
        "unavailable_advanced",
        "presets",
        "conversion_fields",
        "preprocess_fields",
        "postprocess_fields",
    ):
        assert key in info
    assert info["engine"]["name"] == "vtracer"
    assert {"bw", "photo", "poster"} <= set(info["presets"])


def test_base_fields_are_always_available() -> None:
    conv = _by_name(build_info_payload(detect_vtracer_capabilities())["conversion_fields"])
    for name in ("clustering", "hierarchical", "mode", "filter_speckle", "color_precision"):
        assert conv[name]["unavailable"] is False


def test_advanced_fields_mirror_engine_support() -> None:
    caps = detect_vtracer_capabilities()
    conv = _by_name(build_info_payload(caps)["conversion_fields"])
    for name in sorted(ADVANCED):
        assert conv[name]["unavailable"] is (not caps.supports(name))


def test_a_fully_capable_engine_marks_everything_available() -> None:
    caps = EngineCapabilities(name="vtracer", version="1.0", supported_params=ALL_PARAMS)
    conv = _by_name(build_info_payload(caps)["conversion_fields"])
    for name, field in conv.items():
        assert field["unavailable"] is False, name


def test_unavailable_fields_carry_a_hint() -> None:
    caps = detect_vtracer_capabilities()
    fields = build_info_payload(caps)["conversion_fields"]
    unavailable = [f for f in fields if f["unavailable"]]
    for field in unavailable:
        assert "VTracer 1.0" in field["unavailable_hint"]


def test_pre_max_colors_is_the_starred_preprocess_option() -> None:
    pre = _by_name(build_info_payload(detect_vtracer_capabilities())["preprocess_fields"])
    field = pre["pre_max_colors"]
    assert field["star"] is True
    assert field["unavailable"] is False
    assert field["min"] == 1
    assert field["max"] == 256


def test_invert_is_a_boolean_postprocess_option() -> None:
    post = _by_name(build_info_payload(detect_vtracer_capabilities())["postprocess_fields"])
    field = post["invert"]
    assert field["kind"] == "bool"
    assert field["default"] is False
    assert field["unavailable"] is False
