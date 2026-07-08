"""Ordering enumerations."""
from django.db import models


class OrderType(models.TextChoices):
    DINE_IN = "dine_in"
    TAKEAWAY = "takeaway"
    DELIVERY = "delivery"


class OrderStatus(models.TextChoices):
    OPEN = "open"
    SETTLED = "settled"
    VOID = "void"


class ItemStatus(models.TextChoices):
    ACTIVE = "active"
    VOID = "void"


class DiscountType(models.TextChoices):
    NONE = "none"
    FLAT = "flat"
    PERCENT = "percent"


class PaymentMethod(models.TextChoices):
    CASH = "cash"
    CARD = "card"
    UPI = "upi"
    CREDIT = "credit"


class PaymentKind(models.TextChoices):
    PAYMENT = "payment"
    REFUND = "refund"


class PaymentStatus(models.TextChoices):
    CAPTURED = "captured"
    VOID = "void"


class KOTStatus(models.TextChoices):
    NEW = "new"
    PREPARING = "preparing"
    READY = "ready"
    SERVED = "served"
    CANCELLED = "cancelled"


class InvoiceStatus(models.TextChoices):
    ISSUED = "issued"
    VOID = "void"


class PrintJobType(models.TextChoices):
    CUSTOMER_RECEIPT = "customer_receipt", "Customer Copy"
    RESTAURANT_RECEIPT = "restaurant_receipt", "Restaurant Copy"
    KOT_TICKET = "kot_ticket", "Kitchen Order Ticket"


class PrintJobStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PRINTING = "printing", "Printing"
    PRINTED = "printed", "Printed"
    FAILED = "failed", "Failed"
    RETRYING = "retrying", "Retrying"

