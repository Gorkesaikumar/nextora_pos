"""Inbound gateway webhook events (global, idempotent).

Stored before processing so a redelivered event (same event_id) is a no-op.
Not tenant-scoped: the event arrives on a platform endpoint and the tenant is
resolved from the payload during processing.
"""
from django.db import models

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class WebhookEvent(UUIDModel, TimeStampedModel):
    class Status(models.TextChoices):
        RECEIVED = "received"
        PROCESSED = "processed"
        FAILED = "failed"
        IGNORED = "ignored"

    provider = models.CharField(max_length=30)
    event_id = models.CharField(max_length=160)
    event_type = models.CharField(max_length=80)
    payload = models.JSONField(default=dict)
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.RECEIVED
    )
    processed_at = models.DateTimeField(null=True, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        db_table = "billing_webhook_event"
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "event_id"],
                name="uq_webhook_event__provider_event",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.provider}:{self.event_type}:{self.event_id}"
