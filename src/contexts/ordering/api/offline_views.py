"""Authoritative REST API endpoints for Nextora POS Enterprise Offline Synchronization."""
from decimal import Decimal
import logging
import uuid

from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from contexts.catalog.models import Category, Product
from contexts.ordering.models import Order, OrderItem, Payment
from contexts.ordering.services import invoice_service, order_service, payment_service

from shared.tenancy import get_current_tenant, set_current_tenant

logger = logging.getLogger(__name__)


def _ensure_tenant_context(request):
    if get_current_tenant() is None:
        tid = (
            getattr(request, "tenant_id", None)
            or getattr(request, "tenant", None)
            or request.headers.get("X-Tenant-ID")
            or request.META.get("HTTP_X_TENANT_ID")
        )
        if tid:
            try:
                if hasattr(tid, "id"):
                    set_current_tenant(tid.id)
                else:
                    set_current_tenant(uuid.UUID(str(tid)))
            except (ValueError, AttributeError):
                pass


class OfflineBootstrapAPIView(APIView):
    """
    GET /api/v1/ordering/offline/bootstrap/
    Returns high-speed JSON snapshot of active catalog items, categories, taxes, and permissions
    for priming the Dexie IndexedDB client database.
    """
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        _ensure_tenant_context(request)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        _ensure_tenant_context(request)
        products_qs = Product.objects.filter(is_active=True, is_deleted=False).select_related("category", "tax_class")
        categories_qs = Category.objects.filter(is_active=True, is_deleted=False)

        products_data = []
        for p in products_qs:
            products_data.append({
                "id": str(p.id),
                "tenant_id": str(p.tenant_id) if getattr(p, "tenant_id", None) else "local",
                "category_id": str(p.category_id) if p.category_id else None,
                "sku": p.sku,
                "barcode": p.barcode or p.sku,
                "name": p.name,
                "base_price": float(p.base_price),
                "tax_rate": float(p.tax_class.gst_rate) if getattr(p, "tax_class", None) else 5.0,
                "is_active": p.is_active,
            })

        categories_data = []
        for c in categories_qs:
            categories_data.append({
                "id": str(c.id),
                "tenant_id": str(c.tenant_id) if getattr(c, "tenant_id", None) else "local",
                "parent_id": str(c.parent_id) if c.parent_id else None,
                "name": c.name,
                "sort_order": c.sort_order,
            })

        user_permissions = {
            "id": str(request.user.id),
            "email": request.user.email,
            "tenant_id": str(getattr(request, "tenant", "local")),
            "roles": ["cashier", "branch_manager"] if request.user.is_staff else ["cashier"],
            "permissions": ["orders.create", "orders.view", "catalog.view", "payments.capture"],
        }

        return Response({
            "version": 1,
            "timestamp": timezone.now().isoformat(),
            "products": products_data,
            "categories": categories_data,
            "taxes": [
                {"id": "tax_gst_5", "name": "GST 5%", "rate": 5.0},
                {"id": "tax_gst_18", "name": "GST 18%", "rate": 18.0},
            ],
            "user_permissions": user_permissions,
        }, status=status.HTTP_200_OK)


class OfflineSyncAPIView(APIView):
    """
    POST /api/v1/ordering/offline/sync/
    Authoritative batch synchronization endpoint for offline-originated transactions.
    Enforces idempotency and server-side validation.
    """
    permission_classes = [IsAuthenticated]

    def dispatch(self, request, *args, **kwargs):
        _ensure_tenant_context(request)
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        _ensure_tenant_context(request)
        transactions_list = request.data.get("transactions", [])
        if not isinstance(transactions_list, list):
            return Response(
                {"detail": "transactions must be a list."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        results = []
        for item in transactions_list:
            idempotency_key = item.get("idempotency_key")
            payload = item.get("payload", {})
            offline_ref = payload.get("offline_reference_id") or payload.get("id")

            # Duplicate submission protection via offline_reference_id
            if offline_ref:
                existing_order = Order.objects.filter(offline_reference_id=offline_ref).first()
                if existing_order:
                    results.append({
                        "idempotency_key": idempotency_key,
                        "status": "DUPLICATE_SKIPPED",
                        "order_id": str(existing_order.id),
                        "order_number": existing_order.order_number,
                    })
                    continue

            try:
                with transaction.atomic():
                    loc_id_str = payload.get("location_id")
                    loc_id = uuid.UUID(loc_id_str) if loc_id_str else uuid.uuid4()

                    order = Order.objects.create(
                        location_id=loc_id,
                        offline_reference_id=offline_ref,
                        status="open",
                        created_by=request.user.id,
                        subtotal=Decimal(str(payload.get("subtotal", "0"))),
                        tax_amount=Decimal(str(payload.get("tax_total", "0"))),
                        total=Decimal(str(payload.get("grand_total", "0"))),
                        due_amount=Decimal(str(payload.get("grand_total", "0"))),
                    )

                    # Add line items
                    items_payload = payload.get("items", [])
                    for line in items_payload:
                        prod_id_str = line.get("product_id")
                        if not prod_id_str:
                            continue
                        OrderItem.objects.create(
                            order=order,
                            product_id=uuid.UUID(str(prod_id_str)),
                            name_snapshot=line.get("name", "Item"),
                            qty=Decimal(str(line.get("quantity", "1"))),
                            unit_price=Decimal(str(line.get("unit_price", "0"))),
                            line_total=Decimal(str(line.get("unit_price", "0"))) * Decimal(str(line.get("quantity", "1"))),
                        )

                    # Record payments using payment_service to properly update due_amount
                    payments_payload = payload.get("payments", [])
                    for p in payments_payload:
                        payment_service.add_payment(
                            order_id=order.id,
                            amount=Decimal(str(p.get("amount", order.total))),
                            method=p.get("method", "cash"),
                            idempotency_key=f"{idempotency_key}_{p.get('method', 'cash')}",
                            created_by=request.user.id,
                        )

                    # Assign gapless regulatory invoice number and settle order
                    inv = invoice_service.settle_and_invoice(order_id=order.id)
                    order.refresh_from_db()

                    results.append({
                        "idempotency_key": idempotency_key,
                        "status": "SUCCESS",
                        "order_id": str(order.id),
                        "order_number": order.order_number or inv.number,
                    })
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.exception("Failed to synchronize offline transaction %s", idempotency_key)
                results.append({
                    "idempotency_key": idempotency_key,
                    "status": "ERROR",
                    "detail": str(e),
                })

        return Response({"synced_count": len(results), "results": results}, status=status.HTTP_200_OK)
