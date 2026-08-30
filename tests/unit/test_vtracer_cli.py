"""Unit tests for the VTracer 1.0 CLI adapter (pure parts, no binary needed)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg.config.models import Clustering, ConversionConfig, CurveMode, Hierarchical
from raster2svg.core.capabilities import EngineCapabilities
from raster2svg.core.errors import UnsupportedFeatureError
from raster2svg.engines.vtracer_cli import (
    VTRACER1_PARAMS,
    _input_suffix,
    build_cli_argv,
    parse_vtracer_version,
)

FULL_CAPS = EngineCapabilities(
    name="vtracer",
    version="1.0",
    supported_params=VTRACER1_PARAMS,
    origin="cli",
)


def _has_pair(argv: list[str], flag: str, value: str) -> bool:
    index = argv.index(flag) if flag in argv else -1
    return index != -1 and index + 1 < len(argv) and argv[index + 1] == value


class TestParseVtracerVersion:
    def test_parses_alpha_version(self) -> None:
        assert parse_vtracer_version("vtracer 1.0.0-alpha.4 (commit abc)") == "1.0.0-alpha.4"

    def test_parses_plain_version(self) -> None:
        assert parse_vtracer_version("vtracer 1.2.3") == "1.2.3"

    def test_rejects_zero_major(self) -> None:
        assert parse_vtracer_version("vtracer 0.6.15") is None

    def test_rejects_garbage(self) -> None:
        assert parse_vtracer_version("not a version") is None
        assert parse_vtracer_version("") is None


class TestBuildCliArgv:
    def test_full_flag_mapping(self) -> None:
        config = ConversionConfig(
            clustering=Clustering.COLOR_CLUSTER,
            hierarchical=Hierarchical.CUTOUT,
            mode=CurveMode.SPLINE,
            filter_speckle=5,
            color_precision=4,
            layer_difference=16,
            path_precision=5,
            simplify=1.5,
            palette=["#111111", "#eeeeee"],
            max_colors=16,
            optimize=2,
            binary_threshold=128,
            adaptive_window=51,
            adaptive_t=15,
            watershed_detail=8,
        )
        argv = build_cli_argv(FULL_CAPS, config)
        for flag, value in (
            ("--clustering", "color-cluster"),
            ("--hierarchical", "cutout"),
            ("-m", "spline"),
            ("-f", "5"),
            ("-p", "4"),
            ("-g", "16"),
            ("--path-precision", "5"),
            ("--simplify", "1.5"),
            ("--palette", "#111111,#eeeeee"),
            ("--max-colors", "16"),
            ("--optimize", "2"),
            ("--threshold", "128"),
            ("--adaptive-window", "51"),
            ("--adaptive-t", "15"),
            ("--watershed-detail", "8"),
        ):
            assert _has_pair(argv, flag, value), f"{flag} {value} missing from {argv}"

    def test_adaptive_is_a_valueless_flag(self) -> None:
        config = ConversionConfig(clustering=Clustering.BW, adaptive=True)
        argv = build_cli_argv(FULL_CAPS, config)
        assert "--adaptive" in argv
        assert _has_pair(argv, "--clustering", "bw")

    def test_empty_config_is_empty_argv(self) -> None:
        assert build_cli_argv(FULL_CAPS, ConversionConfig()) == []

    def test_unsupported_field_raises(self) -> None:
        config = ConversionConfig(corner_threshold=90.0)
        with pytest.raises(UnsupportedFeatureError, match="corner_threshold"):
            build_cli_argv(FULL_CAPS, config)

    def test_palette_file_flag(self) -> None:
        config = ConversionConfig(palette_file=Path("palette.txt"))
        assert build_cli_argv(FULL_CAPS, config) == ["--palette-file", "palette.txt"]


class TestInputSuffix:
    def test_jpeg(self) -> None:
        assert _input_suffix("jpeg") == ".jpg"

    def test_tiff(self) -> None:
        assert _input_suffix("TIFF") == ".tif"

    def test_png(self) -> None:
        assert _input_suffix("png") == ".png"

    def test_unknown_falls_back_to_png(self) -> None:
        assert _input_suffix(None) == ".png"
        assert _input_suffix("weird") == ".weird"
