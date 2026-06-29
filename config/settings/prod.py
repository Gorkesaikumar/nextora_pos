"""Production settings.

Imports base + security hardening. Adds Sentry, fails fast on missing config,
and assumes TLS terminates at Nginx with X-Forwarded-Proto set.
"""
import sentry_sdk
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.django import DjangoIntegration

from .base import *  # noqa: F403
from .security import *  # noqa: F403

DEBUG = False

# ALLOWED_HOSTS must be explicitly provided in prod — empty means misconfig.
if not ALLOWED_HOSTS:  # noqa: F405
    raise RuntimeError("DJANGO_ALLOWED_HOSTS must be set in production.")

# --- Observability --------------------------------------------------------
SENTRY_DSN = env("SENTRY_DSN", default="")  # noqa: F405
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=env("SENTRY_ENVIRONMENT", default="production"),  # noqa: F405
        integrations=[DjangoIntegration(), CeleryIntegration()],
        traces_sample_rate=env.float(  # noqa: F405
            "SENTRY_TRACES_SAMPLE_RATE", default=0.0
        ),
        send_default_pii=False,  # never ship PII to the error tracker
    )

# --- Prometheus metrics ---------------------------------------------------
# Handled conditionally in base.py to support safe local development dev/prod parity.

# --- Email (real SMTP via env) --------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405
EMAIL_USE_TLS = True
