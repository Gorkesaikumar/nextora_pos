from rest_framework import serializers

class BulkEvaluateRequestSerializer(serializers.Serializer):
    keys = serializers.ListField(
        child=serializers.CharField(max_length=255),
        allow_empty=False,
        help_text="List of feature flag keys to evaluate."
    )
    context = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Context dictionary (e.g. tenant_id, subscription_tier) to override server-side context."
    )
