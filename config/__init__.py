"""Ensure the Celery app is imported when Django starts so that the
``@shared_task`` decorator and autodiscovery use the configured app.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
