"""Celery application factory.

Queue topology (SLA isolation):
  * critical — payments, invoicing, webhooks. Low latency, scaled aggressively.
  * default  — general async work.
  * bulk     — reports, exports, large emails. Throughput over latency.

A flood of nightly report jobs must never delay a payment capture, so they
live on different queues that scale independently.
"""
import os

from celery import Celery
from kombu import Queue

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.prod")

app = Celery("nextora")

# Read CELERY_* settings from Django config (single source of truth).
app.config_from_object("django.conf:settings", namespace="CELERY")

app.conf.task_queues = (
    Queue("critical"),
    Queue("default"),
    Queue("bulk"),
)
app.conf.task_default_queue = "default"

# Discover tasks.py in every installed app.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:  # pragma: no cover
    """Smoke-test task to confirm worker/broker connectivity."""
    print(f"Request: {self.request!r}")
