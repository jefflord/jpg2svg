"""Configuration precedence resolution (PRD section 8).

Lowest to highest priority:

1. application defaults (all fields None -> engine defaults)
2. built-in preset values
3. config-file values
4. (environment variables - planned)
5. explicit command-line options
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from raster2svg.config.models import (
    Clustering,
    ConversionConfig,
    PresetName,
)
from raster2svg.config.presets import resolve_preset
from raster2svg.core.errors import ConfigError


def resolve_conversion_config(
    *,
    preset: PresetName | str | None = None,
    config_file_values: dict[str, Any] | None = None,
    cli_values: dict[str, Any] | None = None,
) -> ConversionConfig:
    """Merge preset, config-file, and CLI values into one validated config.

    The preset name follows the same precedence as every other value:
    ``preset`` argument (the CLI ``--preset``) > config-file value >
    ``cli_values``. The values of the winning preset are applied first, so
    config-file and CLI options still override them (PRD sections 8 and 9.1).
    """
    file_values = {
        key: value for key, value in (config_file_values or {}).items() if value is not None
    }
    cli = {key: value for key, value in (cli_values or {}).items() if value is not None}

    preset_name: str | None = None
    if preset is not None:
        preset_name = preset.value if isinstance(preset, PresetName) else str(preset)
    elif file_values.get("preset") is not None:
        preset_name = str(file_values["preset"])
    elif cli.get("preset") is not None:
        preset_name = str(cli["preset"])

    # UnknownPresetError (a ConfigError subclass) propagates to the caller
    # with an actionable hint; resolve_preset follows the base chain.
    base: dict[str, Any] = {}
    if preset_name is not None:
        base.update(resolve_preset(preset_name).conversion)

    base.update(file_values)
    base.update(cli)
    if preset_name is not None:
        base["preset"] = preset_name

    # PRD 9.18: --adaptive implies clustering=bw, unless the caller explicitly
    # passed a conflicting clustering on the command line.
    if cli.get("adaptive") is True:
        requested = cli.get("clustering")
        if requested is not None and str(requested) != Clustering.BW.value:
            raise ConfigError(
                "--adaptive requires --clustering bw.",
                hint="Drop --clustering (adaptive implies bw) or remove --adaptive.",
            )
        base["clustering"] = Clustering.BW.value

    config = ConversionConfig.from_dict(base)
    _materialize_palette_file(config)
    return config


def _materialize_palette_file(config: ConversionConfig) -> None:
    """Read palette_file into palette (PRD section 9.14).

    Format: one hex color per line, blank lines ignored.
    """
    if config.palette_file is None:
        return
    path = Path(config.palette_file)
    if not path.is_file():
        raise ConfigError(f"Palette file not found: {path}")
    colors = [
        line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not colors:
        raise ConfigError(
            f"Palette file contains no colors: {path}",
            hint="One hex color per line, e.g. #1b1b1b",
        )
    try:
        ConversionConfig.model_validate({"palette": colors})
    except ValidationError as exc:
        raise ConfigError(
            f"Invalid palette in {path}.",
            hint="\n".join(p["msg"] for p in exc.errors()),
        ) from exc
    config.palette = colors
    config.palette_file = None
