"""POS Printer Configuration — per-terminal printer assignment.

Printer settings are persisted at the terminal (POS device) level because
thermal printers are physically connected to a local Windows computer.
This prevents one local printer from being assigned to every business terminal.
"""
from django.db import models
from shared.tenancy.models import TenantAwareModel


class POSPrinterConfig(TenantAwareModel):
    """Per-terminal printer configuration for POS receipt printing.

    Stores the stable printer identity (printer_name) selected by the user
    for their POS terminal. The actual printer status is always fetched live
    from the Print Service at http://127.0.0.1:8989.
    """
    terminal_id = models.UUIDField(
        null=True, blank=True,
        help_text="POS terminal device UUID. None = global/location-level config.",
    )
    location_id = models.UUIDField(
        null=True, blank=True,
        help_text="Store/outlet UUID. Used when terminal_id is not set.",
    )
    printer_name = models.CharField(
        max_length=255, blank=True,
        help_text="Stable printer identity from Print Service (e.g. Windows printer queue name).",
    )
    printer_display_name = models.CharField(
        max_length=255, blank=True,
        help_text="Human-readable printer name for display in the UI.",
    )
    connection_type = models.CharField(
        max_length=50, blank=True,
        help_text="Cached connection type (USB, Network, Bluetooth, Local).",
    )
    is_active = models.BooleanField(default=True)
    auto_print = models.BooleanField(
        default=True,
        help_text="Automatically print receipt after successful transaction.",
    )
    paper_width = models.CharField(
        max_length=10,
        choices=[("80mm", "80mm"), ("58mm", "58mm")],
        default="80mm",
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "pos_printer_config"
        verbose_name = "POS Printer Configuration"
        verbose_name_plural = "POS Printer Configurations"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "terminal_id"],
                condition=models.Q(is_deleted=False, terminal_id__isnull=False),
                name="uq_pos_printer_config__terminal",
            ),
        ]

    def __str__(self) -> str:
        return f"PrinterConfig(terminal={self.terminal_id}, printer={self.printer_name})"
