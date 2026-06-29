from django.urls import path
from contexts.features.api.views import FeatureEvaluationView

app_name = "features"

urlpatterns = [
    path("evaluate/", FeatureEvaluationView.as_view(), name="evaluate"),
]
