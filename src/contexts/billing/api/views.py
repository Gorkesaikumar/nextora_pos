from rest_framework import viewsets, status, views
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from contexts.billing.api.serializers import InvoiceSerializer, SubscriptionSerializer, PlanSerializer
from contexts.billing.models.invoice import SubscriptionInvoice
from contexts.billing.models.plan import Plan
from contexts.billing.models.subscription import Subscription
from contexts.identity.api.permissions import RequirePermission
from contexts.billing.services.pricing_engine import PricingEngine
from contexts.billing.services.license_service import LicenseService
from contexts.billing.gateways.factory import get_gateway
from shared.tenancy.context import get_current_tenant
from django.shortcuts import get_object_or_404


class SubscriptionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = SubscriptionSerializer

    def get_queryset(self):
        return Subscription.objects.select_related("plan").all()

    def get_permissions(self):
        return [IsAuthenticated(), RequirePermission("billing.view")()]


class InvoiceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = InvoiceSerializer

    def get_queryset(self):
        return SubscriptionInvoice.objects.select_related("subscription").all()

    def get_permissions(self):
        return [IsAuthenticated(), RequirePermission("billing.view")()]

    @action(detail=True, methods=["get"])
    def download(self, request, pk=None):
        from django.http import HttpResponse
        from django.template.loader import render_to_string
        try:
            import weasyprint
        except ImportError:
            return Response({"detail": "weasyprint not installed"}, status=status.HTTP_501_NOT_IMPLEMENTED)
            
        invoice = self.get_object()
        tenant_id = get_current_tenant()
        
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        with bypass_tenant():
            tenant = Tenant.objects.get(id=tenant_id)
            
        html_string = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: sans-serif; padding: 20px; }}
                    .header {{ border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 20px; }}
                    .footer {{ border-top: 1px solid #ccc; padding-top: 10px; margin-top: 40px; font-size: 12px; color: #666; }}
                    table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f2f2f2; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h2>Nextora POS</h2>
                    <p>Subscription Invoice: {invoice.number}</p>
                </div>
                
                <p><strong>Billed To:</strong> {tenant.name}</p>
                <p><strong>Date:</strong> {invoice.created_at.strftime('%Y-%m-%d')}</p>
                <p><strong>Status:</strong> {invoice.status.upper()}</p>
                
                <table>
                    <thead>
                        <tr>
                            <th>Plan</th>
                            <th>Period</th>
                            <th>Amount ({invoice.currency})</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>{invoice.subscription.plan.name}</td>
                            <td>{invoice.period_start.strftime('%Y-%m-%d')} to {invoice.period_end.strftime('%Y-%m-%d')}</td>
                            <td>{invoice.amount}</td>
                        </tr>
                    </tbody>
                </table>
                
                <h3 style="text-align: right;">Total Paid: {invoice.currency} {invoice.total}</h3>
                
                <div class="footer">
                    <p>Thank you for your business! For support, contact billing@nextora.com.</p>
                </div>
            </body>
        </html>
        """
        
        pdf_file = weasyprint.HTML(string=html_string).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="invoice_{invoice.number}.pdf"'
        return response


class PlanViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = PlanSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Plan.objects.filter(is_active=True, is_public=True).order_by("display_order")


class RazorpayOrderView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tenant_id = get_current_tenant()
        plan_code = request.data.get("plan_code")
        coupon_code = request.data.get("coupon_code", "").strip()

        if not tenant_id:
            return Response({"detail": "Tenant context required."}, status=status.HTTP_400_BAD_REQUEST)

        plan = get_object_or_404(Plan, code=plan_code, is_active=True)
        
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        with bypass_tenant():
            tenant = get_object_or_404(Tenant, id=tenant_id)

        pricing = PricingEngine.calculate_effective_price(
            tenant=tenant, plan=plan, coupon_code=coupon_code
        )

        if coupon_code and not pricing["coupon_valid"]:
            return Response({"detail": pricing["coupon_error"]}, status=status.HTTP_400_BAD_REQUEST)

        gateway = get_gateway()
        from django.conf import settings
        
        # Razorpay requires amount in minor units (paise)
        try:
            order_data = gateway.create_order(
                amount_minor=int(pricing["total_amount"] * 100), 
                currency=pricing["currency"],
                receipt=f"sub_{tenant_id.hex[:8]}_{plan.code}"
            )
        except Exception as e:
            return Response({"detail": f"Payment gateway error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({
            "order_id": order_data.id,
            "amount": float(pricing["total_amount"]),
            "currency": pricing["currency"],
            "plan_id": str(plan.id),
            "razorpay_key": settings.RAZORPAY_KEY_ID,
        }, status=status.HTTP_200_OK)


class RazorpayVerifyView(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        tenant_id = get_current_tenant()
        razorpay_payment_id = request.data.get("razorpay_payment_id")
        razorpay_order_id = request.data.get("razorpay_order_id")
        razorpay_signature = request.data.get("razorpay_signature")
        plan_code = request.data.get("plan_code")

        if not all([tenant_id, razorpay_payment_id, razorpay_order_id, razorpay_signature, plan_code]):
            return Response({"detail": "Missing required fields."}, status=status.HTTP_400_BAD_REQUEST)

        gateway = get_gateway()
        
        # Verify signature
        if not gateway.verify_payment_signature(razorpay_order_id, razorpay_payment_id, razorpay_signature):
            return Response({"detail": "Invalid payment signature."}, status=status.HTTP_400_BAD_REQUEST)

        # Upgrade Subscription
        plan = get_object_or_404(Plan, code=plan_code, is_active=True)
        
        from contexts.tenants.models import Tenant
        from shared.tenancy.context import bypass_tenant
        from contexts.billing.services.invoice_service import generate_invoice, mark_paid
        from django.db import transaction

        with bypass_tenant():
            tenant = get_object_or_404(Tenant, id=tenant_id)

        try:
            with transaction.atomic():
                sub = LicenseService.renew_or_upgrade(
                    tenant=tenant, new_plan=plan, interval=plan.duration_type
                )
                
                invoice = generate_invoice(
                    tenant_id=tenant.id,
                    subscription=sub,
                    period_start=sub.current_period_start,
                    period_end=sub.current_period_end,
                )
                
                mark_paid(
                    tenant_id=tenant.id,
                    invoice=invoice,
                    provider="razorpay",
                    provider_payment_id=razorpay_payment_id,
                )
        except Exception as e:
            return Response({"detail": f"Failed to activate subscription: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"detail": "Payment verified and subscription activated successfully."}, status=status.HTTP_200_OK)
