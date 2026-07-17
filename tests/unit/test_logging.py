"""Tests for logging configuration and API-key masking helpers."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from logging.handlers import RotatingFileHandler

import pytest

import pa_agent.util.logging as logging_module
from pa_agent.util.mask_secret import mask_secret

_MANAGED_LOGGER_NAMES = ("urllib3", "openai", "httpx")


@pytest.fixture
def isolated_logging_state() -> Iterator[None]:
    """Restore global logging state after tests that reconfigure root handlers."""
    loggers = [logging.getLogger(), *(logging.getLogger(name) for name in _MANAGED_LOGGER_NAMES)]
    saved_states = {
        logger: (list(logger.handlers), logger.level, logger.propagate, logger.disabled)
        for logger in loggers
    }
    saved_configured = logging_module._configured
    saved_formatters = list(logging_module._active_formatters)
    saved_disable_level = logging.root.manager.disable

    for logger in loggers:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
    logging_module._configured = False
    logging_module._active_formatters.clear()
    logging.disable(logging.NOTSET)

    try:
        yield
    finally:
        added_handlers: set[logging.Handler] = set()
        for logger in loggers:
            added_handlers.update(logger.handlers)
            for handler in list(logger.handlers):
                logger.removeHandler(handler)

        saved_handlers = {
            handler
            for handlers, _level, _propagate, _disabled in saved_states.values()
            for handler in handlers
        }
        for handler in added_handlers - saved_handlers:
            handler.close()

        for logger, (handlers, level, propagate, disabled) in saved_states.items():
            logger.setLevel(level)
            logger.propagate = propagate
            logger.disabled = disabled
            for handler in handlers:
                logger.addHandler(handler)

        logging_module._configured = saved_configured
        logging_module._active_formatters[:] = saved_formatters
        logging.disable(saved_disable_level)


def test_masking_formatter_replaces_plaintext_key_after_key_update() -> None:
    old_key = "test-old-key-1234"
    new_key = "test-new-key-5678"
    formatter = logging_module.MaskingFormatter("%(message)s", api_key=old_key)

    old_record = logging.LogRecord("test.logging", logging.INFO, "", 0, "key=%s", (old_key,), None)
    old_message = formatter.format(old_record)
    assert old_key not in old_message
    assert mask_secret(old_key) in old_message

    formatter.set_api_key(new_key)
    new_record = logging.LogRecord("test.logging", logging.INFO, "", 0, "key=%s", (new_key,), None)
    new_message = formatter.format(new_record)
    assert new_key not in new_message
    assert mask_secret(new_key) in new_message


def test_update_api_key_updates_all_active_formatters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = logging_module.MaskingFormatter("%(message)s")
    second = logging_module.MaskingFormatter("%(message)s", api_key="old-key")
    monkeypatch.setattr(logging_module, "_active_formatters", [first, second])

    logging_module.update_api_key("current-key-1234")

    assert first._api_key == "current-key-1234"
    assert second._api_key == "current-key-1234"


def test_verify_logging_handlers_requires_matching_rotating_file(
    isolated_logging_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    expected_path = tmp_path / "pa_agent.log"
    other_path = tmp_path / "other.log"
    monkeypatch.setattr(logging_module, "LOG_FILE_PATH", expected_path)
    root_logger = logging.getLogger()

    assert logging_module.verify_logging_handlers() is False

    other_handler = RotatingFileHandler(other_path)
    root_logger.addHandler(other_handler)
    try:
        assert logging_module.verify_logging_handlers() is False
    finally:
        root_logger.removeHandler(other_handler)
        other_handler.close()

    expected_handler = RotatingFileHandler(expected_path)
    root_logger.addHandler(expected_handler)
    try:
        assert logging_module.verify_logging_handlers() is True
    finally:
        root_logger.removeHandler(expected_handler)
        expected_handler.close()


def test_configure_logging_reuses_and_recovers_handlers(
    isolated_logging_state: None,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    monkeypatch.setattr(logging_module, "LOG_FILE_PATH", tmp_path / "pa_agent.log")
    root_logger = logging.getLogger()

    logging_module.configure_logging(api_key="first-key-1234")
    first_handlers = list(root_logger.handlers)

    assert len(first_handlers) == 2
    assert logging_module.verify_logging_handlers() is True
    assert len(logging_module._active_formatters) == 2
    for name in _MANAGED_LOGGER_NAMES:
        third_party_logger = logging.getLogger(name)
        assert third_party_logger.handlers == first_handlers
        assert third_party_logger.propagate is False

    logging_module.configure_logging(api_key="second-key-5678")
    assert root_logger.handlers == first_handlers
    assert {formatter._api_key for formatter in logging_module._active_formatters} == {
        "second-key-5678"
    }

    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)
    assert logging_module.verify_logging_handlers() is False

    logging_module.configure_logging(api_key="third-key-9012")
    assert len(root_logger.handlers) == 2
    assert logging_module.verify_logging_handlers() is True
    assert {formatter._api_key for formatter in logging_module._active_formatters} == {
        "third-key-9012"
    }
