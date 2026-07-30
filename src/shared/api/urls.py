"""Shared API URL Configuration."""
from django.urls import path

from shared.api.health import RESTHealthCheckView

app_name = "shared_api"

urlpatterns = [
    path("health/", RESTHealthCheckView.as_view(), name="api-health"),
]
