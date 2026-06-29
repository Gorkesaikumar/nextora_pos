"""Order (bill/ticket) with its line items and modifiers."""
from django.db import models
from django.utils import timezone

from contexts.ordering.domain.enums import (
    DiscountType,
    ItemStatus,
    OrderStatus,
    OrderType,
)
from shared.tenancy.models import TenantAwareModel

_MONEY = {"max_digits": 12, "decimal_places": 2, "default": 0}


class Order(TenantAwareModel):
    location_id = models.UUIDField()
    order_number = models.CharField(max_length=30, blank=True)
    table_id = models.UUIDField(null=True, blank=True)
    type = models.CharField(
        max_length=12, choices=OrderType.choices, default=OrderType.DINE_IN
    )
    status = models.CharField(
        max_length=10, choices=OrderStatus.choices,
        default=OrderStatus.OPEN, db_index=True,
    )
    customer_name = models.CharField(max_length=160, blank=True)
    customer_phone = models.CharField(max_length=20, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    is_interstate = models.BooleanField(default=False)

    # Discount / service charge inputs.
    discount_type = models.CharField(
        max_length=8, choices=DiscountType.choices, default=DiscountType.NONE
    )
    discount_value = models.DecimalField(**_MONEY)
    service_charge_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    # Computed snapshot.
    subtotal = models.DecimalField(**_MONEY)
    discount_amount = models.DecimalField(**_MONEY)
    service_charge_amount = models.DecimalField(**_MONEY)
    taxable_amount = models.DecimalField(**_MONEY)
    cgst = models.DecimalField(**_MONEY)
    sgst = models.DecimalField(**_MONEY)
    igst = models.DecimalField(**_MONEY)
    cess = models.DecimalField(**_MONEY)
    tax_amount = models.DecimalField(**_MONEY)
    round_off = models.DecimalField(**_MONEY)
    total = models.DecimalField(**_MONEY)
    paid_amount = models.DecimalField(**_MONEY)
    due_amount = models.DecimalField(**_MONEY)

    # Lineage for split / merge.
    split_from = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="splits"
    )
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merges"
    )

    opened_at = models.DateTimeField(default=timezone.now)
    settled_at = models.DateTimeField(null=True, blank=True)
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.CharField(max_length=255, blank=True)
    created_by = models.UUIDField(null=True, blank=True)
    waiter_id = models.UUIDField(null=True, blank=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "order"
        indexes = [
            models.Index(
                fields=["tenant", "location_id", "status"],
                name="ix_order__open",
                condition=models.Q(status="open", is_deleted=False),
            ),
            models.Index(
                fields=["tenant", "customer_phone"],
                name="ix_order__tenant_phone",
            ),
            models.Index(
                fields=["tenant", "opened_at"],
                name="ix_order__tenant_opened",
            ),
        ]

    def __str__(self) -> str:
        return self.order_number or str(self.id)

    @property
    def table_number(self):
        if not self.table_id:
            return None
        from contexts.restaurant.models.layout import DiningTable
        table = DiningTable.objects.filter(id=self.table_id).first()
        return table.number if table else None


class OrderItem(TenantAwareModel):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.UUIDField()
    variant_id = models.UUIDField(null=True, blank=True)
    name_snapshot = models.CharField(max_length=220)
    qty = models.DecimalField(max_digits=8, decimal_places=2, default=1)
    unit_price = models.DecimalField(**_MONEY)
    modifiers_total = models.DecimalField(**_MONEY)
    line_discount = models.DecimalField(**_MONEY)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    cess_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    hsn_code = models.CharField(max_length=8, blank=True)
    kitchen_station_id = models.UUIDField(null=True, blank=True)
    line_subtotal = models.DecimalField(**_MONEY)
    line_total = models.DecimalField(**_MONEY)
    status = models.CharField(
        max_length=8, choices=ItemStatus.choices, default=ItemStatus.ACTIVE
    )
    notes = models.CharField(max_length=255, blank=True)
    kot = models.ForeignKey(
        "ordering.KOT", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="routed_items",
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "order_item"
        indexes = [
            models.Index(fields=["order"], name="ix_order_item__order"),
        ]

    def __str__(self) -> str:
        return f"{self.name_snapshot} x{self.qty}"


class OrderItemModifier(TenantAwareModel):
    item = models.ForeignKey(
        OrderItem, on_delete=models.CASCADE, related_name="modifiers"
    )
    modifier_id = models.UUIDField()
    name_snapshot = models.CharField(max_length=160)
    price_delta = models.DecimalField(**_MONEY)
    qty = models.DecimalField(max_digits=8, decimal_places=2, default=1)

    class Meta(TenantAwareModel.Meta):
        db_table = "order_item_modifier"
