"""Unit tests: built-in and custom presets (PRD section 16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg.config.models import ConversionConfig, CurveMode
from raster2svg.config.presets import (
    PRESETS,
    UnknownPresetError,
    available_presets,
    custom_presets_dir,
    get_preset,
    preset_source,
    resolve_preset,
    save_custom_preset,
)
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.core.errors import ConfigError


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(tmp_path / "data"))


def test_builtins_are_the_prd_required_set() -> None:
    assert set(PRESETS) == {"bw", "photo", "poster"}


def test_available_starts_empty_of_customs() -> None:
    assert available_presets() == ["bw", "photo", "poster"]


def test_preset_source_and_unknown() -> None:
    assert preset_source("photo") == "builtin"
    with pytest.raises(UnknownPresetError):
        preset_source("nope")


def test_resolve_preset_builtin() -> None:
    values = resolve_preset("poster")
    assert values["hierarchical"] == "cutout"
    assert values["mode"] == "spline"


def test_save_and_resolve_custom_preset() -> None:
    path = save_custom_preset("my-logo", {"mode": "polygon", "max_colors": 4})
    assert path.exists()
    names = available_presets()
    assert names[:3] == ["bw", "photo", "poster"]
    assert names[-1] == "my-logo"
    assert preset_source("my-logo") == "custom"
    values = resolve_preset("my-logo")
    assert values["mode"] == "polygon"
    assert values["max_colors"] == 4


def test_custom_preset_base_chain() -> None:
    save_custom_preset("line-art", {"base": "photo", "filter_speckle": 1})
    values = resolve_preset("line-art")
    # Base value inherited (photo does not set filter_speckle):
    assert values["clustering"] == "color-cluster"
    assert values["filter_speckle"] == 1


def test_custom_preset_overrides_conflicting_base_value() -> None:
    # photo sets mode=spline; the derived preset must win with mode=polygon.
    save_custom_preset("logo-variant", {"base": "photo", "mode": "polygon"})
    values = resolve_preset("logo-variant")
    assert values["mode"] == "polygon"
    # Non-conflicting base values are still inherited:
    assert values["clustering"] == "color-cluster"
    assert values["hierarchical"] == "stacked"
    # Base key itself is not a conversion setting:
    assert "base" not in values


def test_custom_preset_chain_of_customs() -> None:
    save_custom_preset("flat", {"mode": "polygon"})
    save_custom_preset("flat-lite", {"base": "flat", "filter_speckle": 2})
    values = resolve_preset("flat-lite")
    assert values["mode"] == "polygon"
    assert values["filter_speckle"] == 2


def test_base_cycle_is_rejected() -> None:
    # save_custom_preset validates the base exists, so a cycle can only exist
    # via hand-edited files. Simulate that by writing both files directly.
    directory = custom_presets_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "a.toml").write_text('base = "b"\nmode = "pixel"\n', encoding="utf-8")
    (directory / "b.toml").write_text('base = "a"\nfilter_speckle = 3\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="cycle"):
        resolve_preset("a")


def test_save_rejects_builtin_name_collision() -> None:
    with pytest.raises(ConfigError, match="shadow"):
        save_custom_preset("photo", {"mode": "pixel"})


def test_save_rejects_invalid_name() -> None:
    with pytest.raises(ConfigError, match="Invalid preset name"):
        save_custom_preset("My Logo!", {"mode": "pixel"})


def test_save_rejects_invalid_values() -> None:
    with pytest.raises(ConfigError, match="invalid conversion setting") as exc:
        save_custom_preset("bad", {"color_precision": 99})
    assert "color_precision" in (exc.value.hint or "")


def test_save_rejects_empty_values() -> None:
    with pytest.raises(ConfigError, match="no values"):
        save_custom_preset("empty", {})


def test_save_rejects_unknown_base() -> None:
    with pytest.raises(UnknownPresetError):
        save_custom_preset("orphan", {"base": "does-not-exist", "mode": "pixel"})


def test_saved_file_round_trips() -> None:
    save_custom_preset("roundtrip", {"mode": "spline", "palette": ["#112233", "#aabbcc"]})
    data = get_preset("roundtrip")
    assert data["mode"] == "spline"
    assert data["palette"] == ["#112233", "#aabbcc"]


def test_saved_preset_values_stay_validated() -> None:
    save_custom_preset("validated", {"mode": "spline", "color_precision": 5})
    config = ConversionConfig.model_validate(resolve_preset("validated"))
    assert config.mode is CurveMode.SPLINE
    assert config.color_precision == 5


def test_resolver_applies_custom_preset() -> None:
    save_custom_preset("tiny", {"max_colors": 2, "mode": "polygon"})
    config = resolve_conversion_config(preset="tiny")
    assert config.max_colors == 2
    assert config.mode is CurveMode.POLYGON
    assert config.preset == "tiny"


def test_explicit_values_override_custom_preset() -> None:
    save_custom_preset("tiny", {"max_colors": 2})
    config = resolve_conversion_config(preset="tiny", cli_values={"max_colors": 8})
    assert config.max_colors == 8


def test_unknown_preset_error_lists_customs() -> None:
    save_custom_preset("my-logo", {"mode": "polygon"})
    with pytest.raises(UnknownPresetError) as exc:
        get_preset("ghost")
    assert "my-logo" in exc.value.available
