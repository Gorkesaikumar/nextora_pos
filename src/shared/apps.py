from django.apps import AppConfig


class SharedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shared"
    verbose_name = "Shared Kernel"

    def ready(self):
        from shared.infrastructure.monitoring.celery import setup_celery_monitoring
        setup_celery_monitoring()
