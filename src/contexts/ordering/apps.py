from django.apps import AppConfig


class OrderingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.ordering"
    label = "ordering"
    verbose_name = "Ordering & POS Billing"
