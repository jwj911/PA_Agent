"""Tests for crash diagnostics helpers."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from pa_agent.util import crash_diagnostics


def test_log_file_handler_attached_detects_matching_rotating_file_handler(
    tmp_path,
    monkeypatch,
) -> None:
    log_path = tmp_path / "pa_agent.log"
    monkeypatch.setattr(crash_diagnostics, "LOG_FILE_PATH", log_path)
    logger = logging.Logger("test_crash_diagnostics_matching")
    handler = RotatingFileHandler(log_path)
    logger.addHandler(handler)

    try:
        assert crash_diagnostics._log_file_handler_attached(logger) is True
    finally:
        logger.removeHandler(handler)
        handler.close()


def test_log_file_handler_attached_rejects_missing_or_different_file_handler(
    tmp_path,
    monkeypatch,
) -> None:
    expected_path = tmp_path / "pa_agent.log"
    other_path = tmp_path / "other.log"
    monkeypatch.setattr(crash_diagnostics, "LOG_FILE_PATH", expected_path)
    logger = logging.Logger("test_crash_diagnostics_nonmatching")

    assert crash_diagnostics._log_file_handler_attached(logger) is False

    handler = RotatingFileHandler(other_path)
    logger.addHandler(handler)
    try:
        assert crash_diagnostics._log_file_handler_attached(logger) is False
    finally:
        logger.removeHandler(handler)
        handler.close()
