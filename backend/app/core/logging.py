"""Structured logging.

Two hard rules, both driven by the privacy requirement in section 28 of the
brief: legal questions, retrieved passages and generated answers never reach the
logs. Only identifiers, counts, scores and durations do.

`bind_request_id` puts a request id on every record emitted while handling a
request, so a chat turn can be reconstructed from usage_logs + logs without ever
storing its content.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)

# Fields that must never be serialized into a log record, whatever a caller
# passes in `extra`. Enforced centrally rather than trusted at each call site.
_FORBIDDEN_FIELDS = frozenset(
    {
        "message_content",
        "query",
        "question",
        "answer",
        "prompt",
        "context",
        "chunk_content",
        "excerpt",
        "password",
        "api_key",
        "token",
        "authorization",
        "secret",
    }
)

# LogRecord's own attributes, so `extra` keys can be told apart from them.
_RESERVED = frozenset(
    logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()
) | {"message", "asctime", "taskName"}


def new_request_id() -> str:
    return uuid.uuid4().hex


def bind_request_id(request_id: str | None = None) -> str:
    """Attach a request id to the current context and return it."""
    rid = request_id or new_request_id()
    _request_id.set(rid)
    return rid


def get_request_id() -> str | None:
    return _request_id.get()


def _extras(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _RESERVED and not key.startswith("_")
    }


class RedactionFilter(logging.Filter):
    """Drops forbidden keys before any formatter sees them."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__):
            if key.lower() in _FORBIDDEN_FIELDS:
                record.__dict__[key] = "[redacted]"
        return True


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if rid := get_request_id():
            payload["request_id"] = rid
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        payload.update(_extras(record))
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Human-readable variant for local development."""

    def format(self, record: logging.LogRecord) -> str:
        stamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S")
        rid = get_request_id()
        prefix = f"{stamp} {record.levelname:<7} {record.name}"
        if rid:
            prefix += f" [{rid[:8]}]"
        line = f"{prefix} {record.getMessage()}"
        if extras := _extras(record):
            line += " " + " ".join(f"{k}={v}" for k, v in extras.items())
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging() -> None:
    """Install handlers on the root logger. Idempotent."""
    formatter: logging.Formatter = (
        JsonFormatter() if settings.LOG_FORMAT == "json" else ConsoleFormatter()
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(settings.LOG_LEVEL)

    # uvicorn duplicates records through its own handlers; route them here.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True

    # Access logs would record full request URIs, which can carry a legal
    # question as a query string.
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
