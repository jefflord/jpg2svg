"""Logging setup (PRD section 18)."""

from __future__ import annotations

import logging
import sys

_CONFIGURED = False


def configure_logging(*, verbose: bool = False, quiet: bool = False) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(level)
    root.handlers.clear()
    root.addHandler(handler)
    _CONFIGURED = True
