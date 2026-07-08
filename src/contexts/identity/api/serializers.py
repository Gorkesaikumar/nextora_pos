"""REST serializers for enterprise authentication, session inspection, and profile management."""
from django.contrib.auth import get_user_model
from rest_framework import serializers

from contexts.identity.models.session import UserSession

User = get_user_model()


class UserProfileSerializer(serializers.ModelSerializer):
    """Exposes public user profile using UUID primary key exclusively."""

    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "full_name",
            "is_active",
            "is_email_verified",
            "token_version",
            "last_login_ip",
            "created_at",
        ]
        read_only_fields = ["id", "email", "token_version", "last_login_ip", "created_at"]


class UserSessionSerializer(serializers.ModelSerializer):
    """Serializes active device session ledger."""

    id = serializers.UUIDField(read_only=True)

    class Meta:
        model = UserSession
        fields = [
            "id",
            "device_type",
            "ip_address",
            "user_agent",
            "browser",
            "operating_system",
            "last_active_at",
            "is_active",
            "revoked_at",
        ]
        read_only_fields = fields


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=128)
    new_password = serializers.CharField(min_length=12)
