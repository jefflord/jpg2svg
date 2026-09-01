"""Unit tests: built-in and custom presets (PRD section 16)."""

from __future__ import annotations

from pathlib import Path

import pytest

from raster2svg.config.models import ConversionConfig, CurveMode
from raster2svg.config.presets import (
    PRESETS,
    Preset,
    UnknownPresetError,
    available_presets,
    custom_presets_dir,
    get_preset,
    preset_details,
    preset_source,
    resolve_preset,
    save_custom_preset,
)
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.core.errors import ConfigError

BUILTIN_NAMES = {
    "bw",
    "photo",
    "poster",
    "flat-illustration",
    "clip-art",
    "clip-art-soft",
    "clip-art-strong",
    "comic",
    "line-art",
    "line-art-inverted",
    "silhouette",
    "silhouette-inverted",
    "logo-cleanup",
    "pixel-art",
}


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RASTER2SVG_DATA_DIR", str(tmp_path / "data"))


def test_builtins_include_the_prd_required_set() -> None:
    assert {"bw", "photo", "poster"} <= set(PRESETS)
    assert set(PRESETS) == BUILTIN_NAMES


def test_available_starts_empty_of_customs() -> None:
    assert available_presets() == sorted(BUILTIN_NAMES)


def test_preset_source_and_unknown() -> None:
    assert preset_source("photo") == "builtin"
    assert preset_source("pixel-art") == "builtin"
    with pytest.raises(UnknownPresetError):
        preset_source("nope")


def test_resolve_preset_builtin_sections() -> None:
    preset = resolve_preset("poster")
    assert isinstance(preset, Preset)
    assert preset.source == "builtin"
    assert preset.conversion["hierarchical"] == "cutout"
    assert preset.conversion["mode"] == "spline"
    assert preset.preprocess["denoise"] is True
    assert preset.description
    assert preset.recommended_for
    assert preset.base is None


def test_every_builtin_has_description_and_recommendations() -> None:
    for name in PRESETS:
        preset = get_preset(name)
        assert preset.description, name
        assert preset.recommended_for, name


def test_save_and_resolve_custom_preset() -> None:
    path = save_custom_preset("my-logo", {"mode": "polygon", "max_colors": 4})
    assert path.exists()
    names = available_presets()
    assert names[: len(BUILTIN_NAMES)] == sorted(BUILTIN_NAMES)
    assert names[-1] == "my-logo"
    assert preset_source("my-logo") == "custom"
    values = resolve_preset("my-logo")
    assert values.conversion["mode"] == "polygon"
    assert values.conversion["max_colors"] == 4
    assert values.preprocess == {}


def test_save_structured_preset_with_preprocess() -> None:
    path = save_custom_preset(
        "my-clip",
        {
            "description": "My clip art",
            "conversion": {"mode": "spline", "filter_speckle": 3},
            "preprocess": {"denoise": True, "posterize": 5},
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "[conversion]" in text
    assert "[preprocess]" in text
    assert "denoise = true" in text

    preset = resolve_preset("my-clip")
    assert preset.conversion == {"mode": "spline", "filter_speckle": 3}
    assert preset.preprocess == {"denoise": True, "posterize": 5}
    assert preset.description == "My clip art"


def test_inverted_presets_resolve_invert_and_inherit_base() -> None:
    for inverted, base in (
        ("line-art-inverted", "line-art"),
        ("silhouette-inverted", "silhouette"),
    ):
        preset = resolve_preset(inverted)
        # The whole point of the preset: it flips the output.
        assert preset.postprocess == {"invert": True}
        # Everything else is inherited from the base preset it derives from.
        assert preset.conversion == resolve_preset(base).conversion
        assert preset.preprocess == resolve_preset(base).preprocess
        assert preset.description
        assert preset.recommended_for


def test_save_structured_preset_with_postprocess() -> None:
    path = save_custom_preset(
        "my-invert",
        {
            "description": "Negative output",
            "conversion": {"mode": "spline"},
            "postprocess": {"invert": True},
        },
    )
    text = path.read_text(encoding="utf-8")
    assert "[conversion]" in text
    assert "[postprocess]" in text
    assert "invert = true" in text

    preset = resolve_preset("my-invert")
    assert preset.conversion == {"mode": "spline"}
    assert preset.preprocess == {}
    assert preset.postprocess == {"invert": True}
    assert preset.description == "Negative output"


def test_custom_preset_postprocess_override_wins_over_base() -> None:
    # line-art-inverted flips the output; a derived preset may turn it back off.
    save_custom_preset(
        "line-art-normal",
        {
            "base": "line-art-inverted",
            "postprocess": {"invert": False},
        },
    )
    preset = resolve_preset("line-art-normal")
    assert preset.postprocess == {"invert": False}
    # The base's conversion values are still inherited:
    assert preset.conversion == resolve_preset("line-art").conversion


def test_custom_preset_base_chain() -> None:
    save_custom_preset("my-line", {"base": "photo", "filter_speckle": 1})
    preset = resolve_preset("my-line")
    # Base value inherited (photo does not set filter_speckle):
    assert preset.conversion["clustering"] == "color-cluster"
    assert preset.conversion["filter_speckle"] == 1
    # The photo preset's preprocess base is inherited too:
    assert preset.preprocess["denoise"] is True


def test_custom_preset_overrides_conflicting_base_value() -> None:
    # photo sets mode=spline; the derived preset must win with mode=polygon.
    save_custom_preset("logo-variant", {"base": "photo", "mode": "polygon"})
    preset = resolve_preset("logo-variant")
    assert preset.conversion["mode"] == "polygon"
    # Non-conflicting base values are still inherited:
    assert preset.conversion["clustering"] == "color-cluster"
    assert preset.conversion["hierarchical"] == "stacked"
    # Metadata comes from the base (derived has none of its own):
    assert preset.description
    assert "photos" in preset.recommended_for
    # Base key itself is not a conversion setting:
    assert "base" not in preset.conversion
    assert preset.base is None  # resolved result is the fully merged preset


def test_custom_preset_preprocess_override_wins_over_base() -> None:
    save_custom_preset(
        "clean-clip",
        {
            "base": "clip-art",
            "preprocess": {"denoise": True, "blur": False},
        },
    )
    preset = resolve_preset("clean-clip")
    assert preset.preprocess["blur"] is False
    # clip-art's other preprocess values are inherited:
    assert preset.preprocess["posterize"] == 5
    assert preset.preprocess["autocontrast"] is True


def test_custom_preset_chain_of_customs() -> None:
    save_custom_preset("flat", {"mode": "polygon"})
    save_custom_preset("flat-lite", {"base": "flat", "filter_speckle": 2})
    preset = resolve_preset("flat-lite")
    assert preset.conversion["mode"] == "polygon"
    assert preset.conversion["filter_speckle"] == 2


def test_base_cycle_is_rejected() -> None:
    # save_custom_preset validates the base exists, so a cycle can only exist
    # via hand-edited files. Simulate that by writing both files directly.
    directory = custom_presets_dir()
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "a.toml").write_text('base = "b"\nmode = "pixel"\n', encoding="utf-8")
    (directory / "b.toml").write_text('base = "a"\nfilter_speckle = 3\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="cycle"):
        resolve_preset("a")


def test_base_chain_depth_is_rejected() -> None:
    directory = custom_presets_dir()
    directory.mkdir(parents=True, exist_ok=True)
    # A chain of nine presets exceeds the allowed depth of eight.
    for index in range(9):
        base = f'base = "p{index + 1}"\n' if index < 8 else ""
        (directory / f"p{index}.toml").write_text(f'{base}mode = "pixel"\n', encoding="utf-8")
    with pytest.raises(ConfigError, match="too deep"):
        resolve_preset("p0")


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


def test_save_rejects_invalid_preprocess_values() -> None:
    with pytest.raises(ConfigError, match="invalid preprocess setting") as exc:
        save_custom_preset("bad-pre", {"preprocess": {"posterize": 32}})
    assert "posterize" in (exc.value.hint or "")


def test_save_rejects_invalid_postprocess_values() -> None:
    with pytest.raises(ConfigError, match="invalid postprocess setting") as exc:
        save_custom_preset("bad-post", {"postprocess": {"invert": "not-a-bool"}})
    assert "invert" in (exc.value.hint or "")


def test_save_rejects_mixed_flat_and_section_values() -> None:
    with pytest.raises(ConfigError, match="mixes sectioned and flat"):
        save_custom_preset("mixed", {"mode": "pixel", "conversion": {"optimize": 1}})


def test_save_rejects_empty_values() -> None:
    with pytest.raises(ConfigError, match="no values"):
        save_custom_preset("empty", {})


def test_save_rejects_unknown_base() -> None:
    with pytest.raises(UnknownPresetError):
        save_custom_preset("orphan", {"base": "does-not-exist", "mode": "pixel"})


def test_saved_file_round_trips() -> None:
    save_custom_preset("roundtrip", {"mode": "spline", "palette": ["#112233", "#aabbcc"]})
    preset = get_preset("roundtrip")
    assert preset.conversion["mode"] == "spline"
    assert preset.conversion["palette"] == ["#112233", "#aabbcc"]


def test_saved_preset_values_stay_validated() -> None:
    save_custom_preset("validated", {"mode": "spline", "color_precision": 5})
    resolved = resolve_preset("validated")
    config = ConversionConfig(**resolved.conversion)
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
    assert exc.value.name == "ghost"


def test_preset_details_covers_all_presets() -> None:
    save_custom_preset("listed", {"mode": "polygon"})
    details = preset_details()
    assert set(details) == set(available_presets())
    assert details["photo"]["source"] == "builtin"
    assert details["photo"]["description"]
    assert details["listed"]["source"] == "custom"
