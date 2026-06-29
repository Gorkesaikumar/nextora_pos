from rest_framework import serializers

from ..models import InAppNotification


class InAppNotificationSerializer(serializers.ModelSerializer):

    class Meta:
        model = InAppNotification
        fields = ["id", "title", "body", "is_read", "read_at", "created_at"]
        read_only_fields = ["id", "title", "body", "read_at", "created_at"]
