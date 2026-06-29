from django.db import models
from shared.tenancy.models import TenantAwareModel


class ChannelType(models.TextChoices):
    EMAIL = "email", "Email"
    SMS = "sms", "SMS"
    WHATSAPP = "whatsapp", "WhatsApp"
    PUSH = "push", "Push Notification"
    IN_APP = "in_app", "In-App Notification"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    SCHEDULED = "scheduled", "Scheduled"
    QUEUED = "queued", "Queued"
    SENT = "sent", "Sent"
    DELIVERED = "delivered", "Delivered"
    FAILED = "failed", "Failed"


class NotificationTemplate(TenantAwareModel):
    name = models.CharField(max_length=100)  # e.g. "order.receipt"
    language = models.CharField(max_length=10, default="en")
    channel = models.CharField(max_length=20, choices=ChannelType.choices)
    subject = models.CharField(max_length=255, blank=True)
    body_template = models.TextField()
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "notification_template"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "name", "language", "channel"],
                name="uq_notification_template__tenant_name_lang_channel",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.channel}) - {self.language}"


class Notification(TenantAwareModel):
    channel = models.CharField(max_length=20, choices=ChannelType.choices)
    recipient = models.JSONField(help_text="Recipient details, e.g., email address, phone, or token")
    status = models.CharField(
        max_length=20,
        choices=NotificationStatus.choices,
        default=NotificationStatus.PENDING,
        db_index=True,
    )
    template = models.ForeignKey(
        NotificationTemplate, on_delete=models.SET_NULL, null=True, blank=True
    )
    context_data = models.JSONField(default=dict, blank=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True, db_index=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "notification"
        indexes = [
            models.Index(fields=["status", "scheduled_for"]),
        ]

    def __str__(self) -> str:
        return f"{self.channel} to {self.recipient} ({self.status})"


class InAppNotification(TenantAwareModel):
    user_id = models.UUIDField(db_index=True)
    title = models.CharField(max_length=255)
    body = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "in_app_notification"
        indexes = [
            models.Index(fields=["user_id", "is_read"]),
        ]

    def __str__(self) -> str:
        return f"In-App for {self.user_id} - {self.title}"
