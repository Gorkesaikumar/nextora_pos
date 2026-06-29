from django.apps import AppConfig

class SearchConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.search"
    label = "search"
    verbose_name = "Universal Search"

    def ready(self):
        # Register search providers on load
        import contexts.search.impl  # noqa
        # Register signals for cache invalidation
        import contexts.search.signals  # noqa
