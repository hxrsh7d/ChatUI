"""Tests for logging_config.py -- mainly that the JSON formatter produces
valid, parseable JSON and never crashes on the extra_fields mechanism."""

import json
import logging

from logging_config import JsonFormatter, TextFormatter, get_logger


def _make_record(msg: str, extra_fields: dict | None = None) -> logging.LogRecord:
    record = logging.LogRecord(
        name="chatui.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=msg,
        args=(),
        exc_info=None,
    )
    if extra_fields is not None:
        record.extra_fields = extra_fields
    return record


def test_json_formatter_produces_valid_json():
    formatter = JsonFormatter()
    record = _make_record("hello world", {"status": 200, "duration_ms": 12.3})
    output = formatter.format(record)
    parsed = json.loads(output)
    assert parsed["message"] == "hello world"
    assert parsed["level"] == "INFO"
    assert parsed["status"] == 200
    assert parsed["duration_ms"] == 12.3


def test_json_formatter_without_extra_fields_still_valid():
    formatter = JsonFormatter()
    output = formatter.format(_make_record("plain message"))
    parsed = json.loads(output)
    assert parsed["message"] == "plain message"


def test_json_formatter_never_includes_raw_secrets_by_accident():
    # extra_fields is an explicit opt-in dict the caller controls -- this
    # just documents/asserts that formatting doesn't pull in anything from
    # the record beyond what's explicitly passed.
    formatter = JsonFormatter()
    output = formatter.format(_make_record("request", {"path": "/api/chat"}))
    assert "Authorization" not in output
    assert "Bearer" not in output


def test_text_formatter_appends_extra_fields_readably():
    formatter = TextFormatter("%(message)s")
    output = formatter.format(_make_record("request", {"status": 200, "path": "/health"}))
    assert "request" in output
    assert "status=200" in output
    assert "path=/health" in output


def test_get_logger_namespaces_under_chatui():
    logger = get_logger("mymodule")
    assert logger.name == "chatui.mymodule"
