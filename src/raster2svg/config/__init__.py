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
]
