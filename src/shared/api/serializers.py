"""Base serializers for Nextora POS API.

Ensures standardized representations (e.g., date formats, fields) across contexts.
"""
from rest_framework import serializers


class BaseSerializer(serializers.Serializer):
    """Base standard serializer for non-model payloads."""

    pass


class BaseModelSerializer(serializers.ModelSerializer):
    """Base ModelSerializer for all model-backed entities.

    Ensures UUID primary keys are rendered as strings and datetimes are uniform.
    """

    # Reusable read-only fields that are common across models
    id = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")
    updated_at = serializers.DateTimeField(read_only=True, format="%Y-%m-%dT%H:%M:%SZ")

    # If the model inherits from TenantAwareModel, we make tenant read-only
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "tenant" in self.fields:
            self.fields["tenant"].read_only = True
