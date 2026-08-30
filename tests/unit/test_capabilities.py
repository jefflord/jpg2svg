"""Unit tests for engine capabilities and capability-driven help (PRD 21)."""

from __future__ import annotations

import pytest

import raster2svg.cli.options as options
from raster2svg.cli.options import _option_help
from raster2svg.core.capabilities import (
    ENGINE_DEPENDENT_OPTIONS,
    EngineCapabilities,
    detect_vtracer_capabilities,
    split_engine_dependent,
)


def _caps(params: set[str]) -> EngineCapabilities:
    return EngineCapabilities(
        name="vtracer", version="0.0.0", supported_params=frozenset(params)
    )


def test_split_with_full_support() -> None:
    all_params = {param for _, param in ENGINE_DEPENDENT_OPTIONS}
    available, unavailable = split_engine_dependent(_caps(all_params))
    assert unavailable == []
    assert len(available) == len(ENGINE_DEPENDENT_OPTIONS)


def test_split_with_no_support() -> None:
    available, unavailable = split_engine_dependent(_caps(set()))
    assert available == []
    assert len(unavailable) == len(ENGINE_DEPENDENT_OPTIONS)


def test_split_partial_shares_palette_param() -> None:
    available, unavailable = split_engine_dependent(_caps({"simplify", "palette"}))
    assert {"--simplify", "--palette", "--palette-file"} <= set(available)
    assert "--max-colors" in unavailable


def test_split_partitions_all_options_for_installed_engine() -> None:
    caps = detect_vtracer_capabilities()
    available, unavailable = split_engine_dependent(caps)
    all_options = [option for option, _ in ENGINE_DEPENDENT_OPTIONS]
    assert sorted(available + unavailable) == sorted(all_options)
    assert not (set(available) & set(unavailable))


def test_option_help_marks_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(options, "_ENGINE", _caps(set()))
    text = _option_help("Quantize to N colors.", requires="max_colors")
    assert "UNAVAILABLE" in text
    assert "VTracer 1.0" in text


def test_option_help_omits_marker_when_supported(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(options, "_ENGINE", _caps({"max_colors"}))
    text = _option_help("Quantize to N colors.", requires="max_colors")
    assert "UNAVAILABLE" not in text


def test_option_help_without_requirement_is_never_marked() -> None:
    text = _option_help("Bits per RGB channel, 1-8.")
    assert "UNAVAILABLE" not in text
