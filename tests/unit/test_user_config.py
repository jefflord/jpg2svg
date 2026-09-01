"""Unit tests for the user-level configuration file (PRD section 8)."""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from raster2svg.cli.app import app
from raster2svg.cli.options import resolve_cli_options
from raster2svg.config.models import (
    ConversionConfig,
    OutputConfig,
    PostprocessConfig,
    PreprocessConfig,
)
from raster2svg.config.user_config import find_user_config_file, load_user_config
from raster2svg.core.errors import ConfigError

runner = CliRunner()


def _resolve(
    preset: str | None = None,
    config_path: Path | None = None,
    cli_values: dict[str, object] | None = None,
    postprocess_kwargs: dict[str, object] | None = None,
) -> tuple[ConversionConfig, OutputConfig, PreprocessConfig, PostprocessConfig]:
    return resolve_cli_options(
        preset=preset,
        config_path=config_path,
        cli_values=cli_values or {},
        overwrite=None,
        validate_svg=None,
        no_mkdir=None,
        postprocess_kwargs=postprocess_kwargs,
    )


def test_no_user_config_file_yields_empty_sections(isolated_app_data_dir: Path) -> None:
    assert find_user_config_file() is None
    assert load_user_config() == {
        "conversion": {},
        "preprocess": {},
        "postprocess": {},
        "output": {},
    }


def test_find_user_config_file_prefers_toml(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.json").write_text("{}", encoding="utf-8")
    assert find_user_config_file() == isolated_app_data_dir / "config.json"
    (isolated_app_data_dir / "config.toml").write_text("", encoding="utf-8")
    assert find_user_config_file() == isolated_app_data_dir / "config.toml"


def test_user_config_applies_as_base_values(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\nmode = "polygon"\n', encoding="utf-8"
    )
    config, _, _, _ = _resolve()
    assert config.mode == "polygon"


def test_user_config_overrides_preset_values(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        "[conversion]\nlayer_difference = 42\n", encoding="utf-8"
    )
    config, _, _, _ = _resolve(preset="photo")
    assert config.layer_difference == 42
    assert config.mode == "spline"  # untouched preset value


def test_explicit_file_overrides_user_config_key_by_key(
    isolated_app_data_dir: Path, tmp_path: Path
) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\nmode = "polygon"\nfilter_speckle = 2\n', encoding="utf-8"
    )
    project = tmp_path / "project.toml"
    project.write_text('[conversion]\nmode = "spline"\n', encoding="utf-8")
    config, _, _, _ = _resolve(config_path=project)
    assert config.mode == "spline"  # project file wins
    assert config.filter_speckle == 2  # user value fills the gap


def test_cli_overrides_user_config(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\nmode = "polygon"\n', encoding="utf-8"
    )
    config, _, _, _ = _resolve(cli_values={"mode": "spline"})
    assert config.mode == "spline"


def test_user_config_selects_preset(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\npreset = "bw"\n', encoding="utf-8"
    )
    config, _, _, _ = _resolve()
    assert config.clustering == "bw"


def test_cli_preset_beats_user_preset(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\npreset = "bw"\n', encoding="utf-8"
    )
    config, _, _, _ = _resolve(preset="photo")
    assert config.clustering == "color-cluster"


def test_user_preprocess_section_applies(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        "[preprocess]\nsharpen = true\n", encoding="utf-8"
    )
    _, _, preprocess, _ = _resolve()
    assert preprocess.sharpen is True


def test_user_postprocess_section_applies(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        "[postprocess]\ninvert = true\n", encoding="utf-8"
    )
    _, _, _, postprocess = _resolve()
    assert postprocess.invert is True


def test_cli_invert_beats_user_postprocess(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        "[postprocess]\ninvert = true\n", encoding="utf-8"
    )
    _, _, _, postprocess = _resolve(postprocess_kwargs={"invert": False})
    assert postprocess.invert is False


def test_invalid_user_config_is_an_actionable_error(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\nmode = "polygon"\n\n[bogus]\nx = 1\n', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="Unknown top-level"):
        _resolve()


def test_config_show_includes_user_values(isolated_app_data_dir: Path) -> None:
    (isolated_app_data_dir / "config.toml").write_text(
        '[conversion]\nmode = "polygon"\n', encoding="utf-8"
    )
    result = runner.invoke(app, ["config", "show", "--format", "json"])
    assert result.exit_code == 0, result.output
    assert '"mode": "polygon"' in result.output


def test_config_show_inverted_preset_has_postprocess(isolated_app_data_dir: Path) -> None:
    args = ["config", "show", "--preset", "line-art-inverted", "--format", "json"]
    result = runner.invoke(app, args)
    assert result.exit_code == 0, result.output
    assert '"invert": true' in result.output
