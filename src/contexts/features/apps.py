from django.apps import AppConfig

class FeaturesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.features"
    verbose_name = "Feature Flags"

    def ready(self):
        import contexts.features.signals  # noqa
