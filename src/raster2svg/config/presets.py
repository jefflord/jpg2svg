"""Built-in and custom presets (PRD section 16).

Built-in presets mirror the VTracer presets available in the installed
package (PRD 16.1: ``bw``, ``photo``, ``poster``). A preset is a set of
initial values: explicit configuration-file values and CLI options always
override them (PRD 8, 9.1).

Custom presets (PRD 16.4) are user-saved TOML files stored in the
platform-appropriate application directory. A custom preset may set a
``base`` key to inherit from another preset (built-in or custom); the base
is resolved recursively, with the derived preset's values winning.

A custom preset must only contain conversion settings (plus the optional
``base`` key). Values are validated against ``ConversionConfig`` before
saving so that a saved preset can never be silently ignored (PRD 21).
"""

from __future__ import annotations

import os
import re
import tomllib
from pathlib import Path
from typing import Any

import platformdirs

from raster2svg.config.models import ConversionConfig
from raster2svg.core.errors import ConfigError

PRESET_NOTE = (
    "A preset only sets initial values; explicit config-file values and CLI "
    "options always override it."
)

# PRD 16.1: required built-ins. Values are starting points only; every field
# is overridable, so these never limit the user.
PRESETS: dict[str, dict[str, Any]] = {
    "bw": {
        "clustering": "bw",
        "hierarchical": "stacked",
        "mode": "spline",
        "filter_speckle": 2,
        "path_precision": 3,
    },
    "photo": {
        "clustering": "color-cluster",
        "hierarchical": "stacked",
        "mode": "spline",
        "color_precision": 6,
        "layer_difference": 12,
        "path_precision": 3,
    },
    "poster": {
        "clustering": "color-cluster",
        "hierarchical": "cutout",
        "mode": "spline",
        "color_precision": 4,
        "layer_difference": 24,
        "path_precision": 3,
    },
}

CUSTOM_BASE_KEY = "base"
_PRESET_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_MAX_BASE_DEPTH = 8


class UnknownPresetError(ConfigError):
    """The requested preset name does not exist (built-in or custom)."""

    def __init__(self, name: str) -> None:
        super().__init__(
            f"Unknown preset: {name}",
            hint=f"Available presets: {', '.join(available_presets())}. "
            "Save your own with: raster2svg preset save NAME --from-config FILE",
        )
        self.name = name
        self.available = available_presets()


_ENV_DATA_DIR = "RASTER2SVG_DATA_DIR"


def custom_presets_dir() -> Path:
    """Platform directory where custom presets are stored (PRD 16.4).

    Honors ``RASTER2SVG_DATA_DIR`` so the location is relocatable and
    testable without touching the real user profile.
    """
    override = os.environ.get(_ENV_DATA_DIR)
    if override:
        return Path(override)
    return Path(platformdirs.user_data_dir("raster2svg", appauthor=False))


def available_presets() -> list[str]:
    """All preset names: built-ins first, then custom (alphabetical)."""
    return sorted(PRESETS) + sorted(list_custom_presets())


def preset_source(name: str) -> str:
    """Return "builtin" or "custom" for a preset name (raises if unknown)."""
    if name in PRESETS:
        return "builtin"
    if name in list_custom_presets():
        return "custom"
    raise UnknownPresetError(name)


def list_custom_presets() -> dict[str, dict[str, Any]]:
    """Load every custom preset from the application directory.

    File name (minus the .toml suffix) is the preset name. Files that cannot
    be parsed or that fail validation are skipped silently here; ``get_preset``
    raises a specific error when one of them is actually requested.
    """
    directory = custom_presets_dir()
    if not directory.is_dir():
        return {}
    presets: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.toml")):
        try:
            presets[path.stem] = _parse_custom_preset_file(path)
        except ConfigError:
            continue
    return presets


def get_preset(name: str) -> dict[str, Any]:
    """Return the raw value dict for a built-in or custom preset.

    Custom presets are returned as parsed (may include the ``base`` key).
    Raises UnknownPresetError if the name is not found, ConfigError if a
    custom preset file is unreadable/invalid.
    """
    if name in PRESETS:
        return dict(PRESETS[name])
    custom = list_custom_presets()
    if name in custom:
        return custom[name]
    raise UnknownPresetError(name)


def resolve_preset(name: str) -> dict[str, Any]:
    """Resolve a preset including any ``base`` chain (PRD 16.4 extension).

    Base values are applied first, then the preset's own values, so the
    derived preset wins on conflict. Cycles and overly deep chains raise
    ConfigError instead of looping.
    """
    seen: list[str] = []
    chain: list[dict[str, Any]] = []
    current: str | None = name
    while current is not None:
        if current in seen:
            raise ConfigError(
                "Preset base chain contains a cycle.",
                hint=" -> ".join([*seen, current]),
            )
        if len(seen) >= _MAX_BASE_DEPTH:
            raise ConfigError("Preset base chain is too deep.")
        values = get_preset(current)
        chain.append(values)
        seen.append(current)
        current = values.get(CUSTOM_BASE_KEY)

    # ``chain`` is ordered derived-first, base-last. Merge base-first so the
    # derived preset's own values win over the values it inherits.
    resolved: dict[str, Any] = {}
    for values in reversed(chain):
        for key, value in values.items():
            if key != CUSTOM_BASE_KEY:
                resolved[key] = value
    return resolved


def validate_preset_values(name: str, values: dict[str, Any]) -> None:
    """Validate preset values against the canonical conversion model.

    Raises ConfigError listing every offending field so users can fix the
    preset file in one pass.
    """
    conversion_values = {key: value for key, value in values.items() if key != CUSTOM_BASE_KEY}
    try:
        ConversionConfig(**conversion_values)
    except Exception as exc:  # noqa: BLE001 - pydantic errors have no common subclass
        lines = []
        for problem in getattr(exc, "errors", lambda: [])():
            location = ".".join(str(part) for part in problem["loc"])
            lines.append(f"{location}: {problem['msg']}")
        detail = "\n".join(lines) or str(exc)
        raise ConfigError(
            f"Preset {name!r} contains invalid conversion setting(s).",
            hint=detail,
        ) from exc


def save_custom_preset(name: str, values: dict[str, Any]) -> Path:
    """Validate and persist a custom preset as TOML (PRD 16.4).

    The preset must not shadow a built-in name. Returns the written path.
    """
    if name in PRESETS:
        raise ConfigError(
            f"Cannot save preset {name!r}: it would shadow a built-in preset.",
            hint=f"Built-in presets: {', '.join(sorted(PRESETS))}. Choose a different name.",
        )
    if not _PRESET_NAME.match(name):
        raise ConfigError(
            f"Invalid preset name: {name!r}",
            hint="Use lowercase letters, digits, and dashes (e.g. 'my-logo').",
        )
    if not values:
        raise ConfigError(f"Preset {name!r} has no values to save.")

    validate_preset_values(name, values)
    if CUSTOM_BASE_KEY in values:
        base = values[CUSTOM_BASE_KEY]
        get_preset(base)  # raises UnknownPresetError if the base does not exist

    directory = custom_presets_dir()
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{name}.toml"
    path.write_text(render_preset_toml(name, values), encoding="utf-8")
    return path


def render_preset_toml(name: str, values: dict[str, Any]) -> str:
    """Render a preset as a TOML document (used by `preset save`)."""
    lines = [f"# raster2svg preset: {name}", ""]
    ordered: dict[str, Any] = {}
    if CUSTOM_BASE_KEY in values:
        ordered[CUSTOM_BASE_KEY] = values[CUSTOM_BASE_KEY]
    for key, value in values.items():
        if key != CUSTOM_BASE_KEY:
            ordered[key] = value
    for key, value in ordered.items():
        lines.append(f"{key} = {_toml_value(value)}")
    return "\n".join(lines) + "\n"


def _parse_custom_preset_file(path: Path) -> dict[str, Any]:
    try:
        data: Any = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ConfigError(
            f"Custom preset file is not valid TOML: {path}",
            hint=str(exc),
        ) from exc
    if not isinstance(data, dict) or not data:
        raise ConfigError(f"Custom preset file must contain at least one setting: {path}")
    validate_preset_values(path.stem, data)
    return data


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, list):
        return "[" + ", ".join(_toml_value(item) for item in value) + "]"
    raise ConfigError(f"Cannot store value of type {type(value).__name__} in a preset.")
