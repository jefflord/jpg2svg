"""JSON report generation (PRD section 17)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from raster2svg.core.models import (
    STATUS_DRY_RUN,
    STATUS_FAILED,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    ConversionResult,
)


def _result_payload(result: ConversionResult) -> dict[str, Any]:
    return {
        "status": result.status,
        "input": str(result.input_path),
        "output": str(result.output_path) if result.output_path else None,
        "output_bytes": result.output_bytes,
        "input_format": result.input_format,
        "input_width": result.input_width,
        "input_height": result.input_height,
        "duration_ms": result.duration_ms,
        "error": result.error,
        "tool_version": result.tool_version,
        "engine": f"{result.engine_name} {result.engine_version}",
        "config": result.config,
    }


def render_report(result: ConversionResult) -> str:
    """Render one conversion result as a JSON document (PRD 17.1)."""
    return json.dumps(_result_payload(result), indent=2, ensure_ascii=False) + "\n"


def render_batch_report(
    results: list[ConversionResult],
    *,
    input_source: str,
) -> str:
    """Render a whole batch as one JSON document (PRD 12.6, 17.1)."""
    totals = {
        "total": len(results),
        "succeeded": sum(1 for r in results if r.status == STATUS_SUCCESS),
        "dry_run": sum(1 for r in results if r.status == STATUS_DRY_RUN),
        "failed": sum(1 for r in results if r.status == STATUS_FAILED),
        "skipped": sum(1 for r in results if r.status == STATUS_SKIPPED),
    }
    payload = {
        "tool": "raster2svg",
        "input_source": input_source,
        "totals": totals,
        "results": [_result_payload(r) for r in results],
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def render_jsonl_line(result: ConversionResult) -> str:
    """A single JSON line, for streaming output (PRD 17.2)."""
    return json.dumps(_result_payload(result), ensure_ascii=False) + "\n"


def render_jsonl(results: list[ConversionResult]) -> str:
    """One JSON object per line, for pipelines (PRD 17.2)."""
    return "".join(render_jsonl_line(r) for r in results)


def write_report(path: Path, result: ConversionResult) -> None:
    """Write a single-result report to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(result), encoding="utf-8")


def write_batch_report(path: Path, results: list[ConversionResult], *, input_source: str) -> None:
    """Write a batch report to ``path``."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_batch_report(results, input_source=input_source), encoding="utf-8")
