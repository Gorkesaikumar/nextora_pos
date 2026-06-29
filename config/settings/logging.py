"""Logging configuration fragment.

Builds a Django LOGGING dict with two selectable formats:

  * "json"    — structured one-line-per-event logs for production. Machine
                parseable by Loki/ELK/CloudWatch; carries request_id + tenant.
  * "console" — human-friendly colored-ish output for local development.

Keeping this in its own module (SRP) means the logging policy can be reviewed
and changed without touching the rest of the settings.
"""
from typing import Any


def build_logging_config(level: str = "INFO", fmt: str = "json") -> dict[str, Any]:
    handler = "json" if fmt == "json" else "console"

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            # Custom JSON formatter lives in the shared kernel so it is reusable
            # by Celery workers and management commands too.
            "json": {
                "()": "shared.infrastructure.logging.formatters.JSONFormatter",
            },
            "console": {
                "format": "%(asctime)s %(levelname)-8s %(name)s "
                "[req=%(request_id)s] %(message)s",
            },
        },
        "filters": {
            # Injects request_id / tenant_id into every record (defaults to '-'
            # when outside a request, e.g. in a Celery task or mgmt command).
            "context": {
                "()": "shared.infrastructure.logging.filters.ContextFilter",
            },
        },
        "handlers": {
            "json": {
                "class": "logging.StreamHandler",
                "formatter": "json",
                "filters": ["context"],
            },
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "console",
                "filters": ["context"],
            },
        },
        "root": {"handlers": [handler], "level": level},
        "loggers": {
            "django": {"handlers": [handler], "level": level, "propagate": False},
            "django.request": {
                "handlers": [handler],
                "level": "WARNING",
                "propagate": False,
            },
            # Silence noisy SQL unless explicitly debugging.
            "django.db.backends": {
                "handlers": [handler],
                "level": "WARNING",
                "propagate": False,
            },
            "celery": {"handlers": [handler], "level": level, "propagate": False},
            "nextora": {"handlers": [handler], "level": level, "propagate": False},
        },
    }
