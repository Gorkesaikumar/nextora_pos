from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.tenants"
    label = "tenants"
    verbose_name = "Tenants & White-Label"

    def ready(self):
        import contexts.tenants.signals  # noqa
