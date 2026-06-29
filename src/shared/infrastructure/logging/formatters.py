"""Structured JSON log formatter.

Emits one JSON object per log record with a stable schema so downstream log
pipelines (Loki / ELK / CloudWatch) can index without regex parsing.

Intentionally dependency-free (std-lib json) — the logging path must be cheap
and must never fail to import.
"""
import json
import logging
from datetime import UTC, datetime

# Attributes that are part of LogRecord by default — anything NOT in here that
# a caller passes via `extra=` is treated as a structured field and included.
_RESERVED = set(
    logging.makeLogRecord({}).__dict__.keys()
) | {"request_id", "tenant_id", "asctime", "message"}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "-"),
            "tenant_id": getattr(record, "tenant_id", "-"),
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Promote any structured extras (logger.info("x", extra={"order_id": ...})).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value

        return json.dumps(payload, default=str, ensure_ascii=False)
