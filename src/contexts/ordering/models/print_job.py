"""PrintJob model — queues, stores, and tracks automated thermal receipt and KOT print jobs."""
import uuid
from django.db import models
from django.db.models import Q
from contexts.ordering.domain.enums import PrintJobStatus, PrintJobType
from shared.tenancy.models import TenantAwareModel


class PrintJob(TenantAwareModel):
    order = models.ForeignKey(
        "ordering.Order",
        on_delete=models.CASCADE,
        related_name="print_jobs",
    )
    invoice = models.ForeignKey(
        "ordering.Invoice",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs",
    )
    kot = models.ForeignKey(
        "ordering.KOT",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="print_jobs",
    )
    job_type = models.CharField(
        max_length=30,
        choices=PrintJobType.choices,
    )
    status = models.CharField(
        max_length=20,
        choices=PrintJobStatus.choices,
        default=PrintJobStatus.PENDING,
    )
    content_text = models.TextField(help_text="Formatted ASCII text for thermal roll display.")
    content_escpos = models.BinaryField(help_text="Raw ESC/POS byte stream for printer hardware.")
    retry_count = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    printed_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "print_job"
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "order", "job_type"],
                condition=Q(is_deleted=False, kot__isnull=True),
                name="uq_print_job__receipt_once",
            ),
            models.UniqueConstraint(
                fields=["tenant", "order", "kot", "job_type"],
                condition=Q(is_deleted=False, kot__isnull=False),
                name="uq_print_job__kot_once",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.get_job_type_display()} for Order {self.order_id} ({self.status})"
