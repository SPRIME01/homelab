"""
Python structured logger implementation with a shared schema.

This module provides a dependency-free logger that mirrors the behaviour of
the Node.js logger and powers the end-to-end structured logging tests.
"""

from __future__ import annotations

import contextvars
import json
import os
import re
import sys
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

# -----------------------------------------------------------------------------
# Configuration helpers
# -----------------------------------------------------------------------------

LEVEL_WEIGHTS: Dict[str, int] = {
    "debug": 10,
    "info": 20,
    "warn": 30,
    "warning": 30,
    "error": 40,
}

OPTIONAL_ROOT_FIELDS = [
    "request_id",
    "user_hash",
    "source",
    "duration_ms",
    "status_code",
    "tags",
    "trace_id",
    "span_id",
]

LEVEL_COLORS = {
    "debug": "\033[36m",
    "info": "\033[32m",
    "warn": "\033[33m",
    "error": "\033[31m",
}
COLOR_RESET = "\033[0m"
COLOR_DIM = "\033[2m"
COLOR_BOLD = "\033[1m"

_event_id_counter = 0
_event_id_lock = threading.Lock()


def generate_event_id() -> str:
    """Generate a monotonic event identifier."""
    global _event_id_counter
    with _event_id_lock:
        _event_id_counter += 1
        return f"evt_{int(datetime.now(timezone.utc).timestamp() * 1000)}_{_event_id_counter}"


def get_version() -> str:
    """Read the project version from pyproject.toml if available."""
    try:
        pyproject_path = Path.cwd() / "pyproject.toml"
        if pyproject_path.exists():
            for line in pyproject_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("version"):
                    return line.split("=", 1)[1].strip().strip("\"'")
    except Exception:
        pass
    return "0.0.0"


def serialize_error(error: Optional[BaseException]) -> Optional[Dict[str, Any]]:
    """Convert an exception into a serialisable dictionary.

    Uses an allowlist approach for safety and redacts sensitive information.
    Only copies attributes that are explicitly allowed and safe for logging.
    """
    if not error:
        return None

    # Allowlist of safe attributes to copy from the exception
    # These attributes are generally safe to log and don't contain sensitive data
    SAFE_ATTRIBUTES = [
        "args",      # Exception arguments
        "code",      # Exception code (often used in HTTP/API errors)
        "errno",     # System error number
        "message",   # Error message
        "filename",  # Source filename (if applicable)
        "lineno",    # Line number in source file (if applicable)
    ]

    # Patterns that might indicate sensitive information
    SENSITIVE_PATTERNS = [
        r'password', r'passwd', r'pwd',
        r'token', r'key', r'secret',
        r'credential', r'auth',
        r'ssn', r'social_security',
        r'credit_card', r'cc_number',
        r'account_number', r'account_num',
    ]

    def _redact_sensitive_data(value: Any) -> Any:
        """Check if a value matches sensitive patterns and redact if needed."""
        if isinstance(value, str):
            # Check for sensitive patterns (case insensitive)
            for pattern in SENSITIVE_PATTERNS:
                if re.search(pattern, value, re.IGNORECASE):
                    return "[REDACTED]"
        return value

    serialized: Dict[str, Any] = {
        "name": type(error).__name__,
        "message": str(error) or "Error",
    }

    if hasattr(error, "__dict__"):
        for key, value in error.__dict__.items():
            # Skip private attributes (starting with "_")
            if key.startswith("_"):
                continue

            # Only include attributes in our allowlist
            if key in SAFE_ATTRIBUTES:
                # Redact sensitive data in the value
                serialized[key] = _redact_sensitive_data(value)

    stack = "".join(
        traceback.format_exception(error.__class__, error, error.__traceback__)
    )
    if stack:
        serialized["stack"] = stack

    return serialized


config: Dict[str, Any] = {
    "service": os.getenv("HOMELAB_SERVICE", "unknown-service"),
    "environment": os.getenv("HOMELAB_ENVIRONMENT", "development"),
    "log_target": os.getenv("HOMELAB_LOG_TARGET", "stdout").lower(),
    "log_level": os.getenv("HOMELAB_LOG_LEVEL", "info").lower(),
    "force_pretty": os.getenv("HOMELAB_FORCE_PRETTY", "").lower() == "true",
    "version": get_version(),
}

use_pretty = (
    config["log_target"] == "stdout"
    and (config["force_pretty"] or sys.stdout.isatty())
)


# -----------------------------------------------------------------------------
# Structured logger implementation
# -----------------------------------------------------------------------------

class StructuredLogger:
    """Logger that enforces the common schema and output formats."""

    def __init__(
        self,
        config: Dict[str, Any],
        bindings: Optional[Dict[str, Any]] = None,
        pretty: bool = False,
        colorize: bool = False,
        stream=None,
    ) -> None:
        self.config = config
        self.bindings = bindings or {}
        self.pretty = pretty
        self.colorize = colorize
        self._stream = stream
        self.level_threshold = LEVEL_WEIGHTS.get(config["log_level"], 20)

    # ------------------------------------------------------------------
    # Logger factories
    # ------------------------------------------------------------------
    def child(self, **bindings: Any) -> "StructuredLogger":
        merged = {**self.bindings}
        for key, value in bindings.items():
            if value is not None:
                merged[key] = value
        return StructuredLogger(
            self.config,
            merged,
            pretty=self.pretty,
            colorize=self.colorize,
            stream=self._stream,
        )

    def create_logger(
        self,
        service: Optional[str] = None,
        environment: Optional[str] = None,
        version: Optional[str] = None,
        category: Optional[str] = None,
    ) -> "StructuredLogger":
        return self.child(
            service=service or self.config["service"],
            environment=environment or self.config["environment"],
            version=version or self.config["version"],
            category=category or "app",
        )

    def bind(self, **bindings: Any) -> "StructuredLogger":
        """Compatibility helper matching structlog's bind method."""
        return self.child(**bindings)

    def with_category(self, category: str) -> "StructuredLogger":
        return self.child(category=category)

    def bind_trace(
        self, trace_id: Optional[str], span_id: Optional[str] = None
    ) -> "StructuredLogger":
        return self.child(trace_id=trace_id, span_id=span_id)

    def with_request(
        self, request_id: Optional[str], user_hash: Optional[str] = None
    ) -> "StructuredLogger":
        return self.child(request_id=request_id, user_hash=user_hash)

    # ------------------------------------------------------------------
    # Core logging
    # ------------------------------------------------------------------
    def log(self, level: str, message: str, **kwargs: Any) -> None:
        level = level.lower()
        if LEVEL_WEIGHTS.get(level, 0) < self.level_threshold:
            return

        extra = dict(kwargs)
        entry = self._prepare_entry(level, message, extra)
        self._emit(entry)

    def debug(self, message: str, **kwargs: Any) -> None:
        self.log("debug", message, **kwargs)

    def info(self, message: str, **kwargs: Any) -> None:
        self.log("info", message, **kwargs)

    def warn(self, message: str, **kwargs: Any) -> None:
        self.log("warn", message, **kwargs)

    def error(self, message: str, **kwargs: Any) -> None:
        self.log("error", message, **kwargs)

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------
    def log_request(
        self,
        method: str,
        url: str,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = {
            "method": method,
            "url": url,
        }
        if user_agent:
            context["userAgent"] = user_agent
        context.update(kwargs)
        self.info(
            "HTTP Request",
            request_id=request_id,
            context=context,
        )

    def log_response(
        self,
        method: str,
        url: str,
        status_code: int,
        duration_ms: int,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        context = {
            "method": method,
            "url": url,
            **kwargs,
        }
        self.info(
            "HTTP Response",
            request_id=request_id,
            status_code=status_code,
            duration_ms=duration_ms,
            context=context,
        )

    def log_error(self, error: BaseException, **kwargs: Any) -> None:
        context = dict(kwargs.pop("context", {}) or {})
        context.update(kwargs)
        error_payload = serialize_error(error)
        if error_payload:
            context["err"] = error_payload
        context.setdefault("error_type", type(error).__name__)
        context.setdefault("error_message", str(error) or "Error occurred")
        message = str(error) or "Error occurred"
        self.error(message, context=context)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prepare_entry(
        self, level: str, message: str, extra: Dict[str, Any]
    ) -> Dict[str, Any]:
        context_arg = extra.pop("context", None)
        context: Dict[str, Any] = {}
        if isinstance(context_arg, dict):
            context.update(context_arg)

        entry: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "message": message or "",
            "service": self.bindings.get("service", self.config["service"]),
            "environment": self.bindings.get("environment", self.config["environment"]),
            "version": self.bindings.get("version", self.config["version"]),
            "category": self.bindings.get("category", "app"),
            "event_id": extra.pop("event_id", generate_event_id()),
        }

        for field in OPTIONAL_ROOT_FIELDS:
            bound_value = self.bindings.get(field)
            if bound_value is not None:
                entry[field] = bound_value

        for field in OPTIONAL_ROOT_FIELDS:
            if field in extra:
                value = extra.pop(field)
                if value is not None:
                    entry[field] = value
                elif field in entry:
                    entry.pop(field, None)

        for key, value in list(extra.items()):
            if value is not None:
                context[key] = value

        entry["context"] = context if context else {}

        for key in list(entry.keys()):
            if entry[key] is None:
                entry.pop(key, None)

        return entry

    def _emit(self, entry: Dict[str, Any]) -> None:
        stream = self._stream or sys.stdout
        if self.pretty:
            output = self._format_pretty(entry)
        else:
            output = json.dumps(entry, separators=(",", ":"), ensure_ascii=False)
        stream.write(output + os.linesep)
        stream.flush()

    def _format_pretty(self, entry: Dict[str, Any]) -> str:
        timestamp = entry.get("timestamp", "")
        try:
            if timestamp:
                dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
                timestamp = dt.strftime("%H:%M:%S")
        except Exception:
            pass

        level = (entry.get("level") or "info").lower()
        message = entry.get("message", "")
        service = entry.get("service", "")
        category = entry.get("category", "")

        parts = []
        if timestamp:
            parts.append(self._apply_color(timestamp, COLOR_DIM))
        parts.append(self._apply_color(level.upper(), LEVEL_COLORS.get(level, "")))
        if service:
            parts.append(self._apply_color(service, COLOR_BOLD))
        if category and category != "app":
            parts.append(category)

        trace_id = entry.get("trace_id")
        if trace_id:
            parts.append(f"[{str(trace_id)[:8]}...]")

        if "duration_ms" in entry:
            parts.append(f"({entry['duration_ms']}ms)")

        parts.append("-")
        parts.append(message)

        line = " ".join(part for part in parts if part)

        context = entry.get("context") or {}
        if context:
            context_json = json.dumps(context, indent=2, ensure_ascii=False)
            dimmed = self._apply_color(context_json, COLOR_DIM)
            return f"{line}\n{dimmed}"

        return line

    def _apply_color(self, text: str, code: str) -> str:
        if not self.colorize or not code:
            return text
        return f"{code}{text}{COLOR_RESET}"


# -----------------------------------------------------------------------------
# Global logger and utilities
# -----------------------------------------------------------------------------

# Context variable to store the current logger
_current_logger: contextvars.ContextVar[Optional[StructuredLogger]] = contextvars.ContextVar(
    "current_logger", default=None
)

def get_logger() -> StructuredLogger:
    """Get the current logger from context or return the default logger."""
    return _current_logger.get() or logger

logger = StructuredLogger(
    config,
    {
        "service": config["service"],
        "environment": config["environment"],
        "version": config["version"],
        "category": "app",
    },
    pretty=use_pretty,
    colorize=use_pretty and sys.stdout.isatty(),
)


class LoggerUtils:
    """Utility helpers mirroring the Node.js logger API."""

    @staticmethod
    def create_logger(
        service: Optional[str] = None,
        environment: Optional[str] = None,
        version: Optional[str] = None,
        category: Optional[str] = None,
    ) -> StructuredLogger:
        return logger.create_logger(service, environment, version, category)

    @staticmethod
    def with_category(category: str) -> StructuredLogger:
        return logger.with_category(category)

    @staticmethod
    def bind_trace(trace_id: Optional[str], span_id: Optional[str] = None) -> StructuredLogger:
        return logger.bind_trace(trace_id, span_id)

    @staticmethod
    def with_request(request_id: Optional[str], user_hash: Optional[str] = None) -> StructuredLogger:
        return logger.with_request(request_id, user_hash)

    @staticmethod
    def with_span(span_context: Dict[str, str]):
        def decorator(fn):
            def wrapper(*args, **kwargs):
                trace_id = span_context.get("trace_id")
                span_id = span_context.get("span_id")
                span_logger = logger.bind_trace(trace_id, span_id)
                token = _current_logger.set(span_logger)
                try:
                    return fn(*args, **kwargs)
                finally:
                    _current_logger.reset(token)

            return wrapper

        return decorator

    @staticmethod
    def log_request(
        method: str,
        url: str,
        request_id: Optional[str] = None,
        user_agent: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        logger.log_request(method, url, request_id, user_agent, **kwargs)

    @staticmethod
    def log_response(
        method: str,
        url: str,
        status_code: int,
        duration_ms: int,
        request_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        logger.log_response(method, url, status_code, duration_ms, request_id, **kwargs)

    @staticmethod
    def log_error(error: BaseException, **kwargs: Any) -> None:
        logger.log_error(error, **kwargs)


# Convenience exports mirroring common logging APIs
debug = logger.debug
info = logger.info
warn = logger.warn
error = logger.error


__all__ = ["logger", "LoggerUtils", "config", "serialize_error", "generate_event_id", "get_logger"]
