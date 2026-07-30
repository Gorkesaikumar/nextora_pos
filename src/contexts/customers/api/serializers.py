"""DRF serializers for the Customers API."""
from decimal import Decimal

from rest_framework import serializers

from shared.api.serializers import BaseModelSerializer
from ..models import (
    Coupon,
    CouponRedemption,
    CreditLedger,
    Customer,
    LoyaltyProgram,
    PointsLedger,
    WalletTransaction,
)


class CustomerSerializer(BaseModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "email",
            # GST / B2B
            "gstin",
            "legal_name",
            "state_code",
            "accepts_marketing",
            # Loyalty
            "loyalty_tier",
            "loyalty_points",
            "lifetime_points",
            # Value accounts
            "wallet_balance",
            "credit_limit",
            "outstanding_credit",
        ]
        read_only_fields = [
            "id",
            "loyalty_tier",
            "loyalty_points",
            "lifetime_points",
            "wallet_balance",
            "outstanding_credit",
        ]


class LoyaltyProgramSerializer(BaseModelSerializer):
    class Meta:
        model = LoyaltyProgram
        fields = [
            "id",
            "earn_rate",
            "redeem_value",
            "silver_threshold",
            "gold_threshold",
            "platinum_threshold",
            "points_expiry_days",
        ]


class PointsLedgerSerializer(BaseModelSerializer):
    class Meta:
        model = PointsLedger
        fields = ["id", "customer", "points", "reason", "order_id", "created_at"]
        read_only_fields = fields


class WalletTransactionSerializer(BaseModelSerializer):
    class Meta:
        model = WalletTransaction
        fields = ["id", "customer", "amount", "tx_type", "order_id", "created_at"]
        read_only_fields = fields


class CreditLedgerSerializer(BaseModelSerializer):
    class Meta:
        model = CreditLedger
        fields = ["id", "customer", "amount", "ledger_type", "invoice_id", "created_at"]
        read_only_fields = fields


class CouponSerializer(BaseModelSerializer):
    class Meta:
        model = Coupon
        fields = [
            "id",
            "code",
            "discount_type",
            "discount_value",
            "min_purchase",
            "valid_from",
            "valid_to",
            "max_uses",
            "per_customer_limit",
            "current_uses",
            "is_active",
        ]
        read_only_fields = ["id", "current_uses"]


class CouponRedemptionSerializer(BaseModelSerializer):
    coupon_code = serializers.CharField(source="coupon.code", read_only=True)

    class Meta:
        model = CouponRedemption
        fields = ["id", "coupon", "coupon_code", "customer", "order_id", "created_at"]
        read_only_fields = fields


# --- Input serializers -------------------------------------------------------

class WalletDepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )


class EarnPointsSerializer(serializers.Serializer):
    points = serializers.IntegerField(required=False, min_value=1)
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01"), required=False
    )
    reason = serializers.CharField(max_length=255, default="purchase")
    order_id = serializers.UUIDField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(max_length=120, default="")

    def validate(self, data):
        if not data.get("points") and not data.get("amount"):
            raise serializers.ValidationError("Provide either 'points' or 'amount'.")
        return data


class RedeemPointsSerializer(serializers.Serializer):
    points = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=255, default="redemption")
    order_id = serializers.UUIDField(required=False, allow_null=True)
    idempotency_key = serializers.CharField(max_length=120, default="")


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.00")
    )
