"""Ensure the Celery app is imported when Django starts so that the
``@shared_task`` decorator and autodiscovery use the configured app.

The import is lazy to allow Django management commands (e.g. makemigrations,
migrate, runserver) to work when Celery is not installed or when running
outside the full Docker stack.
"""
try:
    from .celery import app as celery_app

    __all__ = ("celery_app",)
except ImportError:
    # Celery not installed — this is fine for development / CI without Docker.
    # The @shared_task decorator and Celery Beat scheduler won't be available,
    # but all synchronous Django commands will work normally.
    celery_app = None  # type: ignore[assignment]
    __all__ = ("celery_app",)
