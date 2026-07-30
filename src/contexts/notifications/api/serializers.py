"""Serializers for Notifications API."""
from rest_framework import serializers

from contexts.notifications.models import (
    Notification,
    NotificationTemplate,
    InAppNotification,
    ChannelType,
    NotificationStatus
)


class NotificationTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationTemplate
        fields = [
            "id",
            "name",
            "language",
            "channel",
            "subject",
            "body_template",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class NotificationSerializer(serializers.ModelSerializer):
    template_name = serializers.CharField(source="template.name", read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id",
            "channel",
            "recipient",
            "status",
            "template",
            "template_name",
            "context_data",
            "scheduled_for",
            "sent_at",
            "retry_count",
            "last_error",
            "external_id",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "sent_at",
            "retry_count",
            "last_error",
            "external_id",
            "created_at",
        ]


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = [
            "id",
            "user_id",
            "title",
            "body",
            "is_read",
            "read_at",
            "created_at",
        ]
        read_only_fields = ["id", "user_id", "title", "body", "created_at"]


class SendNotificationSerializer(serializers.Serializer):
    channel = serializers.ChoiceField(choices=ChannelType.choices)
    recipient = serializers.JSONField(help_text="Recipient details, e.g., email address, phone, or token")
    template_name = serializers.CharField(required=False, allow_blank=True, help_text="Optional template name")
    context_data = serializers.JSONField(required=False, default=dict)
    scheduled_for = serializers.DateTimeField(required=False, allow_null=True)
    language = serializers.CharField(required=False, default="en")


class SendReceiptSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    channel = serializers.ChoiceField(choices=[ChannelType.EMAIL, ChannelType.SMS, ChannelType.WHATSAPP])
    recipient = serializers.CharField(help_text="Email or Phone Number")
