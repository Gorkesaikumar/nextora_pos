"""Thermal receipt rendering and automated print job dispatch.

Uses the centralized PrintServiceClient to communicate with the Nextora Print Service
running at http://127.0.0.1:8989. The old browser-based printing via window.print()
is replaced with server-side Print Service calls for reliable physical printing.
"""
import logging
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from contexts.ordering.domain.enums import PrintJobStatus, PrintJobType
from contexts.ordering.models import KOT, Invoice, Order, PrintJob
from contexts.ordering.services.print_service_client import PrintServiceClient
from contexts.ordering.services.print_templates import KOTTemplate
from contexts.ordering.services.receipt_data_mapper import build_receipt_payload, render_receipt_html

logger = logging.getLogger(__name__)


def create_order_print_jobs(
    order: Order,
    invoice: Invoice,
    kots: list[KOT] | None = None,
    paper_width: str = "80mm",
) -> list[PrintJob]:
    """Create persistent PrintJobs for Customer Copy, Restaurant Copy, and KOT.
    
    These jobs are stored in the database for later reference but actual printing
    is delegated to the Print Service via dispatch_print_jobs.
    """
    if kots is None:
        kots = list(order.kots.all())

    jobs = []
    
    kot_tpl = KOTTemplate(paper_width=paper_width)

    # 1. Customer Receipt Copy
    customer_job, _ = PrintJob.objects.get_or_create(
        order=order,
        invoice=invoice,
        job_type=PrintJobType.CUSTOMER_RECEIPT,
        defaults={
            "tenant": order.tenant,
            "content_text": render_receipt_html(order, invoice, copy_type="customer", paper_width=paper_width),
            "content_escpos": b"",
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
            "content_text": render_receipt_html(order, invoice, copy_type="restaurant", paper_width=paper_width),
            "content_escpos": b"",
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


def _get_configured_printer_name(order) -> str:
    """Get the configured printer name for a given order's location/terminal.

    Uses the POS terminal's printer configuration if available, otherwise
    falls back to the global default.
    """
    try:
        from contexts.ordering.models.pos_config import POSPrinterConfig
        # First try device/terminal-level config
        terminal_id = getattr(order, "terminal_id", None)
        if terminal_id:
            config = POSPrinterConfig.objects.filter(
                terminal_id=terminal_id,
                is_active=True,
            ).first()
            if config and config.printer_name:
                return config.printer_name

        # Fallback to the first active printer for the tenant
        config = POSPrinterConfig.objects.filter(is_active=True).first()
        if config and config.printer_name:
            return config.printer_name
    except Exception:
        pass
    return ""


def dispatch_to_print_service(
    order: Order,
    invoice: Invoice,
    *,
    printer_name: str = "",
    idempotency_key: str = "",
    paper_width: str = "80mm",
) -> dict:
    """Send a receipt to the Print Service for physical printing.

    This is the NEW primary print dispatch method. It uses the centralized
    PrintServiceClient to send the receipt payload to the local Print Service.

    Returns the Print Service response with job_id and status.
    """
    if not printer_name:
        printer_name = _get_configured_printer_name(order)

    if not printer_name:
        return {
            "success": False,
            "error": "No receipt printer configured. Please select a printer in Printer Settings.",
            "error_code": "NO_PRINTER_CONFIGURED",
        }

    payload_dict = build_receipt_payload(
        order=order,
        invoice=invoice,
        copy_type="customer",
        is_reprint=False,
        paper_width=paper_width,
    )
    html_content = render_receipt_html(
        order=order,
        invoice=invoice,
        copy_type="customer",
        is_reprint=False,
        paper_width=paper_width,
    )

    client = PrintServiceClient()
    result = client.print_receipt(
        printer_name=printer_name,
        receipt_data=payload_dict,
        html=html_content,
        copies=1,
        idempotency_key=idempotency_key,
    )

    if result.success:
        logger.info(
            "Print job submitted: printer='%s' job_id='%s' status='%s'",
            printer_name,
            result.data.get("job_id", "unknown"),
            result.data.get("status", "unknown"),
        )
        # Update local PrintJob records
        _update_print_job_status(order, result.data.get("job_id", ""), PrintJobStatus.PRINTED)
        return {
            "success": True,
            "job_id": result.data.get("job_id", ""),
            "status": result.data.get("status", "queued"),
            "message": "Receipt sent to printer.",
        }
    else:
        logger.warning(
            "Print job FAILED: printer='%s' error='%s'",
            printer_name, result.error,
        )
        _update_print_job_status(order, "", PrintJobStatus.FAILED, error=result.error)
        return {
            "success": False,
            "error": result.error or "Print Service returned an error.",
            "error_code": result.error_code or "PRINT_ERROR",
        }


def _update_print_job_status(order, job_id: str, status: str, error: str = "") -> None:
    """Update the most recent PrintJob records for an order."""
    try:
        jobs = PrintJob.objects.filter(
            order=order,
            job_type=PrintJobType.CUSTOMER_RECEIPT,
        ).order_by("-created_at")[:1]
        for job in jobs:
            job.status = status
            job.error_message = error
            if status == PrintJobStatus.PRINTED:
                job.printed_at = timezone.now()
            job.save(update_fields=["status", "error_message", "printed_at", "updated_at"])
    except Exception as e:
        logger.debug("Could not update PrintJob status: %s", e)


def dispatch_print_jobs_on_commit(jobs: list[PrintJob]) -> None:
    """Schedule print jobs to execute ONLY after the database transaction commits.

    For server-side Print Service integration, this creates the jobs but
    actual printing is handled by the checkout flow calling dispatch_to_print_service().
    """
    # Jobs are stored in DB; printing is triggered from the view layer
    # after the successful response is ready to be sent.
    pass


def execute_print_job(job: PrintJob) -> bool:
    """Execute a single print job (for legacy/retry scenarios).

    Uses the Print Service to send the stored ESC/POS content.
    """
    if job.status == PrintJobStatus.PRINTED:
        return True

    job.status = PrintJobStatus.PRINTING
    job.save(update_fields=["status", "updated_at"])

    try:
        printer_name = _get_configured_printer_name(job.order) or ""
        if not printer_name:
            raise ConnectionError("No printer configured. Please select a printer in Printer Settings.")

        # Build receipt payload from stored order/invoice data
        invoice = job.invoice
        if not invoice:
            invoice = getattr(job.order, "invoice", None)
        if not invoice:
            invoice = job.order.invoice if hasattr(job.order, "invoice") else None

        if invoice:
            copy_t = "customer" if job.job_type == PrintJobType.CUSTOMER_RECEIPT else "restaurant"
            payload_dict = build_receipt_payload(
                order=job.order,
                invoice=invoice,
                copy_type=copy_t,
                is_reprint=True,
            )
            html_content = render_receipt_html(
                order=job.order,
                invoice=invoice,
                copy_type=copy_t,
                is_reprint=True,
            )
            client = PrintServiceClient()
            result = client.print_receipt(
                printer_name=printer_name,
                receipt_data=payload_dict,
                html=html_content,
                copies=1,
            )
        else:
            # Fallback: send the stored ESC/POS content as raw bytes
            client = PrintServiceClient()
            import base64
            raw_result = client._post("/print/raw", payload={
                "printer_name": printer_name,
                "raw_bytes_base64": base64.b64encode(bytes(job.content_escpos)).decode("ascii"),
            })
            success = raw_result.success
            if success:
                job.status = PrintJobStatus.PRINTED
                job.printed_at = timezone.now()
                job.error_message = ""
                job.save(update_fields=["status", "printed_at", "error_message", "updated_at"])
            return success

        if result.success:
            job.status = PrintJobStatus.PRINTED
            job.printed_at = timezone.now()
            job.error_message = ""
            job.save(update_fields=["status", "printed_at", "error_message", "updated_at"])
            return True
        else:
            error_msg = result.error or "Print Service error"
            logger.warning(f"Print job {job.id} failed: {error_msg}")
            job.retry_count += 1
            job.status = PrintJobStatus.RETRYING if job.retry_count < 5 else PrintJobStatus.FAILED
            job.error_message = error_msg
            job.save(update_fields=["status", "retry_count", "error_message", "updated_at"])
            return False

    except Exception as exc:
        error_msg = f"Printer Error: {exc}"
        logger.warning(f"PrintJob {job.id} failed: {error_msg}")
        job.retry_count += 1
        job.status = PrintJobStatus.RETRYING if job.retry_count < 5 else PrintJobStatus.FAILED
        job.error_message = error_msg
        job.save(update_fields=["status", "retry_count", "error_message", "updated_at"])
        return False


# Maintain old signature for compatibility just in case
def get_archived_restaurant_copy(invoice: Invoice) -> PrintJob | None:
    return PrintJob.objects.filter(
        invoice=invoice,
        job_type=PrintJobType.RESTAURANT_RECEIPT,
    ).first()
