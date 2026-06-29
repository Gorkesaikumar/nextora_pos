"""Ordering error hierarchy."""


class OrderingError(Exception):
    pass


class OrderNotFound(OrderingError):
    pass


class OrderNotOpen(OrderingError):
    """Operation requires an open order."""


class OutstandingDue(OrderingError):
    """Cannot settle: balance remaining."""


class OverRefund(OrderingError):
    """Refund would exceed the captured net amount."""


class InvoiceExists(OrderingError):
    pass


class InvoiceNumberingError(OrderingError):
    """Could not allocate a free invoice number after repeated attempts."""
