"""Stock movement ledger — double-entry ledger for all inventory changes."""
from django.db import models

from contexts.inventory.domain.enums import StockMovementType
from shared.tenancy.models import TenantAwareModel


class StockMovement(TenantAwareModel):
    """
    Immutable ledger record of every stock quantity change. Every operation
    (purchase, sale, transfer, adjustment, damage) creates a movement record.
    The sum of all movements for an InventoryItem equals quantity_on_hand.

    Never delete or mutate a movement; reverse it with an opposing movement instead.
    """
    inventory_item = models.ForeignKey(
        "inventory.InventoryItem",
        on_delete=models.PROTECT,
        related_name="movements",
    )
    batch = models.ForeignKey(
        "inventory.Batch",
        on_delete=models.PROTECT,
        null=True, blank=True,
        related_name="movements",
    )
    movement_type = models.CharField(
        max_length=30, choices=StockMovementType.choices
    )
    quantity = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="Signed quantity: positive = in, negative = out"
    )
    unit_cost = models.DecimalField(
        max_digits=14, decimal_places=4, default=0,
        help_text="Cost per unit at the time of movement"
    )

    # Running balance snapshot — denormalized for fast reporting.
    balance_after = models.DecimalField(
        max_digits=14, decimal_places=3,
        help_text="Quantity on hand after this movement was applied"
    )

    # Soft cross-context references for traceability
    reference_type = models.CharField(
        max_length=50, blank=True,
        help_text="Type of originating document, e.g., 'purchase_order', 'sale_order', 'transfer'"
    )
    reference_id = models.UUIDField(
        null=True, blank=True,
        help_text="UUID of the originating document"
    )
    reference_number = models.CharField(
        max_length=50, blank=True,
        help_text="Human-readable ref number, e.g., PO-2024-001"
    )

    notes = models.TextField(blank=True)

    # The actor who triggered the movement
    performed_by_id = models.UUIDField(
        null=True, blank=True,
        help_text="Cross-context soft FK to identity.User"
    )

    # Exactly-once guard for at-least-once callers (redelivered events / retried
    # tasks). Caller-supplied per logical operation, e.g. "consume:<order_line>"
    # or "po_receipt:<receipt_id>". Empty when the operation needs no dedup.
    idempotency_key = models.CharField(
        max_length=120, blank=True, default="",
        help_text="Caller-supplied key; partial-unique guards against double-apply.",
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "stock_movement"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["inventory_item", "-created_at"],
                name="ix_movement__item_date",
            ),
            models.Index(
                fields=["tenant", "movement_type", "-created_at"],
                name="ix_movement__tenant_type_date",
            ),
        ]
        constraints = [
            # Defense-in-depth: even if the service-level guard races, the DB
            # rejects a second movement carrying the same idempotency key.
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(is_deleted=False) & ~models.Q(idempotency_key=""),
                name="uq_movement__idempotency",
            ),
        ]

    def __str__(self) -> str:
        sign = "+" if self.quantity >= 0 else ""
        return f"{self.movement_type}: {sign}{self.quantity} ({self.inventory_item.product_sku})"
