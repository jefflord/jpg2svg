"""Batch conversion service (PRD section 12).

Collects input files, maps them to output paths, and runs conversions with
bounded concurrency. Individual file failures never abort the batch unless
``fail_fast`` is requested (PRD 12.5/12.6).
"""

from __future__ import annotations

import fnmatch
import logging
import os
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from raster2svg.config.models import ConversionConfig, OutputConfig, PreprocessConfig
from raster2svg.core.errors import ConfigError, InputError, Raster2SvgError
from raster2svg.core.models import (
    STATUS_FAILED,
    STATUS_SKIPPED,
    ConversionResult,
)
from raster2svg.engines.vtracer_engine import VTracerEngine
from raster2svg.services.converter import Converter
from raster2svg.utils.paths import SUPPORTED_INPUT_EXTENSIONS

ProgressCallback = Callable[[ConversionResult], None]

logger = logging.getLogger("raster2svg")


@dataclass(frozen=True)
class BatchEntry:
    """One input file and the output path it will be written to."""

    input_path: Path
    output_path: Path


def resolve_jobs(jobs: str | None, file_count: int) -> int:
    """Resolve ``--jobs`` to a worker count (PRD 12.5).

    ``None``/``"auto"`` pick a conservative default; a positive integer is
    used as-is. The count is always clamped to the number of files.
    """
    if jobs in (None, "", "auto", "AUTO"):
        requested = min(4, os.cpu_count() or 1)
    elif jobs.isdigit():
        requested = max(1, int(jobs))
    else:
        raise ConfigError(
            f"Invalid --jobs value: {jobs}",
            hint="Use a positive integer (e.g. 4) or 'auto'.",
        )
    return max(1, min(requested, max(1, file_count)))


def collect_inputs(
    source: Path,
    *,
    recursive: bool = False,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
) -> list[Path]:
    """Collect supported input files from a file or directory (PRD 12.1-12.4)."""
    if not source.exists():
        raise InputError(
            f"Input path does not exist: {source}",
            hint="Check the path and try again.",
        )
    if source.is_file():
        return [source]
    if not source.is_dir():
        raise InputError(f"Input path is not a file or directory: {source}")

    def matches(name: str) -> bool:
        lower = name.lower()
        if include and not any(fnmatch.fnmatch(lower, p.lower()) for p in include):
            return False
        if exclude:
            return not any(fnmatch.fnmatch(lower, p.lower()) for p in exclude)
        return True

    iterator = source.rglob("*") if recursive else source.iterdir()
    paths = [
        path
        for path in iterator
        if path.is_file()
        and path.suffix.lower() in SUPPORTED_INPUT_EXTENSIONS
        and matches(path.name)
    ]
    return sorted(paths)


def build_entries(
    input_dir: Path,
    input_paths: list[Path],
    output_dir: Path,
) -> list[BatchEntry]:
    """Map inputs to outputs, preserving relative structure (PRD 12.1/12.2)."""
    base = input_dir if input_dir.is_dir() else input_dir.parent
    entries = []
    for path in input_paths:
        relative = path.relative_to(base)
        output_path = output_dir / relative.with_suffix(".svg")
        entries.append(BatchEntry(input_path=path, output_path=output_path))
    _check_collisions(entries)
    return entries


def _check_collisions(entries: list[BatchEntry]) -> None:
    seen: dict[str, Path] = {}
    for entry in entries:
        key = os.path.normcase(os.path.normpath(str(entry.output_path)))
        if key in seen:
            raise ConfigError(
                f"Output collision: {seen[key]} and {entry.input_path} target the same output.",
                hint="Use --include/--exclude or a different --output-dir.",
            )
        seen[key] = entry.input_path


def _engine_info() -> tuple[str, str]:
    caps = VTracerEngine().capabilities
    return caps.name, caps.version


def _failed_result(entry: BatchEntry, message: str) -> ConversionResult:
    engine_name, engine_version = _engine_info()
    from raster2svg._version import __version__

    return ConversionResult(
        status=STATUS_FAILED,
        input_path=entry.input_path,
        output_path=entry.output_path,
        tool_version=__version__,
        engine_name=engine_name,
        engine_version=engine_version,
        duration_ms=0,
        error=message,
    )


def _skipped_result(entry: BatchEntry) -> ConversionResult:
    result = _failed_result(entry, "Skipped: batch stopped (--fail-fast).")
    return ConversionResult(
        status=STATUS_SKIPPED,
        input_path=result.input_path,
        output_path=result.output_path,
        tool_version=result.tool_version,
        engine_name=result.engine_name,
        engine_version=result.engine_version,
        duration_ms=0,
        error=result.error,
    )


def _convert_one(
    entry: BatchEntry,
    config: ConversionConfig,
    output_cfg: OutputConfig,
    preprocess_cfg: PreprocessConfig,
    dry_run: bool,
) -> ConversionResult:
    """Worker entry point (module-level so it can be pickled for spawn)."""
    return Converter().convert(
        entry.input_path,
        entry.output_path,
        config=config,
        output=output_cfg,
        preprocess=preprocess_cfg,
        dry_run=dry_run,
    )


class BatchConverter:
    """Run many conversions with bounded concurrency (PRD 12.5)."""

    def __init__(self, converter: Converter | None = None) -> None:
        self._converter = converter or Converter()

    def convert_many(
        self,
        entries: list[BatchEntry],
        *,
        config: ConversionConfig | None = None,
        output: OutputConfig | None = None,
        preprocess: PreprocessConfig | None = None,
        jobs: int = 1,
        fail_fast: bool = False,
        dry_run: bool = False,
        on_result: ProgressCallback | None = None,
    ) -> list[ConversionResult]:
        """Convert every entry; per-file failures are captured, not raised."""
        logger.debug("batch: %d file(s), jobs=%d", len(entries), jobs)
        config = config or ConversionConfig()
        output_cfg = output or OutputConfig()
        preprocess_cfg = preprocess or PreprocessConfig()
        results: list[ConversionResult | None] = [None] * len(entries)

        if jobs <= 1 or len(entries) <= 1:
            self._run_serial(
                entries, results, config, output_cfg, preprocess_cfg, fail_fast, dry_run, on_result
            )
        else:
            self._run_parallel(
                entries,
                results,
                config,
                output_cfg,
                preprocess_cfg,
                jobs,
                fail_fast,
                dry_run,
                on_result,
            )
        final_results = [r for r in results if r is not None]
        for result in final_results:
            if result.status == STATUS_FAILED and result.error:
                logger.warning("%s: %s", result.input_path, result.error)
            elif result.status == STATUS_SKIPPED:
                logger.debug("skipped: %s", result.input_path)
        return final_results

    def _run_serial(
        self,
        entries: list[BatchEntry],
        results: list[ConversionResult | None],
        config: ConversionConfig,
        output_cfg: OutputConfig,
        preprocess_cfg: PreprocessConfig,
        fail_fast: bool,
        dry_run: bool,
        on_result: ProgressCallback | None,
    ) -> None:
        for index, entry in enumerate(entries):
            result = self._convert_catch(entry, config, output_cfg, preprocess_cfg, dry_run)
            results[index] = result
            if on_result is not None:
                on_result(result)
            if fail_fast and result.status == STATUS_FAILED:
                for rest in range(index + 1, len(entries)):
                    results[rest] = _skipped_result(entries[rest])
                break

    def _run_parallel(
        self,
        entries: list[BatchEntry],
        results: list[ConversionResult | None],
        config: ConversionConfig,
        output_cfg: OutputConfig,
        preprocess_cfg: PreprocessConfig,
        jobs: int,
        fail_fast: bool,
        dry_run: bool,
        on_result: ProgressCallback | None,
    ) -> None:
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(_convert_one, entry, config, output_cfg, preprocess_cfg, dry_run): (
                    index,
                    entry,
                )
                for index, entry in enumerate(entries)
            }
            stop = False
            for future in as_completed(futures):
                index, entry = futures[future]
                try:
                    result = future.result()
                except Raster2SvgError as exc:
                    result = _failed_result(entry, exc.message)
                except Exception as exc:  # noqa: BLE001 - report, don't crash the batch
                    result = _failed_result(entry, f"Unexpected error: {exc}")
                results[index] = result
                if on_result is not None:
                    on_result(result)
                if fail_fast and result.status == STATUS_FAILED:
                    stop = True
                    for pending in futures:
                        pending.cancel()
                    break
        if stop:
            for future, (index, entry) in futures.items():
                if results[index] is not None or not future.done() or future.cancelled():
                    continue
                try:
                    results[index] = future.result()
                except Raster2SvgError as exc:
                    results[index] = _failed_result(entry, exc.message)
                except Exception as exc:  # noqa: BLE001
                    results[index] = _failed_result(entry, f"Unexpected error: {exc}")
            for index, existing in enumerate(results):
                if existing is None:
                    results[index] = _skipped_result(entries[index])

    def _convert_catch(
        self,
        entry: BatchEntry,
        config: ConversionConfig,
        output_cfg: OutputConfig,
        preprocess_cfg: PreprocessConfig,
        dry_run: bool,
    ) -> ConversionResult:
        try:
            return self._converter.convert(
                entry.input_path,
                entry.output_path,
                config=config,
                output=output_cfg,
                preprocess=preprocess_cfg,
                dry_run=dry_run,
            )
        except Raster2SvgError as exc:
            return _failed_result(entry, exc.message)
        except Exception as exc:  # noqa: BLE001
            return _failed_result(entry, f"Unexpected error: {exc}")
