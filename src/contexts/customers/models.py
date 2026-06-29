from django.db import models

from shared.tenancy.models import TenantAwareModel


class LoyaltyTier(models.TextChoices):
    BRONZE = "bronze", "Bronze"
    SILVER = "silver", "Silver"
    GOLD = "gold", "Gold"
    PLATINUM = "platinum", "Platinum"


class WalletTxType(models.TextChoices):
    DEPOSIT = "deposit", "Deposit"
    PAYMENT = "payment", "Payment"
    REFUND = "refund", "Refund"


class CreditLedgerType(models.TextChoices):
    CHARGE = "charge", "Charge"
    SETTLEMENT = "settlement", "Settlement"


class CouponDiscountType(models.TextChoices):
    PERCENT = "percent", "Percentage Discount"
    FIXED = "fixed", "Fixed Amount Discount"


class Customer(TenantAwareModel):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)
    email = models.EmailField(blank=True)

    # GST / B2B
    gstin = models.CharField(
        max_length=15, blank=True, help_text="Customer GSTIN registration number"
    )
    legal_name = models.CharField(max_length=255, blank=True, help_text="Legal name matching GSTIN")
    state_code = models.CharField(
        max_length=2, blank=True,
        help_text="GST state code for place-of-supply (IGST vs CGST/SGST)",
    )

    # Marketing consent (lawful basis for offers/referral comms — separate from
    # the contractual basis for loyalty).
    accepts_marketing = models.BooleanField(default=False)

    # Loyalty
    loyalty_tier = models.CharField(
        max_length=20, choices=LoyaltyTier.choices, default=LoyaltyTier.BRONZE
    )
    loyalty_points = models.PositiveIntegerField(
        default=0, help_text="Redeemable points balance"
    )
    lifetime_points = models.PositiveIntegerField(
        default=0,
        help_text="Cumulative points ever earned — the tier basis. Redemption "
                  "does NOT reduce this, so spending points never demotes a tier.",
    )

    # Value accounts (projections of their ledgers)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    credit_limit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, help_text="Maximum store credit limit"
    )
    outstanding_credit = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00, help_text="Current outstanding unpaid credit"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "customer"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "phone"],
                condition=models.Q(is_deleted=False),
                name="uq_customer__tenant_phone",
            )
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.phone})"


class LoyaltyProgram(TenantAwareModel):
    """Per-tenant loyalty configuration (one row per tenant).

    Replaces the hard-coded earn rule and tier thresholds: every value here is
    tenant-editable, per the "no hardcoded business rules" rule.
    """
    earn_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=1,
        help_text="Points earned per 1 unit of currency spent",
    )
    redeem_value = models.DecimalField(
        max_digits=8, decimal_places=4, default=0,
        help_text="Currency value of 1 point at redemption",
    )
    silver_threshold = models.PositiveIntegerField(default=500)
    gold_threshold = models.PositiveIntegerField(default=2000)
    platinum_threshold = models.PositiveIntegerField(default=5000)
    points_expiry_days = models.PositiveIntegerField(
        null=True, blank=True, help_text="Points expire after N days (null = never)"
    )

    class Meta(TenantAwareModel.Meta):
        db_table = "loyalty_program"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant"],
                condition=models.Q(is_deleted=False),
                name="uq_loyalty_program__tenant",
            )
        ]

    def tier_for(self, lifetime_points: int) -> str:
        if lifetime_points >= self.platinum_threshold:
            return LoyaltyTier.PLATINUM
        if lifetime_points >= self.gold_threshold:
            return LoyaltyTier.GOLD
        if lifetime_points >= self.silver_threshold:
            return LoyaltyTier.SILVER
        return LoyaltyTier.BRONZE

    def __str__(self) -> str:
        return f"LoyaltyProgram(earn={self.earn_rate}, redeem={self.redeem_value})"


class PointsLedger(TenantAwareModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="points_ledger")
    points = models.IntegerField(help_text="Points earned (+) or redeemed (-)")
    reason = models.CharField(max_length=255)
    order_id = models.UUIDField(null=True, blank=True, help_text="Soft reference to order")
    idempotency_key = models.CharField(max_length=120, blank=True, default="")

    class Meta(TenantAwareModel.Meta):
        db_table = "customer_points_ledger"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(is_deleted=False) & ~models.Q(idempotency_key=""),
                name="uq_points_ledger__idempotency",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer.name}: {self.points:+} pts ({self.reason})"


class WalletTransaction(TenantAwareModel):
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="wallet_transactions"
    )
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Amount deposited (+) or spent (-)"
    )
    tx_type = models.CharField(max_length=20, choices=WalletTxType.choices)
    order_id = models.UUIDField(null=True, blank=True, help_text="Soft reference to order")
    idempotency_key = models.CharField(max_length=120, blank=True, default="")

    class Meta(TenantAwareModel.Meta):
        db_table = "customer_wallet_transaction"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(is_deleted=False) & ~models.Q(idempotency_key=""),
                name="uq_wallet_tx__idempotency",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer.name}: {self.amount:+} ({self.tx_type})"


class CreditLedger(TenantAwareModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="credit_ledger")
    amount = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Credit charged (+) or settled (-)"
    )
    ledger_type = models.CharField(max_length=20, choices=CreditLedgerType.choices)
    invoice_id = models.UUIDField(null=True, blank=True, help_text="Soft reference to invoice")
    idempotency_key = models.CharField(max_length=120, blank=True, default="")

    class Meta(TenantAwareModel.Meta):
        db_table = "customer_credit_ledger"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(is_deleted=False) & ~models.Q(idempotency_key=""),
                name="uq_credit_ledger__idempotency",
            )
        ]

    def __str__(self) -> str:
        return f"{self.customer.name}: {self.amount:+} ({self.ledger_type})"


class Coupon(TenantAwareModel):
    code = models.CharField(max_length=50)
    discount_type = models.CharField(
        max_length=20, choices=CouponDiscountType.choices, default=CouponDiscountType.PERCENT
    )
    discount_value = models.DecimalField(max_digits=12, decimal_places=2)
    min_purchase = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    valid_from = models.DateTimeField()
    valid_to = models.DateTimeField()
    max_uses = models.PositiveIntegerField(default=1000)
    per_customer_limit = models.PositiveIntegerField(
        default=1, help_text="Max redemptions of this coupon by a single customer"
    )
    current_uses = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta(TenantAwareModel.Meta):
        db_table = "customer_coupon"
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "code"],
                condition=models.Q(is_deleted=False),
                name="uq_coupon__tenant_code",
            )
        ]

    def __str__(self) -> str:
        return f"{self.code} ({self.discount_value})"


class CouponRedemption(TenantAwareModel):
    """One row per successful coupon redemption — enables per-customer caps and
    idempotent, atomic redemption (replaces the non-atomic ``current_uses`` bump)."""
    coupon = models.ForeignKey(Coupon, on_delete=models.CASCADE, related_name="redemptions")
    customer = models.ForeignKey(
        Customer, on_delete=models.CASCADE, related_name="coupon_redemptions"
    )
    order_id = models.UUIDField(null=True, blank=True, help_text="Soft reference to order")
    idempotency_key = models.CharField(max_length=120, blank=True, default="")

    class Meta(TenantAwareModel.Meta):
        db_table = "customer_coupon_redemption"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["coupon", "customer"], name="ix_coupon_redemption__cust"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "idempotency_key"],
                condition=models.Q(is_deleted=False) & ~models.Q(idempotency_key=""),
                name="uq_coupon_redemption__idempotency",
            )
        ]

    def __str__(self) -> str:
        return f"{self.coupon.code} -> {self.customer.name}"
