"""Thermal receipt rendering and automated print job dispatch.

Uses modular printer adapters (Network, USB) and receipt templates
(CustomerReceipt, KOT).
"""
import logging
from django.db import transaction
from django.utils import timezone

from contexts.ordering.domain.enums import PrintJobStatus, PrintJobType
from contexts.ordering.models import KOT, Invoice, Order, PrintJob

from contexts.ordering.services.printer_adapters import get_printer_adapter
from contexts.ordering.services.print_templates import CustomerReceiptTemplate, KOTTemplate

logger = logging.getLogger(__name__)


def create_order_print_jobs(
    order: Order,
    invoice: Invoice,
    kots: list[KOT] | None = None,
    paper_width: str = "80mm",
) -> list[PrintJob]:
    """Create persistent PrintJobs for Customer Copy, Restaurant Copy, and KOT."""
    if kots is None:
        kots = list(order.kots.all())

    jobs = []
    
    receipt_tpl = CustomerReceiptTemplate(paper_width=paper_width)
    kot_tpl = KOTTemplate(paper_width=paper_width)

    # 1. Customer Receipt Copy
    customer_job, _ = PrintJob.objects.get_or_create(
        order=order,
        invoice=invoice,
        job_type=PrintJobType.CUSTOMER_RECEIPT,
        defaults={
            "tenant": order.tenant,
            "content_text": receipt_tpl.render_text(invoice, ""),
            "content_escpos": receipt_tpl.render_escpos(invoice, ""),
            "status": PrintJobStatus.PENDING,
        },
    )
    jobs.append(customer_job)

    # 2. Restaurant Accounting Copy (Archived)
    restaurant_job, _ = PrintJob.objects.get_or_create(
        order=order,
        invoice=invoice,
        job_type=PrintJobType.RESTAURANT_RECEIPT,
        defaults={
            "tenant": order.tenant,
            "content_text": receipt_tpl.render_text(invoice, "RESTAURANT COPY"),
            "content_escpos": receipt_tpl.render_escpos(invoice, "RESTAURANT COPY"),
            "status": PrintJobStatus.PENDING,
        },
    )
    jobs.append(restaurant_job)

    # 3. KOT Copy (for each KOT generated or first KOT if multiple)
    if kots:
        for kot in kots:
            kot_job, _ = PrintJob.objects.get_or_create(
                order=order,
                kot=kot,
                job_type=PrintJobType.KOT_TICKET,
                defaults={
                    "tenant": order.tenant,
                    "content_text": kot_tpl.render_text(kot),
                    "content_escpos": kot_tpl.render_escpos(kot),
                    "status": PrintJobStatus.PENDING,
                },
            )
            jobs.append(kot_job)
    else:
        # Fallback if order had no items requiring KOT or already printed
        kot_job, _ = PrintJob.objects.get_or_create(
            order=order,
            job_type=PrintJobType.KOT_TICKET,
            defaults={
                "tenant": order.tenant,
                "content_text": f"KITCHEN ORDER TICKET\nOrder #{order.order_number}\nNo KOT items\n",
                "content_escpos": b"\x1b\x40KITCHEN ORDER TICKET\nNo KOT items\n\n\n\x1d\x56\x00",
                "status": PrintJobStatus.PENDING,
            },
        )
        jobs.append(kot_job)

    return jobs


def execute_print_job(job: PrintJob) -> bool:
    """Execute a single thermal print job against configured printer hardware."""
    if job.status == PrintJobStatus.PRINTED:
        return True

    # Mark as printing
    job.status = PrintJobStatus.PRINTING
    job.save(update_fields=["status", "updated_at"])

    MAX_RETRIES = 5

    try:
        from contexts.catalog.models.routing import Printer
        from contexts.catalog.domain.enums import PrinterKind
        
        # Route logic: KOTs go to Kitchen printers, Receipts go to Receipt printers
        if job.job_type == PrintJobType.KOT_TICKET:
            # Check if KOT has a specific station mapped to a printer, otherwise fallback to any Kitchen printer
            printer = Printer.objects.filter(is_active=True, kind=PrinterKind.KITCHEN).first()
        else:
            printer = Printer.objects.filter(is_active=True, kind=PrinterKind.RECEIPT).first()

        # Fallback to ANY online printer if specific kind is not found
        if not printer:
            printer = Printer.objects.filter(is_active=True, status="online").first()

        if not printer:
            raise ConnectionError("No online printer configured for this job type.")

        adapter = get_printer_adapter(printer)
        adapter.print_bytes(bytes(job.content_escpos))
        
        job.status = PrintJobStatus.PRINTED
        job.printed_at = timezone.now()
        job.error_message = ""
        job.save(update_fields=["status", "printed_at", "error_message", "updated_at"])
        return True

    except Exception as exc:
        error_msg = f"Printer Error: {exc}"
        logger.warning(f"PrintJob {job.id} failed: {error_msg}")
        job.retry_count += 1
        job.status = PrintJobStatus.RETRYING if job.retry_count < MAX_RETRIES else PrintJobStatus.FAILED
        job.error_message = error_msg
        job.save(update_fields=["status", "retry_count", "error_message", "updated_at"])
        return False


def dispatch_print_jobs_on_commit(jobs: list[PrintJob]) -> None:
    """Schedule print jobs to execute ONLY after the database transaction successfully commits."""
    job_ids = [job.id for job in jobs]

    def _run_after_commit() -> None:
        for jid in job_ids:
            job = PrintJob.objects.filter(id=jid).first()
            if job:
                execute_print_job(job)

    transaction.on_commit(_run_after_commit)


# Maintain old signature for compatibility just in case
def get_archived_restaurant_copy(invoice: Invoice) -> PrintJob | None:
    return PrintJob.objects.filter(
        invoice=invoice,
        job_type=PrintJobType.RESTAURANT_RECEIPT,
    ).first()

# Mocking the resolved names for compatibility where other files might import them directly
# In a real scenario, everything should just use the new template engine.
def _resolve_cashier_name(order: Order) -> str:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_id = order.created_by or order.waiter_id
    if user_id:
        user = User.objects.filter(id=user_id).first()
        if user:
            return user.full_name or user.get_username()
    return "POS Terminal #1"
