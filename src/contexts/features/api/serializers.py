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


class FeatureValidationRequestSerializer(serializers.Serializer):
    key = serializers.CharField(
        max_length=255, 
        help_text="The specific feature flag key to validate access for."
    )
    context = serializers.JSONField(
        required=False,
        default=dict,
        help_text="Context dictionary to override server-side context."
    )


class FeatureCacheClearSerializer(serializers.Serializer):
    keys = serializers.ListField(
        child=serializers.CharField(max_length=255),
        required=False,
        default=list,
        help_text="List of feature keys to clear from cache. If empty, clears all."
    )
