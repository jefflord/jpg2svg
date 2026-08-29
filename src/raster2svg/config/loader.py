"""Configuration file loading (PRD section 10).

Supported formats (PRD 10.1): TOML (``.toml``) and JSON (``.json``), detected
by file extension. YAML is optional per the PRD and is not part of the core
dependencies, so it is not enabled.

Two document shapes are accepted:

* sectioned (recommended) - matches the ``AppConfig`` schema::

    { "conversion": {...}, "preprocess": {...}, "output": {...} }

* flat - every top-level key is a conversion value (convenient for small files).

Unknown top-level keys in a sectioned file are rejected rather than silently
ignored (PRD section 21: "do not silently ignore requested features").
"""

from __future__ import annotations

import json
import tomllib
from pathlib import Path
from typing import Any

from raster2svg.core.errors import ConfigError

KNOWN_SECTIONS = ("conversion", "preprocess", "output")


def load_config_file(path: Path) -> dict[str, Any]:
    """Load a TOML or JSON config file.

    Returns a normalized dict with ``conversion``, ``preprocess`` and
    ``output`` keys, each a dict (possibly empty), suitable for ``AppConfig``
    and the resolver.
    """
    if not path.is_file():
        raise ConfigError(f"Config file not found: {path}", hint="Check the --config path.")
    suffix = path.suffix.lower()
    if suffix not in (".toml", ".json"):
        raise ConfigError(
            f"Unsupported config file format: {path.name}",
            hint="Supported extensions: .toml, .json",
        )

    try:
        raw = path.read_bytes().decode("utf-8-sig")
    except OSError as exc:
        raise ConfigError(f"Cannot read config file: {path}", hint=str(exc)) from exc
    except UnicodeDecodeError as exc:
        raise ConfigError(f"Config file is not valid UTF-8: {path}", hint=str(exc)) from exc

    try:
        if suffix == ".toml":
            data: Any = tomllib.loads(raw)
        else:
            data = json.loads(raw)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in config file: {path}", hint=str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in config file: {path}", hint=str(exc)) from exc

    if not isinstance(data, dict):
        raise ConfigError(
            "Config file must contain a table/object at the top level.",
            hint=f"Got {type(data).__name__} in {path.name}.",
        )

    return _normalize(data, path.name)


def _normalize(data: dict[str, Any], name: str) -> dict[str, Any]:
    sections = set(data)
    if not sections:
        return {"conversion": {}, "preprocess": {}, "output": {}}

    if not sections.intersection(KNOWN_SECTIONS):
        # Flat shape: everything is a conversion value.
        return {"conversion": dict(data), "preprocess": {}, "output": {}}

    unknown = sections.difference(KNOWN_SECTIONS)
    if unknown:
        raise ConfigError(
            f"Unknown top-level key(s) in {name}: {', '.join(sorted(unknown))}",
            hint="Tracing options belong in the [conversion] section "
            "(or at the top level of a flat config file). "
            f"Known sections: {', '.join(KNOWN_SECTIONS)}.",
        )

    conversion = data.get("conversion")
    if conversion is not None and not isinstance(conversion, dict):
        raise ConfigError(
            f"The conversion section must be a table in {name}.",
            hint=f"Got {type(conversion).__name__}.",
        )
    preprocess = data.get("preprocess")
    if preprocess is not None and not isinstance(preprocess, dict):
        raise ConfigError(
            f"The preprocess section must be a table in {name}.",
            hint=f"Got {type(preprocess).__name__}.",
        )
    output = data.get("output")
    if output is not None and not isinstance(output, dict):
        raise ConfigError(
            f"The output section must be a table in {name}.",
            hint=f"Got {type(output).__name__}.",
        )
    return {
        "conversion": conversion or {},
        "preprocess": preprocess or {},
        "output": output or {},
    }
