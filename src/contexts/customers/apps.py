from django.apps import AppConfig


class CustomersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.customers"
    label = "customers"
    verbose_name = "Customer Relationship & loyalty"

    def ready(self) -> None:
        # Importing the events package registers the domain-event handlers.
        from contexts.customers import events  # noqa: F401
