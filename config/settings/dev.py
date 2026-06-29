"""Development settings.

Optimised for fast feedback and debuggability. Deliberately does NOT import
security.py — local http, relaxed cookies, debug toolbar. Production hardening
must never leak into dev (and vice versa).
"""
from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]  # noqa: S104  (dev only)

INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE.insert(  # noqa: F405
    0, "debug_toolbar.middleware.DebugToolbarMiddleware"
)
INTERNAL_IPS = ["127.0.0.1"]

# Show full email content in console rather than sending it.
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Eager Celery is OPTIONAL in dev; default keeps the real broker so behaviour
# matches prod. Flip CELERY_TASK_ALWAYS_EAGER=true to run tasks inline.
CELERY_TASK_ALWAYS_EAGER = env.bool(  # noqa: F405
    "CELERY_TASK_ALWAYS_EAGER", default=False
)

# Relaxed throttles so local testing isn't rate-limited.
REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {  # noqa: F405
    "anon": "1000/min",
    "user": "10000/min",
}
