from django.apps import AppConfig


class BillingConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "contexts.billing"
    label = "billing"
    verbose_name = "Billing & Subscriptions"

    def ready(self) -> None:
        self._register_usage_providers()

    @staticmethod
    def _register_usage_providers() -> None:
        """Wire live-count usage providers. Counters cover the rest.

        Branches/storage/invoices use UsageCounter rows; employees is a live
        count of active memberships so it always reflects reality.
        """
        import uuid

        from contexts.billing.domain import metrics
        from contexts.billing.services import usage

        def count_employees(tenant_id: uuid.UUID) -> int:
            from contexts.identity.models import Membership

            return (
                Membership.objects.filter(tenant_id=tenant_id, is_active=True)
                .values("user")
                .distinct()
                .count()
            )

        usage.register_provider(metrics.EMPLOYEES, count_employees)
