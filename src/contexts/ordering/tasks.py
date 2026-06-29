import logging
from uuid import UUID

from celery import shared_task
from django.db import OperationalError

from contexts.ordering.services.invoice_service import settle_and_invoice
from shared.tenancy.scope import tenant_scope

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    queue="critical",  # Placed in the critical queue for financial/payment paths
    max_retries=5,
    default_retry_delay=5,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
)
def generate_invoice_task(self, order_id: str, tenant_id: str) -> str:
    """Asynchronously issues a tax invoice for an order.

    Retries on DB OperationalError (locking contentions). Once generated,
    triggers the PDF compiler task.
    """
    tenant_uuid = UUID(tenant_id)
    order_uuid = UUID(order_id)

    with tenant_scope(tenant_uuid):
        logger.info(f"Generating invoice for order {order_uuid}...")
        invoice = settle_and_invoice(order_uuid)

        # Trigger PDF generation after invoice record is successfully committed
        from shared.infrastructure.tasks.pdf import export_pdf_task

        file_key = f"invoices/{invoice.number}.pdf"
        html_content = (
            f"<h1>Invoice {invoice.number}</h1>"
            f"<p>Restaurant: {invoice.tenant.name}</p>"
            f"<p>Date: {invoice.issued_at:%Y-%m-%d}</p>"
            f"<p>Total: {invoice.total}</p>"
        )

        export_pdf_task.delay(
            tenant_id=tenant_id,
            file_key=file_key,
            html_content=html_content,
        )

    return str(invoice.id)
