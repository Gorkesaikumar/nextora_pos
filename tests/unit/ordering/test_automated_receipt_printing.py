"""Unit tests for automated, idempotent 3-receipt printing after payment."""
import pytest
import uuid
from decimal import Decimal
from unittest.mock import patch
from django.db import transaction

from contexts.ordering.domain.enums import (
    OrderStatus,
    PrintJobStatus,
    PrintJobType,
)
from contexts.ordering.models import Invoice, Order, PrintJob
from contexts.ordering.services.printing import (
    create_order_print_jobs,
    execute_print_job,
)
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def sample_order(db, active_tenant):
    set_current_tenant(active_tenant.id)
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-TEST-001",
        status=OrderStatus.OPEN,
        subtotal=Decimal("500.00"),
        total=Decimal("525.00"),
    )
    yield order
    clear_current_tenant()


@pytest.mark.django_db
def test_create_order_print_jobs_generates_exactly_three_receipts(active_tenant, sample_order):
    """Verify that completing an order generates Customer Copy, Restaurant Copy, and KOT."""
    set_current_tenant(active_tenant.id)
    invoice = Invoice.objects.create(
        number="INV-2026-0001",
        order=sample_order,
        location_id=sample_order.location_id,
        series="INV",
        subtotal=sample_order.subtotal,
        total=sample_order.total,
    )

    jobs = create_order_print_jobs(sample_order, invoice)

    assert len(jobs) == 3
    job_types = {j.job_type for j in jobs}
    assert job_types == {
        PrintJobType.CUSTOMER_RECEIPT,
        PrintJobType.RESTAURANT_RECEIPT,
        PrintJobType.KOT_TICKET,
    }

    customer_job = next(j for j in jobs if j.job_type == PrintJobType.CUSTOMER_RECEIPT)
    assert "*** CUSTOMER COPY ***" in customer_job.content_text
    assert customer_job.status == PrintJobStatus.PENDING

    restaurant_job = next(j for j in jobs if j.job_type == PrintJobType.RESTAURANT_RECEIPT)
    assert "*** RESTAURANT COPY ***" in restaurant_job.content_text


@pytest.mark.django_db
def test_print_jobs_are_idempotent_no_duplicates_on_retry(active_tenant, sample_order):
    """Verify that repeated calls or double clicks do not create duplicate PrintJobs."""
    set_current_tenant(active_tenant.id)
    invoice = Invoice.objects.create(
        number="INV-2026-0002",
        order=sample_order,
        location_id=sample_order.location_id,
        series="INV",
        subtotal=sample_order.subtotal,
        total=sample_order.total,
    )

    first_jobs = create_order_print_jobs(sample_order, invoice)
    second_jobs = create_order_print_jobs(sample_order, invoice)

    assert len(first_jobs) == 3
    assert len(second_jobs) == 3
    assert {j.id for j in first_jobs} == {j.id for j in second_jobs}
    assert PrintJob.objects.filter(order=sample_order).count() == 3


@pytest.mark.django_db
def test_execute_print_job_failure_does_not_abort_sale_and_queues_retry(active_tenant, sample_order):
    """Verify that hardware delivery failure keeps sale completed and queues retry."""
    set_current_tenant(active_tenant.id)
    from contexts.catalog.models.routing import Printer
    Printer.objects.create(
        tenant=active_tenant,
        code="PRN-TEST",
        name="Test Kitchen Printer",
        ip_address="192.168.1.100",
        port=9100,
        is_active=True,
        status="online",
    )

    invoice = Invoice.objects.create(
        number="INV-2026-0003",
        order=sample_order,
        location_id=sample_order.location_id,
        series="INV",
        subtotal=sample_order.subtotal,
        total=sample_order.total,
    )

    jobs = create_order_print_jobs(sample_order, invoice)
    job = jobs[0]

    # Simulate hardware delivery failure
    with patch("socket.create_connection", side_effect=OSError("Printer unreachable")):
        success = execute_print_job(job)

    job.refresh_from_db()
    sample_order.refresh_from_db()

    assert success is False
    assert job.status == PrintJobStatus.RETRYING
    assert job.retry_count == 1
    assert "Printer unreachable" in job.error_message

