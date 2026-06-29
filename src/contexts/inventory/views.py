"""Inventory web views — server-rendered operational surfaces.

Four feature areas, each backed by the existing service layer:
  * Suppliers          — vendor master CRUD.
  * Inventory items    — stock records, levels, low-stock visibility.
  * Purchase orders    — raise POs and receive stock against them.
  * Stock adjustments  — manual corrections with supervised approval.

Views stay thin: they validate input and delegate every state change to a
service (numbering, ledger postings, weighted-average cost and audit all live
there). Reads are tenant-scoped automatically by the model managers.
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin
from contexts.inventory.domain.enums import PurchaseOrderStatus
from contexts.inventory.exceptions import (
    DuplicateCode,
    InventoryError,
    SupplierNotFound,
    ValidationError as InventoryValidationError,
)
from contexts.inventory.forms import (
    InventoryItemForm,
    PurchaseOrderForm,
    ReorderLevelsForm,
    StockAdjustmentForm,
    SupplierForm,
    parse_line_items,
)
from contexts.inventory.models import (
    InventoryItem,
    PurchaseOrder,
    StockAdjustment,
    Supplier,
    Warehouse,
)
from contexts.inventory.models.adjustment import AdjustmentReason
from contexts.inventory.domain.enums import StockMovementType
from contexts.inventory.services import (
    adjustment_service,
    item_service,
    purchase_service,
    supplier_service,
    warehouse_service,
)
from contexts.inventory.services.movement_service import apply_stock_movement

logger = logging.getLogger(__name__)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
class InventoryAccessMixin(TenantPermissionRequiredMixin, LoginRequiredMixin):
    """Login + tenant-scoped permission gate for all inventory web views."""


def _actor_id(request):
    user = getattr(request, "user", None)
    return getattr(user, "id", None) if user and user.is_authenticated else None


def _ensure_default_warehouse() -> Warehouse:
    """Return the tenant's default warehouse, provisioning one on first use.

    Inventory items, POs and adjustments all require a warehouse. Tenants get a
    sensible "Main Store" default automatically so the module is usable without
    a separate warehouse-setup step.
    """
    existing = Warehouse.objects.filter(is_active=True).order_by("-is_default", "name").first()
    if existing is not None:
        return existing
    return warehouse_service.create_warehouse(
        name="Main Store", code="WH-01", is_default=True,
    )


def _to_decimal(value, field: str) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise InventoryValidationError({field: f"'{value}' is not a valid number."})


# --------------------------------------------------------------------------- #
# Suppliers
# --------------------------------------------------------------------------- #
class SupplierListView(InventoryAccessMixin, ListView):
    permission_required = "inventory.view"
    model = Supplier
    template_name = "inventory/supplier_list.html"
    context_object_name = "suppliers"
    paginate_by = 25

    def get_queryset(self):
        qs = Supplier.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(
                Q(name__icontains=q) | Q(code__icontains=q)
                | Q(contact_person__icontains=q) | Q(phone__icontains=q)
            )
        return qs.order_by("name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        return ctx


class SupplierCreateView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def get(self, request):
        return render(request, "inventory/supplier_form.html", {
            "form": SupplierForm(), "action": "Create",
        })

    def post(self, request):
        form = SupplierForm(request.POST)
        if not form.is_valid():
            return render(request, "inventory/supplier_form.html", {"form": form, "action": "Create"})
        try:
            supplier = supplier_service.create_supplier(**form.cleaned_data)
        except DuplicateCode as exc:
            for field, msg in exc.errors.items():
                form.add_error(field if field in form.fields else None, msg)
            return render(request, "inventory/supplier_form.html", {"form": form, "action": "Create"})
        messages.success(request, f'Supplier "{supplier.name}" created.')
        return redirect("inventory:supplier_list")


class SupplierUpdateView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def get(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        return render(request, "inventory/supplier_form.html", {
            "form": SupplierForm(instance=supplier), "action": "Edit", "supplier": supplier,
        })

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        form = SupplierForm(request.POST, instance=supplier)
        if not form.is_valid():
            return render(request, "inventory/supplier_form.html", {"form": form, "action": "Edit", "supplier": supplier})
        try:
            supplier_service.update_supplier(supplier.id, form.cleaned_data)
        except DuplicateCode as exc:
            for field, msg in exc.errors.items():
                form.add_error(field if field in form.fields else None, msg)
            return render(request, "inventory/supplier_form.html", {"form": form, "action": "Edit", "supplier": supplier})
        except SupplierNotFound:
            raise Http404
        messages.success(request, f'Supplier "{supplier.name}" updated.')
        return redirect("inventory:supplier_list")


class SupplierDeleteView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        name = supplier.name
        supplier.delete()  # soft delete
        messages.success(request, f'Supplier "{name}" removed.')
        return redirect("inventory:supplier_list")


# --------------------------------------------------------------------------- #
# Inventory items
# --------------------------------------------------------------------------- #
class InventoryItemListView(InventoryAccessMixin, ListView):
    permission_required = "inventory.view"
    model = InventoryItem
    template_name = "inventory/item_list.html"
    context_object_name = "items"
    paginate_by = 25

    def get_queryset(self):
        qs = InventoryItem.objects.select_related("warehouse")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(product_name__icontains=q) | Q(product_sku__icontains=q))
        if self.request.GET.get("low") == "1":
            qs = qs.filter(quantity_on_hand__lte=F("minimum_stock"), minimum_stock__gt=0)
        return qs.order_by("product_name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["low_only"] = self.request.GET.get("low") == "1"
        return ctx


class InventoryItemCreateView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def get(self, request):
        return render(request, "inventory/item_form.html", {
            "form": InventoryItemForm(), "action": "Add",
        })

    def post(self, request):
        form = InventoryItemForm(request.POST)
        if not form.is_valid():
            return render(request, "inventory/item_form.html", {"form": form, "action": "Add"})

        data = form.cleaned_data
        product = data["product"]
        warehouse = data["warehouse"] or _ensure_default_warehouse()
        try:
            item = item_service.ensure_item(
                product_id=product.id,
                warehouse_id=warehouse.id,
                product_sku=product.sku,
                product_name=product.name,
                minimum_stock=data["minimum_stock"],
                reorder_point=data["reorder_point"],
                reorder_quantity=data["reorder_quantity"],
            )
            opening = data["opening_quantity"] or Decimal("0")
            if opening > 0:
                apply_stock_movement(
                    inventory_item_id=item.id,
                    movement_type=StockMovementType.OPENING,
                    quantity=opening,
                    unit_cost=data.get("average_cost") or Decimal("0"),
                    reference_type="opening_balance",
                    reference_number="OPENING",
                    performed_by_id=_actor_id(request),
                )
            # Link the catalog product to its stock record.
            if product.inventory_item_id != item.id:
                product.inventory_item_id = item.id
                product.save(update_fields=["inventory_item_id", "updated_at"])
        except InventoryError as exc:
            messages.error(request, str(exc))
            return render(request, "inventory/item_form.html", {"form": form, "action": "Add"})

        messages.success(request, f'Stock record for "{product.name}" created.')
        return redirect("inventory:item_list")


class InventoryItemUpdateView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def get(self, request, pk):
        item = get_object_or_404(InventoryItem.objects.select_related("warehouse"), pk=pk)
        return render(request, "inventory/item_reorder_form.html", {
            "form": ReorderLevelsForm(instance=item), "item": item,
        })

    def post(self, request, pk):
        item = get_object_or_404(InventoryItem.objects.select_related("warehouse"), pk=pk)
        form = ReorderLevelsForm(request.POST, instance=item)
        if not form.is_valid():
            return render(request, "inventory/item_reorder_form.html", {"form": form, "item": item})
        item_service.set_reorder_levels(
            item.id,
            minimum_stock=form.cleaned_data["minimum_stock"],
            reorder_point=form.cleaned_data["reorder_point"],
            reorder_quantity=form.cleaned_data["reorder_quantity"],
        )
        if form.cleaned_data["is_active"] != item.is_active:
            item.is_active = form.cleaned_data["is_active"]
            item.save(update_fields=["is_active", "updated_at"])
        messages.success(request, f'Updated levels for "{item.product_name}".')
        return redirect("inventory:item_list")


# --------------------------------------------------------------------------- #
# Purchase orders
# --------------------------------------------------------------------------- #
class PurchaseOrderListView(InventoryAccessMixin, ListView):
    permission_required = "inventory.view"
    model = PurchaseOrder
    template_name = "inventory/purchase_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        qs = PurchaseOrder.objects.select_related("supplier", "warehouse")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(order_number__icontains=q) | Q(supplier__name__icontains=q))
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = PurchaseOrderStatus.choices
        return ctx


class PurchaseOrderCreateView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def _line_items(self):
        return InventoryItem.objects.filter(is_active=True).order_by("product_name")

    def get(self, request):
        return render(request, "inventory/purchase_form.html", {
            "form": PurchaseOrderForm(), "line_items": self._line_items(),
        })

    def post(self, request):
        form = PurchaseOrderForm(request.POST)
        rows = parse_line_items(request.POST)
        ctx = {"form": form, "line_items": self._line_items()}

        if not form.is_valid():
            return render(request, "inventory/purchase_form.html", ctx)
        if not rows:
            messages.error(request, "Add at least one line item to the purchase order.")
            return render(request, "inventory/purchase_form.html", ctx)

        try:
            lines = [{
                "inventory_item_id": r["inventory_item_id"],
                "quantity_ordered": _to_decimal(r["quantity"], "quantity"),
                "unit_cost": _to_decimal(r.get("unit_cost", "0") or "0", "unit_cost"),
                "tax_rate": _to_decimal(r.get("tax_rate", "0") or "0", "tax_rate"),
            } for r in rows]
            po = purchase_service.create_purchase_order(
                tenant_id=request.tenant_id,
                supplier_id=form.cleaned_data["supplier"].id,
                warehouse_id=form.cleaned_data["warehouse"].id,
                lines=lines,
                expected_delivery_date=form.cleaned_data["expected_delivery_date"],
                notes=form.cleaned_data["notes"],
            )
        except InventoryError as exc:
            messages.error(request, str(exc))
            return render(request, "inventory/purchase_form.html", ctx)

        messages.success(request, f"Purchase order {po.order_number} created.")
        return redirect("inventory:purchase_detail", pk=po.id)


class PurchaseOrderDetailView(InventoryAccessMixin, View):
    permission_required = "inventory.view"

    def get(self, request, pk):
        po = get_object_or_404(
            PurchaseOrder.objects.select_related("supplier", "warehouse"), pk=pk
        )
        lines = po.lines.select_related("inventory_item").all()
        receivable = po.status not in (PurchaseOrderStatus.RECEIVED, PurchaseOrderStatus.CANCELLED)
        return render(request, "inventory/purchase_detail.html", {
            "po": po, "lines": lines, "receivable": receivable,
        })


class PurchaseOrderReceiveView(InventoryAccessMixin, View):
    permission_required = "inventory.manage"

    def post(self, request, pk):
        po = get_object_or_404(PurchaseOrder, pk=pk)
        line_ids = request.POST.getlist("line_id")
        qtys = request.POST.getlist("receive_quantity")
        batches = request.POST.getlist("batch_number")

        receipts = []
        try:
            for idx, line_id in enumerate(line_ids):
                qty_raw = (qtys[idx] if idx < len(qtys) else "").strip()
                if not qty_raw:
                    continue
                qty = _to_decimal(qty_raw, "receive_quantity")
                if qty <= 0:
                    continue
                receipt = {"line_id": line_id, "quantity_received": qty}
                batch_no = (batches[idx] if idx < len(batches) else "").strip()
                if batch_no:
                    receipt["batch_number"] = batch_no
                receipts.append(receipt)

            if not receipts:
                messages.error(request, "Enter a received quantity on at least one line.")
                return redirect("inventory:purchase_detail", pk=po.id)

            purchase_service.receive_purchase_order(
                purchase_order_id=po.id,
                receipts=receipts,
                received_by_id=_actor_id(request),
            )
        except InventoryError as exc:
            messages.error(request, str(exc))
            return redirect("inventory:purchase_detail", pk=po.id)

        messages.success(request, f"Stock received against {po.order_number}.")
        return redirect("inventory:purchase_detail", pk=po.id)


# --------------------------------------------------------------------------- #
# Stock adjustments
# --------------------------------------------------------------------------- #
class StockAdjustmentListView(InventoryAccessMixin, ListView):
    permission_required = "inventory.view"
    model = StockAdjustment
    template_name = "inventory/adjustment_list.html"
    context_object_name = "adjustments"
    paginate_by = 25

    def get_queryset(self):
        qs = StockAdjustment.objects.select_related("warehouse")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(adjustment_number__icontains=q)
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["reasons"] = dict(AdjustmentReason.choices)
        return ctx


class StockAdjustmentCreateView(InventoryAccessMixin, View):
    permission_required = "inventory.adjust"

    def _line_items(self):
        return InventoryItem.objects.filter(is_active=True).order_by("product_name")

    def get(self, request):
        return render(request, "inventory/adjustment_form.html", {
            "form": StockAdjustmentForm(), "line_items": self._line_items(),
        })

    def post(self, request):
        form = StockAdjustmentForm(request.POST)
        rows = parse_line_items(request.POST)
        ctx = {"form": form, "line_items": self._line_items()}

        if not form.is_valid():
            return render(request, "inventory/adjustment_form.html", ctx)
        if not rows:
            messages.error(request, "Add at least one item to adjust.")
            return render(request, "inventory/adjustment_form.html", ctx)

        try:
            lines = [{
                "inventory_item_id": r["inventory_item_id"],
                "quantity_after": _to_decimal(r["quantity"], "quantity_after"),
            } for r in rows]
            adjustment = adjustment_service.create_adjustment(
                tenant_id=request.tenant_id,
                warehouse_id=form.cleaned_data["warehouse"].id,
                reason=form.cleaned_data["reason"],
                lines=lines,
                notes=form.cleaned_data["notes"],
                adjusted_by_id=_actor_id(request),
            )
        except InventoryError as exc:
            messages.error(request, str(exc))
            return render(request, "inventory/adjustment_form.html", ctx)

        # Auto-apply when the actor can also approve; otherwise leave pending.
        if request.POST.get("apply_now") == "1":
            try:
                adjustment_service.approve_and_apply_adjustment(
                    adjustment.id, approved_by_id=_actor_id(request)
                )
                messages.success(request, f"Adjustment {adjustment.adjustment_number} applied.")
            except InventoryError as exc:
                messages.warning(
                    request,
                    f"Adjustment {adjustment.adjustment_number} saved but not applied: {exc}",
                )
        else:
            messages.success(
                request,
                f"Adjustment {adjustment.adjustment_number} created — pending approval.",
            )
        return redirect("inventory:adjustment_list")


class StockAdjustmentApproveView(InventoryAccessMixin, View):
    permission_required = "inventory.adjust"

    def post(self, request, pk):
        adjustment = get_object_or_404(StockAdjustment, pk=pk)
        try:
            adjustment_service.approve_and_apply_adjustment(
                adjustment.id, approved_by_id=_actor_id(request)
            )
        except InventoryError as exc:
            messages.error(request, str(exc))
            return redirect("inventory:adjustment_list")
        messages.success(request, f"Adjustment {adjustment.adjustment_number} approved and applied.")
        return redirect("inventory:adjustment_list")
