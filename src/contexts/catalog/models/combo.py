"""Combo Offers and Promotional Bundles."""
from django.db import models
from django.utils import timezone

from contexts.catalog.domain.enums import (
    ComboOfferType, 
    ComboStatus,
    CustomerEligibility,
    UsageLimitType
)
from shared.tenancy.models import TenantAwareModel


class ComboOffer(TenantAwareModel):
    """A combo deal or promotion (e.g. Lunch Combo, Buy 1 Get 1)."""
    name = models.CharField(max_length=160)
    internal_code = models.CharField(max_length=64, blank=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="catalog/combos/", null=True, blank=True)
    
    status = models.CharField(
        max_length=20, choices=ComboStatus.choices, default=ComboStatus.DRAFT
    )
    offer_type = models.CharField(
        max_length=30, choices=ComboOfferType.choices, default=ComboOfferType.FIXED_PRICE
    )
    priority = models.PositiveIntegerField(
        default=0, help_text="Higher priority offers apply first in auto-detection"
    )
    
    # Value (Depends on offer_type. e.g. Fixed Price = 299.00, Percentage = 15.00)
    discount_value = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    # Availability Rules
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    
    # JSON array of weekday ints [0,1,2,3,4,5,6] (Monday=0)
    available_days = models.JSONField(default=list, blank=True)
    
    # JSON array of order types ['dine_in', 'takeaway', 'delivery']
    order_types = models.JSONField(default=list, blank=True)

    # Advanced Eligibility Rules
    min_order_value = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        help_text="Minimum cart subtotal required to unlock this offer"
    )
    min_cart_items = models.PositiveIntegerField(
        default=0, help_text="Minimum total items required in the cart"
    )
    customer_eligibility = models.CharField(
        max_length=20, 
        choices=CustomerEligibility.choices, 
        default=CustomerEligibility.ALL
    )
    
    # Example format: [{"product_id": "<uuid>", "min_qty": 2}]
    eligibility_products = models.JSONField(default=list, blank=True)
    
    # Example format: [{"category_id": "<uuid>", "min_qty": 1}]
    eligibility_categories = models.JSONField(default=list, blank=True)
    
    # Usage Limits
    usage_limit_type = models.CharField(
        max_length=20,
        choices=UsageLimitType.choices,
        default=UsageLimitType.UNLIMITED
    )
    usage_limit_value = models.PositiveIntegerField(
        default=0, help_text="Limit value (e.g., 1 for once per order, 5 for daily limit)"
    )
    current_uses = models.PositiveIntegerField(default=0, help_text="Total overall redemptions")

    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "combo_offer"
        ordering = ["sort_order", "name"]

    def __str__(self) -> str:
        return self.name

    @property
    def is_currently_available(self) -> bool:
        if self.status != ComboStatus.ACTIVE:
            return False
            
        now = timezone.now()
        local_date = timezone.localdate(now)
        local_time = timezone.localtime(now).time()
        
        if self.start_date and local_date < self.start_date:
            return False
        if self.end_date and local_date > self.end_date:
            return False
            
        if self.start_time and local_time < self.start_time:
            return False
        if self.end_time and local_time > self.end_time:
            return False
            
        if self.available_days:
            if local_date.weekday() not in self.available_days:
                return False
                
        return True


class ComboGroup(TenantAwareModel):
    """A selection group within a Combo (e.g. 'Choose 1 Burger', 'Choose 2 Sides')."""
    combo = models.ForeignKey(ComboOffer, on_delete=models.CASCADE, related_name="groups")
    name = models.CharField(max_length=120)
    
    min_selections = models.PositiveIntegerField(default=1)
    max_selections = models.PositiveIntegerField(default=1)
    
    sort_order = models.PositiveIntegerField(default=0)
    
    class Meta(TenantAwareModel.Meta):
        db_table = "combo_group"
        ordering = ["sort_order"]

    def __str__(self) -> str:
        return f"{self.combo.name} - {self.name}"


class ComboGroupItem(TenantAwareModel):
    """A specific product allowed in a ComboGroup, with an optional upgrade surcharge."""
    group = models.ForeignKey(ComboGroup, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("catalog.Product", on_delete=models.CASCADE)
    
    # Optional extra cost to select this premium item in the combo
    upgrade_surcharge = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    
    sort_order = models.PositiveIntegerField(default=0)

    class Meta(TenantAwareModel.Meta):
        db_table = "combo_group_item"
        ordering = ["sort_order"]
        constraints = [
            models.UniqueConstraint(
                fields=["group", "product"], 
                condition=models.Q(is_deleted=False),
                name="uq_combo_group_item"
            )
        ]

    def __str__(self) -> str:
        return f"{self.group.name} - {self.product.name}"
