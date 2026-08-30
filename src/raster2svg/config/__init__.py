"""Configuration models, presets, config-file loading, and precedence resolution."""

from raster2svg.config.loader import load_config_file
from raster2svg.config.models import (
    AppConfig,
    Clustering,
    ConversionConfig,
    CurveMode,
    Hierarchical,
    OutputConfig,
    PresetName,
)
from raster2svg.config.presets import (
    PRESETS,
    UnknownPresetError,
    available_presets,
    get_preset,
    list_custom_presets,
    preset_source,
    resolve_preset,
    save_custom_preset,
)
from raster2svg.config.resolver import resolve_conversion_config
from raster2svg.config.user_config import (
    find_user_config_file,
    load_user_config,
    user_config_dir,
)

__all__ = [
    "AppConfig",
    "Clustering",
    "ConversionConfig",
    "CurveMode",
    "Hierarchical",
    "OutputConfig",
    "PRESETS",
    "PresetName",
    "UnknownPresetError",
    "available_presets",
    "get_preset",
    "list_custom_presets",
    "load_config_file",
    "preset_source",
    "resolve_conversion_config",
    "resolve_preset",
    "save_custom_preset",
    "user_config_dir",
    "find_user_config_file",
    "load_user_config",
]
