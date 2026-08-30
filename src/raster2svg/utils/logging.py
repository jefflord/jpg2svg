"""Logging setup (PRD section 18).

Level resolution (PRD 18.1):
* ``--log-level`` wins when given;
* ``--verbose`` maps to DEBUG;
* ``--quiet`` maps to WARNING;
* otherwise INFO.

Log messages go to stderr by default; ``--log-file`` (PRD 18.2) also writes
them to a file.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from raster2svg.core.errors import ConfigError, OutputError

#: Accepted ``--log-level`` names (case-insensitive).
LEVELS: dict[str, int] = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
}

_FORMAT = "%(levelname)s %(name)s: %(message)s"


def resolve_level(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_level: str | None = None,
) -> int:
    """Resolve the effective logging level (PRD 18.1).

    Raises:
        ConfigError: if ``--verbose`` and ``--quiet`` are combined, or if the
            level name is not one of debug/info/warning/error.
    """
    if verbose and quiet:
        raise ConfigError(
            "--verbose and --quiet are mutually exclusive.",
            hint="Use one of them, or set the level with --log-level.",
        )
    if log_level is not None:
        try:
            return LEVELS[log_level.strip().lower()]
        except KeyError:
            raise ConfigError(
                f"Invalid --log-level: {log_level}",
                hint="Expected one of: debug, info, warning, error.",
            ) from None
    if verbose:
        return logging.DEBUG
    if quiet:
        return logging.WARNING
    return logging.INFO


def configure_logging(
    *,
    verbose: bool = False,
    quiet: bool = False,
    log_level: str | None = None,
    log_file: str | Path | None = None,
) -> int:
    """Configure the root logger and return the effective level.

    Each call replaces the previous configuration, which keeps unit tests
    hermetic (no shared module-level state).

    Raises:
        ConfigError: on conflicting or invalid level options.
        OutputError: if the log file cannot be created.
    """
    level = resolve_level(verbose=verbose, quiet=quiet, log_level=log_level)
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    stream_handler = logging.StreamHandler(stream=sys.stderr)
    stream_handler.setFormatter(logging.Formatter(_FORMAT))
    root.addHandler(stream_handler)
    if log_file is not None:
        target = Path(log_file)
        try:
            if str(target.parent) not in ("", "."):
                target.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(target, encoding="utf-8")
        except OSError as exc:
            raise OutputError(
                f"Cannot create log file: {target}",
                hint="Check the path and permissions.",
            ) from exc
        file_handler.setFormatter(logging.Formatter(_FORMAT))
        root.addHandler(file_handler)
    return level
