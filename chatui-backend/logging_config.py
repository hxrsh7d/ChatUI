"""
Centralized logging setup.

LOG_FORMAT=json gives structured, machine-parseable log lines (one JSON
object per line) -- useful if you're shipping logs somewhere for
aggregation. The default, LOG_FORMAT=text, is a plain human-readable line,
better for reading chatui-backend-output.log directly during development.

Never logs Authorization headers, API keys, full request bodies, or
document contents -- only method/path/status/timing and short error
messages that are already safe to show the frontend.
"""

from __future__ import annotations

import json
import logging
import sys

import config


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "time": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class TextFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        extra = getattr(record, "extra_fields", None)
        if extra:
            suffix = " ".join(f"{k}={v}" for k, v in extra.items())
            return f"{base} | {suffix}"
        return base


def setup_logging() -> None:
    root = logging.getLogger("chatui")
    if root.handlers:
        return  # already configured (e.g. module re-imported under pytest/reload)

    root.setLevel(config.LOG_LEVEL)
    handler = logging.StreamHandler(sys.stdout)
    if config.LOG_FORMAT == "json":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(TextFormatter("%(asctime)s %(levelname)-8s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"chatui.{name}")
