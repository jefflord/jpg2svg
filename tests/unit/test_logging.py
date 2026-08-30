"""Unit tests for logging setup (PRD section 18)."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from raster2svg.core.errors import ConfigError, OutputError
from raster2svg.utils.logging import LEVELS, configure_logging, resolve_level


def test_default_level_is_info() -> None:
    assert resolve_level() == logging.INFO


def test_verbose_maps_to_debug() -> None:
    assert resolve_level(verbose=True) == logging.DEBUG


def test_quiet_maps_to_warning() -> None:
    assert resolve_level(quiet=True) == logging.WARNING


def test_explicit_level_wins_over_flags() -> None:
    assert resolve_level(verbose=True, log_level="error") == logging.ERROR
    assert resolve_level(quiet=True, log_level="debug") == logging.DEBUG


def test_level_name_is_case_and_whitespace_insensitive() -> None:
    assert resolve_level(log_level="DEBUG") == logging.DEBUG
    assert resolve_level(log_level=" Warning ") == logging.WARNING


@pytest.mark.parametrize("level", ["debug", "info", "warning", "error"])
def test_all_levels_accepted(level: str) -> None:
    assert resolve_level(log_level=level) == LEVELS[level]


def test_verbose_and_quiet_conflict() -> None:
    with pytest.raises(ConfigError) as exc_info:
        resolve_level(verbose=True, quiet=True)
    assert exc_info.value.exit_code == 2


def test_invalid_level_rejected() -> None:
    with pytest.raises(ConfigError) as exc_info:
        resolve_level(log_level="chatty")
    assert exc_info.value.exit_code == 2
    assert exc_info.value.hint is not None
    assert "debug, info, warning, error" in exc_info.value.hint


def test_configure_returns_level_and_sets_root() -> None:
    level = configure_logging(verbose=True)
    assert level == logging.DEBUG
    root = logging.getLogger()
    assert root.level == logging.DEBUG
    assert any(isinstance(handler, logging.StreamHandler) for handler in root.handlers)


def test_configure_replaces_previous_handlers() -> None:
    configure_logging(verbose=True)
    handler_count = len(logging.getLogger().handlers)
    configure_logging(quiet=True)
    assert len(logging.getLogger().handlers) == handler_count
    assert logging.getLogger().level == logging.WARNING


def test_configure_with_log_file(tmp_path: Path) -> None:
    target = tmp_path / "sub" / "logs" / "conversion.log"
    level = configure_logging(verbose=True, log_file=target)
    assert level == logging.DEBUG
    logging.getLogger("raster2svg").debug("hello %s", "world")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert target.exists()
    assert "hello world" in target.read_text(encoding="utf-8")


def test_log_file_in_cwd(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    configure_logging(verbose=True, log_file="conversion.log")
    logging.getLogger("raster2svg").debug("in cwd")
    for handler in logging.getLogger().handlers:
        handler.flush()
    assert (tmp_path / "conversion.log").exists()


def test_uncreatable_log_file_raises_output_error(tmp_path: Path) -> None:
    blocker = tmp_path / "blocker"
    blocker.write_text("x", encoding="utf-8")
    with pytest.raises(OutputError) as exc_info:
        configure_logging(log_file=blocker / "nested" / "conversion.log")
    assert exc_info.value.exit_code == 3
