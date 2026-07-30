"""Customers API Views.

Reuses all existing services from contexts.customers.services — no business logic here.
All viewsets use BaseModelViewSet for pagination, filtering, search, and standard responses.
Return plain data from actions — StandardJSONRenderer wraps everything automatically.
"""
from typing import Any

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from shared.api.permissions import BasePermission
from shared.api.views import BaseModelViewSet
from contexts.identity.api.permissions import RequirePermission
from shared.tenancy.context import get_current_tenant

from ..exceptions import CustomerError
from ..models import (
    Coupon,
    CouponRedemption,
    CreditLedger,
    Customer,
    LoyaltyProgram,
    PointsLedger,
    WalletTransaction,
    WalletTxType,
)
from ..services import (
    adjust_wallet_balance,
    create_customer,
    earn_points,
    redeem_coupon,
    redeem_points,
    validate_coupon,
)
from .serializers import (
    CouponRedemptionSerializer,
    CouponSerializer,
    CouponValidateSerializer,
    CreditLedgerSerializer,
    CustomerSerializer,
    EarnPointsSerializer,
    LoyaltyProgramSerializer,
    PointsLedgerSerializer,
    RedeemPointsSerializer,
    WalletDepositSerializer,
    WalletTransactionSerializer,
)


class CustomerViewSet(BaseModelViewSet):
    """Customer CRUD + Wallet, Loyalty, Points, Credit Ledger, History actions."""

    serializer_class = CustomerSerializer
    filterset_fields = ["loyalty_tier", "accepts_marketing"]
    search_fields = ["name", "phone", "email", "gstin", "legal_name"]
    ordering_fields = ["name", "loyalty_points", "wallet_balance", "created_at"]

    def get_queryset(self) -> Any:
        return Customer.objects.all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve"}
        code = "customers.view" if read_only else "customers.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]

    def create(self, request, *args, **kwargs):
        """Delegate creation to service so domain events are published."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        customer = create_customer(**serializer.validated_data)
        return Response(
            self.get_serializer(customer).data,
            status=status.HTTP_201_CREATED,
        )

    # --- Wallet --------------------------------------------------------------

    @action(detail=True, methods=["post"], url_path="wallet/deposit")
    def wallet_deposit(self, request, pk=None):
        """Deposit funds into customer wallet."""
        s = WalletDepositSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            customer = adjust_wallet_balance(
                pk, s.validated_data["amount"], WalletTxType.DEPOSIT
            )
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="wallet/pay")
    def wallet_pay(self, request, pk=None):
        """Deduct a payment from customer wallet."""
        s = WalletDepositSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            customer = adjust_wallet_balance(
                pk, -s.validated_data["amount"], WalletTxType.PAYMENT
            )
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="wallet/history")
    def wallet_history(self, request, pk=None):
        """Paginated wallet transaction history for a customer."""
        qs = WalletTransaction.objects.filter(customer_id=pk).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                WalletTransactionSerializer(page, many=True).data
            )
        return Response(WalletTransactionSerializer(qs, many=True).data)

    # --- Loyalty / Points ----------------------------------------------------

    @action(detail=True, methods=["post"], url_path="points/earn")
    def points_earn(self, request, pk=None):
        """Earn loyalty points for a customer."""
        s = EarnPointsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            customer = earn_points(pk, **s.validated_data)
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="points/redeem")
    def points_redeem(self, request, pk=None):
        """Redeem loyalty points for a customer."""
        s = RedeemPointsSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        try:
            customer = redeem_points(pk, **s.validated_data)
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CustomerSerializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="points/history")
    def points_history(self, request, pk=None):
        """Paginated loyalty points ledger for a customer."""
        qs = PointsLedger.objects.filter(customer_id=pk).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                PointsLedgerSerializer(page, many=True).data
            )
        return Response(PointsLedgerSerializer(qs, many=True).data)

    # --- Credit Ledger -------------------------------------------------------

    @action(detail=True, methods=["get"], url_path="credit/ledger")
    def credit_ledger(self, request, pk=None):
        """Paginated credit ledger for a customer."""
        qs = CreditLedger.objects.filter(customer_id=pk).order_by("-created_at")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                CreditLedgerSerializer(page, many=True).data
            )
        return Response(CreditLedgerSerializer(qs, many=True).data)

    # --- Order history (cross-context soft join) ------------------------------

    @action(detail=True, methods=["get"], url_path="orders")
    def order_history(self, request, pk=None):
        """Customer order history — soft-joined via customer_phone."""
        from contexts.ordering.models import Order
        customer = self.get_object()
        qs = list(
            Order.objects.filter(customer_phone=customer.phone)
            .order_by("-created_at")
            .values("id", "order_number", "status", "total", "type", "created_at")
        )
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(page)
        return Response(qs)

    # --- Coupon redemptions --------------------------------------------------

    @action(detail=True, methods=["get"], url_path="coupons")
    def coupon_history(self, request, pk=None):
        """Coupon redemption history for a customer."""
        qs = CouponRedemption.objects.filter(customer_id=pk).select_related("coupon")
        page = self.paginate_queryset(qs)
        if page is not None:
            return self.get_paginated_response(
                CouponRedemptionSerializer(page, many=True).data
            )
        return Response(CouponRedemptionSerializer(qs, many=True).data)


class LoyaltyProgramViewSet(BaseModelViewSet):
    """Tenant loyalty program config — single-row resource."""

    serializer_class = LoyaltyProgramSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self) -> Any:
        return LoyaltyProgram.objects.all()

    def get_permissions(self) -> list:
        code = "customers.view" if self.action in {"list", "retrieve"} else "customers.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]


class CouponViewSet(BaseModelViewSet):
    """Coupon CRUD + validation."""

    serializer_class = CouponSerializer
    filterset_fields = ["discount_type", "is_active"]
    search_fields = ["code"]
    ordering_fields = ["valid_from", "valid_to", "discount_value"]

    def get_queryset(self) -> Any:
        return Coupon.objects.all()

    def get_permissions(self) -> list:
        read_only = self.action in {"list", "retrieve", "validate"}
        code = "customers.view" if read_only else "customers.manage"
        return [IsAuthenticated(), BasePermission(), RequirePermission(code)()]

    @action(detail=False, methods=["post"], url_path="validate")
    def validate(self, request):
        """Read-only coupon validation — date window, global cap, min spend."""
        s = CouponValidateSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        tenant_id = get_current_tenant()
        if not tenant_id:
            return Response(
                {"detail": "Tenant not resolved in current session."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            coupon = validate_coupon(
                s.validated_data["code"], tenant_id, s.validated_data["subtotal"]
            )
            return Response(CouponSerializer(coupon).data, status=status.HTTP_200_OK)
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
