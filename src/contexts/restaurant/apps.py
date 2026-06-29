"""Restaurant bounded context — app configuration."""
from django.apps import AppConfig


class RestaurantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.restaurant"
    label = "restaurant"
    verbose_name = "Restaurant Management"
