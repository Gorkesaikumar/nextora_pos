import uuid

from django.db import models

from shared.infrastructure.models.base import TimeStampedModel, UUIDModel


class OutboxEventStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    IN_PROGRESS = "in_progress", "In Progress"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"


class OutboxEvent(UUIDModel, TimeStampedModel):
    """Stores events as part of the same DB transaction that modified the business entities."""

    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=255, db_index=True)
    event_version = models.PositiveIntegerField(default=1)
    payload = models.JSONField()
    status = models.CharField(
        max_length=20,
        choices=OutboxEventStatus.choices,
        default=OutboxEventStatus.PENDING,
        db_index=True,
    )

    class Meta:
        app_label = "shared"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["status", "created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} ({self.status})"


class EventConsumption(models.Model):
    """Tracks processed events to guarantee idempotency (at-least-once delivery handling)."""

    event_id = models.UUIDField(db_index=True)
    handler_name = models.CharField(max_length=255)
    processed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "shared"
        unique_together = (("event_id", "handler_name"),)

    def __str__(self):
        return f"Event {self.event_id} -> {self.handler_name}"


class DeadLetterEvent(UUIDModel, TimeStampedModel):
    """Stores events that have permanently failed after max retries."""

    event_id = models.UUIDField(db_index=True)
    tenant_id = models.UUIDField(null=True, blank=True, db_index=True)
    event_type = models.CharField(max_length=255)
    handler_name = models.CharField(max_length=255)
    error_message = models.TextField()
    stack_trace = models.TextField(null=True, blank=True)
    failed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "shared"
        ordering = ["-failed_at"]

    def __str__(self):
        return f"DLQ: {self.event_type} -> {self.handler_name}"
