"""Pydantic configuration models (PRD section 20).

Every engine-facing field is optional. ``None`` means "let the installed
tracing engine use its own default" (PRD section 33, rule 6), so the same
model stays valid across VTracer releases with different feature sets.
"""

from __future__ import annotations

import re
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from raster2svg.core.errors import ConfigError

_HEX_COLOR = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


class Clustering(StrEnum):
    """Region clustering strategy (PRD section 9.2)."""

    COLOR_CLUSTER = "color-cluster"
    BW = "bw"
    WATERSHED = "watershed"


class Hierarchical(StrEnum):
    """Layering mode (PRD section 9.3)."""

    STACKED = "stacked"
    CUTOUT = "cutout"


class CurveMode(StrEnum):
    """Curve fitting mode (PRD section 9.4)."""

    PIXEL = "pixel"
    POLYGON = "polygon"
    SPLINE = "spline"


class PresetName(StrEnum):
    """Built-in presets (PRD section 16.1).

    Kept for API compatibility; the ``preset`` field itself accepts any
    built-in or user-saved custom preset name (PRD 16.4).
    """

    BW = "bw"
    PHOTO = "photo"
    POSTER = "poster"


def _config_error_from_validation(error: ValidationError) -> ConfigError:
    lines = []
    for prob in error.errors():
        location = ".".join(str(part) for part in prob["loc"])
        lines.append(f"{location}: {prob['msg']}")
    return ConfigError("Invalid configuration value(s).", hint="\n".join(lines))


class ConversionConfig(BaseModel):
    """Canonical tracing settings (PRD section 20.1)."""

    model_config = ConfigDict(extra="forbid")

    # str (not PresetName) so user-saved custom presets are valid (PRD 16.4);
    # existence is checked by the resolver, which reports all known presets.
    preset: str | None = None
    clustering: Clustering | None = None
    hierarchical: Hierarchical | None = None
    mode: CurveMode | None = None

    filter_speckle: int | None = Field(default=None, ge=1, le=100)
    color_precision: int | None = Field(default=None, ge=1, le=8)
    layer_difference: int | None = Field(default=None, ge=1, le=255)
    corner_threshold: float | None = Field(default=None, ge=0, le=180)
    length_threshold: float | None = Field(default=None, ge=3.5, le=10)
    max_iterations: int | None = Field(default=None, ge=1, le=100)
    splice_threshold: float | None = Field(default=None, ge=0, le=180)
    path_precision: int | None = Field(default=None, ge=0, le=8)

    # Features that may be unsupported depending on the installed engine
    # version; see raster2svg.engines.vtracer_engine and `engine capabilities`.
    simplify: float | None = Field(default=None, gt=0, le=10)
    palette: list[str] | None = None
    palette_file: Path | None = None
    max_colors: int | None = Field(default=None, ge=1, le=65536)
    optimize: int | None = Field(default=None, ge=0, le=2)

    binary_threshold: int | None = Field(default=None, ge=0, le=255)
    adaptive: bool | None = None
    adaptive_window: int | None = Field(default=None, ge=3)
    adaptive_t: int | None = Field(default=None, ge=0, le=255)
    watershed_detail: int | None = Field(default=None, ge=0, le=255)

    @field_validator("palette")
    @classmethod
    def _validate_palette(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return value
        for color in value:
            if not _HEX_COLOR.match(color):
                raise ValueError(f"invalid hex color {color!r}; expected #rgb or #rrggbb")
        # PRD 9.14: remove duplicates, preserving order.
        return list(dict.fromkeys(value))

    @model_validator(mode="after")
    def _validate_combinations(self) -> ConversionConfig:
        if self.palette_file is not None and self.palette is not None:
            raise ValueError("set either 'palette' or 'palette_file', not both")
        return self

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ConversionConfig:
        """Validate a plain dict, translating errors into ConfigError."""
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise _config_error_from_validation(exc) from exc


class OutputConfig(BaseModel):
    """Output behavior (PRD sections 5.4 and 14)."""

    model_config = ConfigDict(extra="forbid")

    overwrite: bool = False
    validate_svg: bool = True
    create_directories: bool = True


class AppConfig(BaseModel):
    """Root configuration object (PRD section 20)."""

    model_config = ConfigDict(extra="forbid")

    conversion: ConversionConfig = Field(default_factory=ConversionConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AppConfig:
        try:
            return cls.model_validate(data)
        except ValidationError as exc:
            raise _config_error_from_validation(exc) from exc
