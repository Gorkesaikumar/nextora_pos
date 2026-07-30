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


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(min_length=8, required=True)
    confirm_password = serializers.CharField(min_length=8, required=True)

    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Password fields didn't match."})
        return attrs


from shared.api.serializers import BaseModelSerializer
from contexts.identity.models import Membership, Role, Permission


class UserMembershipSerializer(BaseModelSerializer):
    tenant_name = serializers.CharField(source="tenant.name", read_only=True, default=None)
    tenant_slug = serializers.CharField(source="tenant.slug", read_only=True, default=None)
    role_name = serializers.CharField(source="role.name", read_only=True)
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_scope = serializers.CharField(source="role.scope", read_only=True)

    class Meta:
        model = Membership
        fields = [
            "id",
            "tenant",
            "tenant_name",
            "tenant_slug",
            "role",
            "role_name",
            "role_code",
            "role_scope",
        ]


class PermissionSerializer(BaseModelSerializer):
    class Meta:
        model = Permission
        fields = ["id", "code", "name", "description", "module"]


class RoleSerializer(BaseModelSerializer):
    permissions = PermissionSerializer(many=True, read_only=True)

    class Meta:
        model = Role
        fields = [
            "id",
            "code",
            "name",
            "description",
            "scope",
            "is_system",
            "permissions",
        ]
