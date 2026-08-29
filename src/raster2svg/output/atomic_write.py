"""Atomic output writes (PRD section 14.4).

Write to a temporary file in the target directory, then rename over the
target so a partially written SVG can never be left behind.
"""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path

from raster2svg.core.errors import OutputError


def atomic_write_text(
    target: Path,
    text: str,
    *,
    overwrite: bool,
    create_directories: bool = True,
) -> None:
    if target.exists() and not overwrite:
        raise OutputError(
            f"Output file already exists: {target}",
            hint="Use --overwrite to replace it.",
        )
    if not target.parent.exists() and not create_directories:
        raise OutputError(
            f"Output directory does not exist: {target.parent}",
            hint="Omit --no-mkdir to allow creating it.",
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=target.parent, prefix=".raster2svg-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, target)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(tmp_name)
        raise
