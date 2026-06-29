from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.catalog"
    label = "catalog"
    verbose_name = "Catalog & Products"

    def ready(self) -> None:
        # Importing the events package registers the domain-event handlers
        # with the shared event registry.
        from contexts.catalog import events  # noqa: F401
