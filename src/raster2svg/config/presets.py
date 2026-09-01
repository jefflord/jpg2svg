"""Built-in and custom presets (PRD section 16).

A preset is a named bundle of initial values with three sections plus
optional display metadata:

* ``conversion``  -- tracing options, validated against ``ConversionConfig``
* ``preprocess``  -- Pillow preprocessing options, validated against
  ``PreprocessConfig``
* ``postprocess`` -- SVG output options (e.g. invert), validated against
  ``PostprocessConfig``
* metadata        -- ``description``, ``recommended_for``, ``notes``

A preset only sets initial values: config-file values and CLI options always
override it, for both sections (PRD 8, 9.1).

Custom presets (PRD 16.4) are user-saved TOML files in the
platform-appropriate application directory. A custom preset may set a
``base`` key to inherit from another preset (built-in or custom); the base
is resolved recursively, with the derived preset's values winning.

Two file shapes are accepted:

* **structured** (preferred)::

    description = "My clip art"
    base = "clip-art"

    [conversion]
    mode = "spline"

    [preprocess]
    denoise = true

* **legacy flat** (old files keep working): every top-level key except
  ``base``/metadata is a conversion value::

    base = "photo"
    mode = "polygon"

Values are validated against the canonical models before saving so a saved
preset can never be silently ignored (PRD 21).
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import platformdirs

from raster2svg.config.models import ConversionConfig, PostprocessConfig, PreprocessConfig
from raster2svg.core.errors import ConfigError

PRESET_NOTE = (
    "A preset only sets initial values; explicit config-file values and CLI "
    "options always override it (for preprocessing and conversion alike)."
)

_META_KEYS = {"base", "description", "recommended_for", "notes"}
_SECTION_KEYS = {"conversion", "preprocess", "postprocess"}


@dataclass(frozen=True)
class Preset:
    """A preset's values and metadata.

    ``conversion``/``preprocess`` hold the (already base-resolved) starting
    values for each section; empty dicts mean "engine defaults".
    """

    name: str
    source: str  # "builtin" | "custom"
    base: str | None
    description: str | None
    recommended_for: tuple[str, ...]
    notes: str | None
    conversion: dict[str, Any]
    preprocess: dict[str, Any]
    postprocess: dict[str, Any]


# Built-in presets (PRD 16.1 requires bw/photo/poster; the rest extend the
# set). Values are starting points only; every field is overridable, so these
# never limit the user.
PRESETS: dict[str, dict[str, Any]] = {
    "bw": {
        "description": "High-contrast black-and-white graphics, line work, and technical drawings.",
        "recommended_for": ["logos", "icons", "line art", "black & white scans"],
        "conversion": {
            "clustering": "bw",
            "hierarchical": "stacked",
            "mode": "spline",
            "binary_threshold": 128,
            "filter_speckle": 4,
            "simplify": 1.0,
            "optimize": 1,
            "path_precision": 3,
        },
        "preprocess": {"grayscale": True, "denoise": True, "autocontrast": True},
    },
    "photo": {
        "description": "Photorealistic images as smooth, layered color vector art.",
        "recommended_for": ["photos", "portraits", "landscapes"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 6,
            "layer_difference": 12,
            "filter_speckle": 2,
            "simplify": 1.0,
            "optimize": 1,
            "path_precision": 3,
        },
        "preprocess": {"denoise": True},
    },
    "poster": {
        "description": "Bold, flat, few-color poster and screen-print look.",
        "recommended_for": ["posters", "flyers", "screen prints"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "cutout",
            "mode": "spline",
            "color_precision": 4,
            "layer_difference": 24,
            "max_colors": 16,
            "filter_speckle": 4,
            "simplify": 2.0,
            "optimize": 2,
            "path_precision": 3,
        },
        "preprocess": {
            "denoise": True,
            "posterize": 4,
            "autocontrast": True,
            "pre_max_colors": 64,
        },
    },
    "flat-illustration": {
        "description": "Clean flat-design illustration: smooth shapes, limited palette.",
        "recommended_for": ["flat illustrations", "vector art", "infographics"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 4,
            "layer_difference": 20,
            "max_colors": 48,
            "filter_speckle": 4,
            "simplify": 1.5,
            "optimize": 1,
            "path_precision": 3,
        },
        "preprocess": {
            "denoise": True,
            "blur": True,
            "posterize": 5,
            "autocontrast": True,
        },
    },
    "clip-art": {
        "description": "Classic clip art: bold colors, smooth curves, minimal speckle.",
        "recommended_for": ["clip art", "scanned drawings", "cartoons"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 4,
            "layer_difference": 24,
            "max_colors": 32,
            "filter_speckle": 8,
            "simplify": 2.0,
            "optimize": 2,
            "path_precision": 3,
        },
        "preprocess": {
            "denoise": True,
            "blur": True,
            "posterize": 5,
            "autocontrast": True,
            "pre_max_colors": 96,
        },
    },
    "clip-art-soft": {
        "description": "Gentler clip-art tracing: keeps more color and detail, lighter cleanup.",
        "recommended_for": ["detailed clip art", "shaded illustrations"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 5,
            "layer_difference": 16,
            "max_colors": 64,
            "filter_speckle": 4,
            "simplify": 1.0,
            "optimize": 1,
            "path_precision": 3,
        },
        "preprocess": {
            "denoise": True,
            "posterize": 6,
            "autocontrast": True,
            "pre_max_colors": 128,
        },
    },
    "clip-art-strong": {
        "description": "Aggressive clip-art cleanup: very few colors, thick clean shapes.",
        "recommended_for": ["noisy scans", "low-res clip art", "stamps"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 3,
            "layer_difference": 32,
            "max_colors": 16,
            "filter_speckle": 12,
            "simplify": 3.0,
            "optimize": 2,
            "path_precision": 2,
        },
        "preprocess": {
            "denoise": True,
            "blur": True,
            "posterize": 4,
            "autocontrast": True,
            "pre_max_colors": 48,
        },
    },
    "comic": {
        "description": "Comic and manga style: crisp shapes, flat cel color, high contrast.",
        "recommended_for": ["comics", "manga", "cel shading"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 3,
            "layer_difference": 28,
            "max_colors": 32,
            "filter_speckle": 8,
            "simplify": 2.0,
            "optimize": 2,
            "path_precision": 3,
        },
        "preprocess": {
            "denoise": True,
            "blur": True,
            "posterize": 4,
            "autocontrast": True,
            "contrast": 1.4,
        },
    },
    "line-art": {
        "description": "Ink line drawings: adaptive thresholding keeps strokes under uneven light.",
        "recommended_for": ["line art", "ink drawings", "sketches"],
        "conversion": {
            "clustering": "bw",
            "hierarchical": "stacked",
            "mode": "spline",
            "adaptive": True,
            "adaptive_window": 31,
            "adaptive_t": 25,
            "filter_speckle": 6,
            "simplify": 1.0,
            "optimize": 1,
            "path_precision": 3,
        },
        "preprocess": {"grayscale": True, "denoise": True, "blur": True},
    },
    "line-art-inverted": {
        "description": "Negative line art: white strokes on a dark background.",
        "recommended_for": ["line art on dark", "neon and signage", "reversed ink sketches"],
        "base": "line-art",
        "postprocess": {"invert": True},
    },
    "silhouette": {
        "description": "Solid single-color silhouettes: the image becomes one flat shape.",
        "recommended_for": ["silhouettes", "stencils", "shadow shapes"],
        "conversion": {
            "clustering": "bw",
            "hierarchical": "stacked",
            "mode": "spline",
            "binary_threshold": 110,
            "filter_speckle": 12,
            "simplify": 3.0,
            "optimize": 2,
            "path_precision": 2,
        },
        "preprocess": {"grayscale": True, "denoise": True, "blur": True, "autocontrast": True},
    },
    "silhouette-inverted": {
        "description": "Negative silhouette: a solid light shape on a dark background.",
        "recommended_for": ["stencils on dark", "reversed shadow shapes"],
        "base": "silhouette",
        "postprocess": {"invert": True},
    },
    "logo-cleanup": {
        "description": "Logos and badges: precise curves, clean edges, small faithful palette.",
        "recommended_for": ["logos", "badges", "emblems"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "spline",
            "color_precision": 5,
            "layer_difference": 8,
            "max_colors": 24,
            "filter_speckle": 6,
            "simplify": 1.0,
            "optimize": 2,
            "path_precision": 4,
        },
        "preprocess": {"denoise": True},
    },
    "pixel-art": {
        "description": "Pixel art and retro sprites: hard edges, no smoothing, one shape per block",
        "recommended_for": ["pixel art", "retro games", "sprites"],
        "conversion": {
            "clustering": "color-cluster",
            "hierarchical": "stacked",
            "mode": "pixel",
            "color_precision": 5,
            "layer_difference": 16,
            "max_colors": 32,
            "filter_speckle": 1,
            "simplify": 0.5,
            "optimize": 1,
        },
        "preprocess": {},
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
    """Load every custom preset from the application directory (raw dicts).

    File name (minus the .toml suffix) is the preset name. Files that cannot
    be parsed or that fail validation are skipped silently here, so they are
    neither listed nor resolvable (requests for them raise
    UnknownPresetError).
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


def get_preset(name: str) -> Preset:
    """Return one preset (its own values, base chain NOT resolved).

    Raises UnknownPresetError if the name is not found, ConfigError if a
    custom preset file is unreadable/invalid.
    """
    if name in PRESETS:
        return _make_preset(name, "builtin", PRESETS[name])
    custom = list_custom_presets()
    if name in custom:
        return _make_preset(name, "custom", custom[name])
    raise UnknownPresetError(name)


def resolve_preset(name: str) -> Preset:
    """Resolve a preset including any ``base`` chain (PRD 16.4 extension).

    Base values are applied first, then the preset's own values, so the
    derived preset wins on conflict (per section). Metadata (description,
    recommended_for, notes) is inherited from the first preset in the chain
    that has it. Cycles and overly deep chains raise ConfigError.
    """
    seen: list[str] = []
    chain: list[Preset] = []
    current: str | None = name
    while current is not None:
        if current in seen:
            raise ConfigError(
                "Preset base chain contains a cycle.",
                hint=" -> ".join([*seen, current]),
            )
        if len(seen) >= _MAX_BASE_DEPTH:
            raise ConfigError("Preset base chain is too deep.")
        preset = get_preset(current)
        chain.append(preset)
        seen.append(current)
        current = preset.base

    conversion: dict[str, Any] = {}
    preprocess: dict[str, Any] = {}
    postprocess: dict[str, Any] = {}
    for preset in reversed(chain):  # base first, derived last -> derived wins
        conversion.update(preset.conversion)
        preprocess.update(preset.preprocess)
        postprocess.update(preset.postprocess)

    description = next(
        (preset.description for preset in chain if preset.description), None
    )
    notes = next((preset.notes for preset in chain if preset.notes), None)
    recommended_for = next(
        (preset.recommended_for for preset in chain if preset.recommended_for), ()
    )

    return Preset(
        name=name,
        source=chain[0].source,
        base=None,
        description=description,
        recommended_for=recommended_for,
        notes=notes,
        conversion=conversion,
        preprocess=preprocess,
        postprocess=postprocess,
    )


def preset_details() -> dict[str, dict[str, Any]]:
    """Resolved metadata for every known preset (for the web UI / CLI list)."""
    details: dict[str, dict[str, Any]] = {}
    for name in available_presets():
        preset = resolve_preset(name)
        details[name] = {
            "description": preset.description or "",
            "recommended_for": list(preset.recommended_for),
            "notes": preset.notes or "",
            "source": preset.source,
        }
    return details


def _make_preset(name: str, source: str, raw: dict[str, Any]) -> Preset:
    validate_preset_values(name, raw)
    conversion, preprocess, postprocess = _split_sections(name, raw)
    return Preset(
        name=name,
        source=source,
        base=raw.get(CUSTOM_BASE_KEY) if isinstance(raw.get(CUSTOM_BASE_KEY), str) else None,
        description=raw.get("description") if isinstance(raw.get("description"), str) else None,
        recommended_for=_tuple_of_str(raw.get("recommended_for")),
        notes=raw.get("notes") if isinstance(raw.get("notes"), str) else None,
        conversion=conversion,
        preprocess=preprocess,
        postprocess=postprocess,
    )


def _split_sections(
    name: str, values: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Split raw preset values into (conversion, preprocess, postprocess).

    Structured files carry ``conversion``/``preprocess``/``postprocess``
    keys; legacy flat files (and conversion-only presets) put conversion
    values at the top level, where any metadata keys are excluded.
    """
    if "conversion" in values or "preprocess" in values or "postprocess" in values:
        unexpected = set(values) - _META_KEYS - _SECTION_KEYS
        if unexpected:
            raise ConfigError(
                f"Preset {name!r} mixes sectioned and flat values.",
                hint=(
                    f"Move {', '.join(sorted(unexpected))} into the [conversion], "
                    "[preprocess], or [postprocess] section when using sectioned keys."
                ),
            )
        conversion = values.get("conversion") or {}
        preprocess = values.get("preprocess") or {}
        postprocess = values.get("postprocess") or {}
    else:
        conversion = {key: value for key, value in values.items() if key not in _META_KEYS}
        preprocess = {}
        postprocess = {}
    if (
        not isinstance(conversion, dict)
        or not isinstance(preprocess, dict)
        or not isinstance(postprocess, dict)
    ):
        raise ConfigError(
            f"Preset {name!r} sections must be tables of settings.",
            hint=(
                "'conversion', 'preprocess', and 'postprocess' values must be "
                "tables/objects."
            ),
        )
    return dict(conversion), dict(preprocess), dict(postprocess)


def validate_preset_values(name: str, values: dict[str, Any]) -> None:
    """Validate preset values against the canonical models.

    Raises ConfigError listing every offending field so users can fix the
    preset in one pass.
    """
    conversion, preprocess, postprocess = _split_sections(name, values)
    _validate_section(name, "conversion", conversion, ConversionConfig)
    _validate_section(name, "preprocess", preprocess, PreprocessConfig)
    _validate_section(name, "postprocess", postprocess, PostprocessConfig)


def _validate_section(
    name: str, section: str, values: dict[str, Any], model: type
) -> None:
    if not values:
        return
    try:
        model(**values)
    except Exception as exc:  # noqa: BLE001 - pydantic errors have no common subclass
        lines = []
        for problem in getattr(exc, "errors", lambda: [])():
            location = ".".join(str(part) for part in problem["loc"])
            lines.append(f"{location}: {problem['msg']}")
        detail = "\n".join(lines) or str(exc)
        raise ConfigError(
            f"Preset {name!r} contains invalid {section} setting(s).",
            hint=detail,
        ) from exc


def save_custom_preset(name: str, values: dict[str, Any]) -> Path:
    """Validate and persist a custom preset as TOML (PRD 16.4).

    Accepts both the structured shape (``conversion``/``preprocess``
    sections, optional metadata) and the legacy flat shape (conversion
    values at the top level). The preset must not shadow a built-in name.
    Returns the written path.
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
    conversion, preprocess, postprocess = _split_sections(name, values)
    if (
        not conversion
        and not preprocess
        and not postprocess
        and CUSTOM_BASE_KEY not in values
        and not (values.get("description") or values.get("notes") or values.get("recommended_for"))
    ):
        raise ConfigError(f"Preset {name!r} has no values to save.")

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
    if values.get("description"):
        lines.append(f"description = {_toml_value(values['description'])}")
    if values.get("recommended_for"):
        lines.append(f"recommended_for = {_toml_value(list(values['recommended_for']))}")
    if values.get("notes"):
        lines.append(f"notes = {_toml_value(values['notes'])}")
    if CUSTOM_BASE_KEY in values:
        lines.append(f"{CUSTOM_BASE_KEY} = {_toml_value(values[CUSTOM_BASE_KEY])}")
    if lines[-1] != "":
        lines.append("")

    conversion, preprocess, postprocess = _split_sections(name, values)
    if conversion:
        lines.append("[conversion]")
        for key, value in conversion.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    if preprocess:
        lines.append("[preprocess]")
        for key, value in preprocess.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    if postprocess:
        lines.append("[postprocess]")
        for key, value in postprocess.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    while lines and lines[-1] == "":
        lines.pop()
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


def _tuple_of_str(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        raise ConfigError(
            "'recommended_for' must be a list of strings.",
            hint='e.g. recommended_for = ["clip art", "cartoons"]',
        )
    return tuple(value)


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
