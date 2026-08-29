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
from raster2svg.config.presets import PRESETS, get_preset
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
    "get_preset",
    "load_config_file",
    "resolve_conversion_config",
]
