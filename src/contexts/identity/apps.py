from django.apps import AppConfig


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.identity"
    label = "identity"  # short label; AUTH_USER_MODEL = "identity.User"
    verbose_name = "Identity & Access"

    def ready(self) -> None:
        # Connect RBAC cache-invalidation signals.
        from contexts.identity import signals  # noqa: F401
