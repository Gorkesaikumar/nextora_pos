"""Enterprise Inventory — apps configuration."""
from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.inventory"
    label = "inventory"
    verbose_name = "Enterprise Inventory"

    def ready(self) -> None:
        # Importing the events package registers the domain-event handlers
        # with the shared event registry.
        from contexts.inventory import events  # noqa: F401
