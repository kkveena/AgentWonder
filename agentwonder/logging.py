"""Structured logging configuration for AgentWonder.

Provides JSON-formatted structured logs suitable for production use.
Falls back to human-readable console output for local development.

Usage::

    from agentwonder.logging import get_logger
    logger = get_logger(__name__)
    logger.info("workflow started", workflow_id="wf_123", template="sequential")
"""

from __future__ import annotations

import logging
import json
import sys
from datetime import datetime, timezone
from typing import Any


class StructuredFormatter(logging.Formatter):
    """JSON log formatter that outputs structured key-value log lines."""

    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Include extra fields attached via StructuredLogger
        extras = getattr(record, "_structured_extras", None)
        if extras:
            entry.update(extras)
        if record.exc_info and record.exc_info[1]:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, default=str)


class ConsoleFormatter(logging.Formatter):
    """Human-readable formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        extras = getattr(record, "_structured_extras", None)
        extra_str = ""
        if extras:
            extra_str = " " + " ".join(f"{k}={v}" for k, v in extras.items())
        msg = f"{ts} [{record.levelname:>7}] {record.name}: {record.getMessage()}{extra_str}"
        if record.exc_info and record.exc_info[1]:
            msg += "\n" + self.formatException(record.exc_info)
        return msg


class StructuredLogger:
    """Wraps stdlib logger with structured key-value logging support.

    Allows passing keyword arguments that are attached as structured
    fields to the log record::

        logger.info("step completed", step_id="s1", duration_ms=42.5)
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _log(self, level: int, msg: str, **kwargs: Any) -> None:
        if not self._logger.isEnabledFor(level):
            return
        record = self._logger.makeRecord(
            self._logger.name, level, "(structured)", 0, msg, (), None,
        )
        record._structured_extras = kwargs  # type: ignore[attr-defined]
        self._logger.handle(record)

    def debug(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.DEBUG, msg, **kwargs)

    def info(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.INFO, msg, **kwargs)

    def warning(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.WARNING, msg, **kwargs)

    def error(self, msg: str, **kwargs: Any) -> None:
        self._log(logging.ERROR, msg, **kwargs)

    def exception(self, msg: str, **kwargs: Any) -> None:
        """Log at ERROR with exception info from sys.exc_info()."""
        import sys as _sys
        record = self._logger.makeRecord(
            self._logger.name, logging.ERROR, "(structured)", 0,
            msg, (), _sys.exc_info(),
        )
        record._structured_extras = kwargs  # type: ignore[attr-defined]
        self._logger.handle(record)


_configured = False


def configure_logging(
    level: str = "INFO",
    json_output: bool = False,
) -> None:
    """Configure root logging for AgentWonder.

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR).
        json_output: If True, use JSON structured output. Otherwise
            use human-readable console format.
    """
    global _configured
    if _configured:
        return
    _configured = True

    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler(sys.stderr)
    if json_output:
        handler.setFormatter(StructuredFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())
    root.addHandler(handler)


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger for the given module name.

    This is the primary entry point. Use instead of ``logging.getLogger``.
    """
    return StructuredLogger(logging.getLogger(name))
