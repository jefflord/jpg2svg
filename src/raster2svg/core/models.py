"""Result types for conversion operations."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

STATUS_SUCCESS = "success"
STATUS_DRY_RUN = "dry-run"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


@dataclass(frozen=True)
class ConversionResult:
    """Outcome of a single conversion attempt."""

    status: str
    input_path: Path
    output_path: Path
    tool_version: str
    engine_name: str
    engine_version: str
    duration_ms: int
    config: dict[str, Any] = field(default_factory=dict)
    output_bytes: int | None = None
    input_format: str | None = None
    input_width: int | None = None
    input_height: int | None = None
    error: str | None = None
