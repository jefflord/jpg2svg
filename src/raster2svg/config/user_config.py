"""User-level configuration file (PRD section 8, precedence level 3).

An optional ``config.toml`` (or ``config.json``) in the application data
directory applies to every conversion on this machine. Its precedence sits
between presets and an explicit ``--config`` file:

    defaults < preset < user config < --config file < CLI options

The file uses the same sectioned/flat document shapes as project config
files (see ``loader.py``). The location is the same platform-appropriate
application directory that custom presets use, with the
``RASTER2SVG_DATA_DIR`` override for tests and relocation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from raster2svg.config.loader import load_config_file
from raster2svg.config.presets import custom_presets_dir

#: File names probed in the application directory, in priority order.
USER_CONFIG_FILENAMES = ("config.toml", "config.json")


def user_config_dir() -> Path:
    """Application data directory that holds the user config file (PRD 8)."""
    return custom_presets_dir()


def find_user_config_file() -> Path | None:
    """Return the user-level config file if one exists, else ``None``."""
    directory = user_config_dir()
    for name in USER_CONFIG_FILENAMES:
        candidate = directory / name
        if candidate.is_file():
            return candidate
    return None


def load_user_config() -> dict[str, Any]:
    """Load the user-level config file as normalized sections.

    Returns empty sections when no user config file exists, so callers can
    merge unconditionally. Raises ConfigError for an invalid file.
    """
    path = find_user_config_file()
    if path is None:
        return {"conversion": {}, "preprocess": {}, "output": {}}
    return load_config_file(path)
