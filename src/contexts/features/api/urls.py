from django.urls import path
from contexts.features.api.views import (
    FeatureEvaluationView,
    SubscriptionFeaturesView,
    EnabledModulesView,
    FeatureLimitsView,
    FeatureValidationView,
    FeatureCacheClearView,
)

app_name = "features"

urlpatterns = [
    path("subscription/", SubscriptionFeaturesView.as_view(), name="subscription-features"),
    path("modules/", EnabledModulesView.as_view(), name="enabled-modules"),
    path("limits/", FeatureLimitsView.as_view(), name="feature-limits"),
    path("evaluate/", FeatureEvaluationView.as_view(), name="evaluate"),
    path("validate/", FeatureValidationView.as_view(), name="validate"),
    path("cache/clear/", FeatureCacheClearView.as_view(), name="cache-clear"),
]
