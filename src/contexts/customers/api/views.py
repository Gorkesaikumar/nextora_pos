from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from shared.tenancy.context import get_current_tenant
from ..exceptions import CustomerError
from ..models import Coupon, Customer, WalletTxType
from ..services import adjust_wallet_balance, validate_coupon
from .serializers import (
    CouponSerializer,
    CouponValidateSerializer,
    CustomerSerializer,
    WalletDepositSerializer,
)


class CustomerViewSet(viewsets.ModelViewSet):
    serializer_class = CustomerSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Customer.objects.all()

    @action(detail=True, methods=["post"], url_path="wallet/deposit")
    def deposit(self, request, pk=None):
        serializer = WalletDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]
        customer = adjust_wallet_balance(pk, amount, WalletTxType.DEPOSIT)

        return Response(self.get_serializer(customer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["post"], url_path="wallet/pay")
    def pay(self, request, pk=None):
        serializer = WalletDepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]
        try:
            customer = adjust_wallet_balance(pk, -amount, WalletTxType.PAYMENT)
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(self.get_serializer(customer).data, status=status.HTTP_200_OK)


class CouponViewSet(viewsets.ModelViewSet):
    serializer_class = CouponSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Coupon.objects.all()

    @action(detail=False, methods=["post"], url_path="validate")
    def validate(self, request):
        serializer = CouponValidateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        code = serializer.validated_data["code"]
        subtotal = serializer.validated_data["subtotal"]
        tenant_id = get_current_tenant()

        if not tenant_id:
            return Response(
                {"detail": "Tenant not resolved in current session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            coupon = validate_coupon(code, tenant_id, subtotal)
            return Response(self.get_serializer(coupon).data, status=status.HTTP_200_OK)
        except CustomerError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)
