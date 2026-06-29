"""Inventory domain enumerations."""
from django.db import models


class StockMovementType(models.TextChoices):
    PURCHASE = "purchase", "Purchase Receipt"
    SALE = "sale", "Sale Deduction"
    TRANSFER_IN = "transfer_in", "Transfer In"
    TRANSFER_OUT = "transfer_out", "Transfer Out"
    ADJUSTMENT_ADD = "adjustment_add", "Adjustment (Add)"
    ADJUSTMENT_REMOVE = "adjustment_remove", "Adjustment (Remove)"
    DAMAGED = "damaged", "Damaged / Spoilage"
    RETURN_SUPPLIER = "return_supplier", "Return to Supplier"
    RETURN_CUSTOMER = "return_customer", "Customer Return"
    OPENING = "opening", "Opening Balance"


class TransferStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    IN_TRANSIT = "in_transit", "In Transit"
    RECEIVED = "received", "Received"
    CANCELLED = "cancelled", "Cancelled"


class PurchaseOrderStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    SENT = "sent", "Sent to Supplier"
    PARTIALLY_RECEIVED = "partially_received", "Partially Received"
    RECEIVED = "received", "Fully Received"
    CANCELLED = "cancelled", "Cancelled"


class AlertType(models.TextChoices):
    LOW_STOCK = "low_stock", "Low Stock"
    OUT_OF_STOCK = "out_of_stock", "Out of Stock"
    EXPIRY_SOON = "expiry_soon", "Expiring Soon"
    EXPIRED = "expired", "Expired"
    DAMAGED = "damaged", "Damaged Stock"


class AlertStatus(models.TextChoices):
    OPEN = "open", "Open"
    ACKNOWLEDGED = "acknowledged", "Acknowledged"
    RESOLVED = "resolved", "Resolved"
