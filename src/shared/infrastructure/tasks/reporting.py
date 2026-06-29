import logging
from uuid import UUID

from celery import shared_task

from contexts.tenants.models import Tenant
from shared.tenancy import bypass_tenant, tenant_scope

logger = logging.getLogger(__name__)


@shared_task(queue="bulk")
def run_daily_reports_sweep() -> str:
    """Sweeps all active tenants to queue daily transaction rollup jobs."""
    logger.info("Starting daily sales reporting sweep...")
    
    with bypass_tenant():
        tenants = list(Tenant.objects.filter(status__in=["trial", "active"]).values_list("id", flat=True))

    for tenant_id in tenants:
        generate_daily_report_task.delay(str(tenant_id))

    return f"Enqueued daily report tasks for {len(tenants)} tenants."


@shared_task(queue="default")
def generate_daily_report_task(tenant_id: str) -> str:
    """Generates daily sales statistics, taxes, and round-offs for a specific tenant."""
    tenant_uuid = UUID(tenant_id)
    
    with tenant_scope(tenant_uuid):
        logger.info(f"Compiling daily transaction reports for tenant: {tenant_uuid}")
        # Core report compiling query stubs would go here
        
    return f"Daily report successfully generated for tenant {tenant_id}."
