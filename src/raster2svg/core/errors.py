"""Exception hierarchy for raster2svg.

Exit codes follow PRD section 12.6:

* 0 - success
* 1 - one or more conversions failed (batch)
* 2 - invalid CLI / configuration
* 3 - input/output filesystem error
* 4 - dependency / runtime error
"""

from __future__ import annotations


class Raster2SvgError(Exception):
    """Base class for all raster2svg errors."""

    exit_code = 4

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.hint = hint

    def render(self) -> str:
        text = f"ERROR: {self.message}"
        if self.hint:
            text = f"{text}\n{self.hint}"
        return text


class ConfigError(Raster2SvgError):
    """Invalid CLI option or configuration value."""

    exit_code = 2


class UnsupportedFeatureError(ConfigError):
    """A requested setting is not supported by the installed tracing engine."""

    exit_code = 2


class InputError(Raster2SvgError):
    """The input image is missing, unreadable, or invalid."""

    exit_code = 3


class OutputError(Raster2SvgError):
    """The output path cannot be used or written."""

    exit_code = 3


class EngineError(Raster2SvgError):
    """The tracing engine failed at runtime."""

    exit_code = 4
