"""Unit tests for enterprise print queue retry mechanisms."""
import uuid
import socket
from decimal import Decimal
import pytest
from unittest.mock import patch, MagicMock

from contexts.ordering.models import PrintJob, Order
from contexts.ordering.domain.enums import PrintJobStatus, PrintJobType, OrderStatus, OrderType
from contexts.ordering.tasks import retry_failed_print_jobs
from contexts.catalog.models.routing import Printer
from shared.tenancy import set_current_tenant
from shared.tenancy.context import clear_current_tenant


@pytest.fixture
def print_queue_test_data(db, active_tenant):
    set_current_tenant(active_tenant.id)
    
    order = Order.objects.create(
        tenant=active_tenant,
        location_id=uuid.uuid4(),
        order_number="ORD-PQ-100",
        status=OrderStatus.SETTLED,
        type=OrderType.DINE_IN,
        customer_name="Queue Tester",
        subtotal=Decimal("50.00"),
        total=Decimal("50.00"),
    )

    printer = Printer.objects.create(
        tenant=active_tenant,
        name="Mock_Paper_Out",
        ip_address="192.168.1.200",
        port=9100,
        is_active=True,
        status="online"
    )

    yield order, printer
    clear_current_tenant()


@pytest.mark.django_db
def test_execute_print_job_simulates_paper_out_error(active_tenant, print_queue_test_data):
    order, printer = print_queue_test_data
    
    job = PrintJob.objects.create(
        tenant=active_tenant,
        order=order,
        job_type=PrintJobType.CUSTOMER_RECEIPT,
        status=PrintJobStatus.PENDING,
        content_text="TEST RECEIPT",
        content_escpos=b"MOCK ESCPOS",
        retry_count=0
    )

    # Mock socket connection success, but printer logic throws "Paper Out" 
    with patch("socket.create_connection", return_value=MagicMock()):
        from contexts.ordering.services.printing import execute_print_job
        result = execute_print_job(job)

        assert result is False
        
        job.refresh_from_db()
        assert job.status == PrintJobStatus.RETRYING
        assert job.retry_count == 1
        assert "Paper Out" in job.error_message


@pytest.mark.django_db
def test_execute_print_job_fails_after_max_retries(active_tenant, print_queue_test_data):
    order, printer = print_queue_test_data
    
    job = PrintJob.objects.create(
        tenant=active_tenant,
        order=order,
        job_type=PrintJobType.CUSTOMER_RECEIPT,
        status=PrintJobStatus.RETRYING,
        content_text="TEST RECEIPT",
        content_escpos=b"MOCK ESCPOS",
        retry_count=4  # One retry left before FAILED
    )

    with patch("socket.create_connection", side_effect=socket.timeout("Socket timed out")):
        from contexts.ordering.services.printing import execute_print_job
        execute_print_job(job)

        job.refresh_from_db()
        assert job.status == PrintJobStatus.FAILED  # Reached max retries (5)
        assert job.retry_count == 5


@pytest.mark.django_db
def test_retry_failed_print_jobs_celery_task(active_tenant, print_queue_test_data):
    order, printer = print_queue_test_data

    # Setup a normal printer so it passes
    printer.name = "Normal Printer"
    printer.save()
    
    job1 = PrintJob.objects.create(
        tenant=active_tenant,
        order=order,
        job_type=PrintJobType.CUSTOMER_RECEIPT,
        status=PrintJobStatus.RETRYING,
        content_text="TEST 1",
        content_escpos=b"MOCK",
        retry_count=2
    )

    job2 = PrintJob.objects.create(
        tenant=active_tenant,
        order=order,
        job_type=PrintJobType.KOT_TICKET,
        status=PrintJobStatus.PENDING,
        content_text="TEST 2",
        content_escpos=b"MOCK",
        retry_count=0
    )

    job3_failed = PrintJob.objects.create(
        tenant=active_tenant,
        order=order,
        job_type=PrintJobType.RESTAURANT_RECEIPT,
        status=PrintJobStatus.FAILED,
        content_text="TEST 3",
        content_escpos=b"MOCK",
        retry_count=5
    )

    # Run celery background task
    with patch("socket.create_connection", return_value=MagicMock()):
        retry_failed_print_jobs()

    # Verify job1 and job2 were retried and are now PRINTED
    job1.refresh_from_db()
    job2.refresh_from_db()
    job3_failed.refresh_from_db()

    assert job1.status == PrintJobStatus.PRINTED
    assert job2.status == PrintJobStatus.PRINTED
    
    # job3 was FAILED, should not be picked up by auto-retry
    assert job3_failed.status == PrintJobStatus.FAILED
