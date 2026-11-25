import contextvars
import json
import logging
import re
from datetime import UTC, datetime
from typing import Any

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default=""
)
request_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")

SENSITIVE_KEYS = {
    "password",
    "password_hash",
    "secret",
    "jwt_secret",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "gemini_api_key",
    "groq_api_key",
    "bank_account",
    "account_number",
    "iban",
    "ifsc",
}

TOKEN_PATTERN = re.compile(r"(Bearer\s+)[A-Za-z0-9\-_\.]+", re.IGNORECASE)


def redact_value(key: str, value: Any) -> Any:
    low = key.lower()
    if any(s in low for s in SENSITIVE_KEYS):
        return "[REDACTED]"
    if isinstance(value, dict):
        return {k: redact_value(str(k), v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_value(key, v) for v in value]
    if isinstance(value, str):
        return TOKEN_PATTERN.sub(r"\1[REDACTED]", value)
    return value


class StructuredJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_value("message", record.getMessage()),
            "correlation_id": correlation_id_var.get() or None,
            "request_id": request_id_var.get() or None,
        }
        extra_fields = getattr(record, "extra_fields", None)
        if isinstance(extra_fields, dict):
            for k, v in extra_fields.items():
                payload[k] = redact_value(str(k), v)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))
    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJsonFormatter())
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
