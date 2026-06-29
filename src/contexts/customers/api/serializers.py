from decimal import Decimal
from rest_framework import serializers

from ..models import Coupon, Customer


class CustomerSerializer(serializers.ModelSerializer):

    class Meta:
        model = Customer
        fields = [
            "id",
            "name",
            "phone",
            "email",
            "gstin",
            "legal_name",
            "loyalty_tier",
            "loyalty_points",
            "wallet_balance",
            "credit_limit",
            "outstanding_credit",
        ]
        read_only_fields = [
            "id",
            "loyalty_tier",
            "loyalty_points",
            "wallet_balance",
            "outstanding_credit",
        ]


class CouponSerializer(serializers.ModelSerializer):

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
            "current_uses",
            "is_active",
        ]
        read_only_fields = ["id", "current_uses"]


class WalletDepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.01")
    )


class CouponValidateSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=50)
    subtotal = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0.00")
    )
