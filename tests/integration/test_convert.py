"""Integration tests: real conversions with the installed VTracer engine."""

from __future__ import annotations

import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from raster2svg import Converter
from raster2svg.config.models import (
    Clustering,
    ConversionConfig,
    CurveMode,
    OutputConfig,
)
from raster2svg.core.errors import (
    InputError,
    OutputError,
    UnsupportedFeatureError,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"

ALLOWED_MODES = (CurveMode.PIXEL, CurveMode.POLYGON, CurveMode.SPLINE)


def _assert_valid_svg(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.strip(), "SVG output is empty"
    root = ET.fromstring(text)
    assert root.tag.rsplit("}", 1)[-1] == "svg"
    assert len(list(root.iter())) > 1, "SVG contains no content"


def test_jpg_to_svg(tmp_path: Path) -> None:
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_photo.jpg",
        tmp_path / "photo.svg",
        output=OutputConfig(overwrite=True),
    )
    assert result.status == "success"
    assert result.input_width == 96
    assert result.input_height == 96
    assert result.input_format == "JPEG"
    assert result.output_bytes and result.output_bytes > 0
    _assert_valid_svg(tmp_path / "photo.svg")
    text = (tmp_path / "photo.svg").read_text(encoding="utf-8")
    assert "<path" in text


def test_png_with_alpha(tmp_path: Path) -> None:
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_logo.png",
        tmp_path / "logo.svg",
        output=OutputConfig(overwrite=True),
    )
    assert result.status == "success"
    _assert_valid_svg(tmp_path / "logo.svg")


def test_config_preset_is_applied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A saved custom preset named in ConversionConfig is applied (PRD 16.4, 23)."""
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(tmp_path / "data"))
    from raster2svg.config.presets import save_custom_preset

    save_custom_preset("my-logo", {"mode": "polygon", "filter_speckle": 5})
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_photo.jpg",
        tmp_path / "custom.svg",
        config=ConversionConfig(preset="my-logo"),
        output=OutputConfig(overwrite=True),
    )
    assert result.status == "success"
    assert result.config["preset"] == "my-logo"
    assert result.config["mode"] == "polygon"
    assert result.config["filter_speckle"] == 5
    _assert_valid_svg(tmp_path / "custom.svg")


def test_bw_clustering(tmp_path: Path) -> None:
    converter = Converter()
    config = ConversionConfig(clustering=Clustering.BW, mode=CurveMode.SPLINE)
    converter.convert(
        FIXTURES / "fixture_bw.png",
        tmp_path / "bw.svg",
        config=config,
        output=OutputConfig(overwrite=True),
    )
    _assert_valid_svg(tmp_path / "bw.svg")


def test_all_curve_modes_run(tmp_path: Path) -> None:
    converter = Converter()
    for mode in sorted(ALLOWED_MODES):
        target = tmp_path / f"mode_{mode.value}.svg"
        config = ConversionConfig(mode=mode)
        converter.convert(
            FIXTURES / "fixture_photo.jpg",
            target,
            config=config,
            output=OutputConfig(overwrite=True),
        )
        _assert_valid_svg(target)


def test_default_output_naming(tmp_path: Path) -> None:
    image = tmp_path / "photo.jpg"
    shutil.copyfile(FIXTURES / "fixture_photo.jpg", image)
    converter = Converter()
    result = converter.convert(image, output=OutputConfig(overwrite=True))
    assert result.output_path == tmp_path / "photo.svg"
    assert (tmp_path / "photo.svg").exists()


def test_overwrite_protection(tmp_path: Path) -> None:
    target = tmp_path / "out.svg"
    target.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    converter = Converter()
    with pytest.raises(OutputError, match="already exists"):
        converter.convert(FIXTURES / "fixture_photo.jpg", target)
    assert "2000/svg" in target.read_text(encoding="utf-8"), "must not overwrite"


def test_overwrite_flag_replaces_file(tmp_path: Path) -> None:
    target = tmp_path / "out.svg"
    target.write_text("placeholder", encoding="utf-8")
    converter = Converter()
    converter.convert(
        FIXTURES / "fixture_photo.jpg",
        target,
        output=OutputConfig(overwrite=True),
    )
    _assert_valid_svg(target)


def test_create_directories_and_no_mkdir(tmp_path: Path) -> None:
    nested = tmp_path / "a" / "b" / "out.svg"
    converter = Converter()
    converter.convert(
        FIXTURES / "fixture_photo.jpg",
        nested,
        output=OutputConfig(overwrite=True),
    )
    assert nested.exists()

    nested2 = tmp_path / "c" / "d" / "out.svg"
    with pytest.raises(OutputError, match="does not exist"):
        converter.convert(
            FIXTURES / "fixture_photo.jpg",
            nested2,
            output=OutputConfig(overwrite=True, create_directories=False),
        )


def test_dry_run_writes_nothing(tmp_path: Path) -> None:
    target = tmp_path / "out.svg"
    converter = Converter()
    result = converter.convert(
        FIXTURES / "fixture_photo.jpg",
        target,
        output=OutputConfig(overwrite=True),
        dry_run=True,
    )
    assert result.status == "dry-run"
    assert not target.exists()


def test_dry_run_still_checks_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "out.svg"
    target.write_text("existing", encoding="utf-8")
    converter = Converter()
    with pytest.raises(OutputError, match="already exists"):
        converter.convert(FIXTURES / "fixture_photo.jpg", target, dry_run=True)


def test_corrupt_image_fails_cleanly(tmp_path: Path) -> None:
    converter = Converter()
    with pytest.raises(InputError, match="Cannot decode"):
        converter.convert(FIXTURES / "fixture_corrupt.jpg", tmp_path / "out.svg")


def test_unsupported_feature_is_not_silently_ignored(tmp_path: Path) -> None:
    converter = Converter()
    config = ConversionConfig(simplify=1.5)
    with pytest.raises(UnsupportedFeatureError, match="simplify"):
        converter.convert(
            FIXTURES / "fixture_photo.jpg",
            tmp_path / "out.svg",
            config=config,
            output=OutputConfig(overwrite=True),
        )
