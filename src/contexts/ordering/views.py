import uuid
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView, ListView
from django.views import View
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache

from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin
from contexts.catalog.models.category import Category
from contexts.catalog.models.product import Product
from contexts.ordering.models.order import Order, OrderItem
from contexts.ordering.services import order_service
from contexts.restaurant.models.branch import Branch
from contexts.ordering.domain.enums import OrderType, OrderStatus, ItemStatus


class POSMainView(LoginRequiredMixin, TemplateView):
    template_name = "ordering/pos.html"

    def get_context_data(self, **kwargs):
        from contexts.catalog.forms import CategoryForm
        from contexts.ordering.models.kot import KOT
        from contexts.ordering.domain.enums import KOTStatus

        context = super().get_context_data(**kwargs)
        # Fetch top-level categories for the filter ribbon
        categories = Category.objects.filter(
            is_active=True, is_deleted=False, parent__isnull=True
        ).order_by('sort_order', 'name')
        context["categories"] = categories

        # Initial load of active products. Ordered category-first so the grid
        # template can `regroup` them under category section headers.
        products = Product.objects.filter(
            is_active=True, is_deleted=False
        ).select_related('category').order_by(
            'category__sort_order', 'category__name', 'sort_order', 'name'
        )
        context["products"] = products

        # Empty form powering the inline "Add Category" modal (reuses catalog).
        context["category_form"] = CategoryForm()

        # Bottom status-bar metrics.
        context["stat_total_items"] = products.count()
        context["stat_categories"] = categories.count()
        context["stat_active_orders"] = Order.objects.filter(
            status=OrderStatus.OPEN
        ).count()
        context["stat_open_kots"] = KOT.objects.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING]
        ).count()

        # Load active session cart if it exists
        order_id = self.request.session.get('active_order_id')
        if order_id:
            try:
                context["active_order"] = Order.objects.get(id=order_id, status=OrderStatus.OPEN)
            except Order.DoesNotExist:
                del self.request.session['active_order_id']
                context["active_order"] = None
        else:
            context["active_order"] = None

        return context


class POSCategoryRibbonView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    """Re-renders just the category filter ribbon.

    Triggered after a category is created via the inline modal so the new
    category appears without a full page reload.
    """
    permission_required = "orders.view"
    template_name = "ordering/partials/category_ribbon.html"
    context_object_name = "categories"

    def get_queryset(self):
        return Category.objects.filter(
            is_active=True, is_deleted=False, parent__isnull=True
        ).order_by('sort_order', 'name')


class POSProductGridView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "orders.view"
    template_name = "ordering/partials/product_grid.html"
    context_object_name = "products"

    def get_queryset(self):
        qs = Product.objects.filter(is_active=True, is_deleted=False).select_related('category').order_by(
            'category__sort_order', 'category__name', 'sort_order', 'name'
        )

        # Filter by search term
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
            
        # Filter by category id
        category_id = self.request.GET.get('category_id')
        if category_id:
            qs = qs.filter(category_id=category_id)
            
        return qs


def _get_or_create_active_order(request):
    """Helper to fetch the session order or spawn a new walk-in order."""
    order_id = request.session.get('active_order_id')
    if order_id:
        try:
            order = Order.objects.get(id=order_id, status=OrderStatus.OPEN)
            return order
        except Order.DoesNotExist:
            del request.session['active_order_id']
            
    # Create new order on the fly. We'll pick the first available branch for this demo.
    branch = Branch.objects.first()
    if not branch:
        # Fallback if no branches exist
        branch_id = uuid.uuid4()
    else:
        branch_id = branch.id

    order = order_service.create_order(
        location_id=branch_id,
        order_type=OrderType.TAKEAWAY, # Default walk-in
        created_by=request.user.id
    )
    request.session['active_order_id'] = str(order.id)
    return order


class POSAddToCartView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.create"
    
    def post(self, request, product_id, *args, **kwargs):
        product = get_object_or_404(Product, id=product_id, is_active=True)
        order = _get_or_create_active_order(request)
        
        # Check if item already exists to increment qty instead of duplicating line
        # Simplification for demo: just add it
        existing_item = order.items.filter(product_id=product_id, status=ItemStatus.ACTIVE).first()
        if existing_item:
            order_service.set_item_qty(order.id, existing_item.id, existing_item.qty + 1)
        else:
            order_service.add_item(order.id, product, qty=1)
            
        order.refresh_from_db()
        return render(request, "ordering/partials/cart_panel.html", {"active_order": order})


class POSUpdateItemView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.update"
    
    def post(self, request, item_id, action, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if not order_id:
            return HttpResponse("")

        order = get_object_or_404(Order, id=order_id)
        item = get_object_or_404(OrderItem, id=item_id, order=order)

        if action == 'add':
            order_service.set_item_qty(order.id, item.id, item.qty + 1)
        elif action == 'sub':
            order_service.set_item_qty(order.id, item.id, item.qty - 1)
        order.refresh_from_db()
        return render(request, "ordering/partials/cart_panel.html", {"active_order": order})


class POSRemoveItemView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.update"
    
    def post(self, request, item_id, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if not order_id:
            return HttpResponse("")

        order = get_object_or_404(Order, id=order_id)
        order_service.void_item(order.id, item_id)
        
        order.refresh_from_db()
        return render(request, "ordering/partials/cart_panel.html", {"active_order": order})


class POSClearCartView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.update"
    
    def post(self, request, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if order_id:
            try:
                order_service.void_order(order_id, reason="Cleared by POS operator")
            except Exception:
                pass
            del request.session['active_order_id']
            
        return render(request, "ordering/partials/cart_panel.html", {"active_order": None})


from contexts.ordering.services import payment_service, invoice_service, kot_service
from decimal import Decimal

class POSSaveOrderView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.update"
    
    def post(self, request, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if not order_id:
            return HttpResponse("")

        order = get_object_or_404(Order, id=order_id)
        if order.items.exists():
            kot_service.generate_kots(order.id)
            
        del request.session['active_order_id']
        return render(request, "ordering/partials/save_order_success_modal.html")


class POSCheckoutModalView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "payments.capture"
    
    def get(self, request, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if not order_id:
            return HttpResponse("")

        order = get_object_or_404(Order, id=order_id)
        if not order.items.exists():
            return HttpResponse("")

        import uuid
        context = {
            "active_order": order,
            "idempotency_key": uuid.uuid4().hex
        }
        return render(request, "ordering/partials/checkout_modal.html", context)


class POSProcessPaymentView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "payments.capture"
    
    def post(self, request, *args, **kwargs):
        order_id = request.session.get('active_order_id')
        if not order_id:
            return HttpResponse("")

        # Ensure request idempotency
        idempotency_key = request.POST.get('idempotency_key')
        from django.core.cache import cache
        cache_key = f"checkout_idempotency_{idempotency_key}" if idempotency_key else None
        
        if cache_key:
            if not cache.add(cache_key, "PROCESSING", timeout=60):
                # If key already exists in cache, it's a duplicate request
                return HttpResponse("<div class='p-4 text-center text-red-600'>Duplicate request detected. Processing already in progress.</div>", status=429)

        order = get_object_or_404(Order, id=order_id)
        method = request.POST.get('method', 'CASH')
        tendered = request.POST.get('tendered')
        
        if tendered:
            tendered = Decimal(tendered)
        else:
            tendered = order.total

        try:
            from contexts.ordering.services.checkout_service import complete_checkout_transaction

            order, invoice, print_jobs = complete_checkout_transaction(
                order_id=order.id,
                method=method,
                tendered=tendered,
                performed_by_id=request.user.id if request.user.is_authenticated else None,
            )

            # Post-commit notifications & table release
            try:
                from contexts.ordering.realtime import broadcast_kds_update
                _tenant_id = getattr(request, "tenant_id", None)
                broadcast_kds_update(tenant_id=_tenant_id, message="New order received.")
            except Exception:
                pass

            if order.table_id:
                from contexts.restaurant.models.layout import DiningTable
                from contexts.restaurant.domain.enums import TableStatus
                DiningTable.objects.filter(id=order.table_id).update(status=TableStatus.VACANT)

            # Clear session cart
            if 'active_order_id' in request.session:
                del request.session['active_order_id']

            return render(
                request,
                "ordering/partials/checkout_success_modal.html",
                {
                    "print_jobs": print_jobs,
                    "invoice": invoice,
                    "order": order,
                },
            )

            
        except Exception as e:
            import traceback
            with open("debug_payment_error.log", "a") as f:
                f.write("=== PAYMENT ERROR ===\n")
                f.write(traceback.format_exc() + "\n")
            
            # Return an alert script and reset the button state so it's not stuck
            error_html = f"""
            <script>
                alert('Payment Error: {str(e)}');
                document.getElementById('checkout-form').__x.$data.processing = false;
            </script>
            """
            return HttpResponse(error_html)


from contexts.ordering.models.kot import KOT
from contexts.ordering.domain.enums import KOTStatus
from django.utils import timezone

def get_kds_metrics(kots):
    now = timezone.now()
    waiting_count = 0
    preparing_count = 0
    ready_count = 0
    delayed_count = 0
    
    for kot in kots:
        if kot.status == KOTStatus.NEW:
            waiting_count += 1
        elif kot.status == KOTStatus.PREPARING:
            preparing_count += 1
        elif kot.status == KOTStatus.READY:
            ready_count += 1
            
        if kot.status in [KOTStatus.NEW, KOTStatus.PREPARING]:
            if (now - kot.created_at_kot).total_seconds() > 900:
                delayed_count += 1
                
    today = now.date()
    todays_kots = KOT.objects.filter(created_at_kot__date=today)
    total_today = todays_kots.count()
    completed_today = todays_kots.filter(status__in=[KOTStatus.READY, KOTStatus.SERVED]).count()
    completion_rate = int((completed_today / total_today * 100)) if total_today > 0 else 0
    
    return {
        "metric_active": waiting_count + preparing_count,
        "metric_waiting": waiting_count,
        "metric_preparing": preparing_count,
        "metric_ready": ready_count,
        "metric_delayed": delayed_count,
        "metric_completion": completion_rate,
        "metric_avg_prep": "14m 30s",
    }

def attach_waiters_and_stations_to_kots(kots):
    from contexts.employees.models import EmployeeProfile
    from contexts.restaurant.models.kitchen import KitchenStation

    waiters = EmployeeProfile.objects.filter(is_active=True)
    waiter_map = {str(w.id): w.user.get_full_name() or w.user.email for w in waiters}

    stations = KitchenStation.objects.filter(is_active=True)
    station_map = {str(s.id): s.name for s in stations}

    for kot in kots:
        if kot.order and kot.order.waiter_id and str(kot.order.waiter_id) in waiter_map:
            kot.waiter_name = waiter_map[str(kot.order.waiter_id)]
        else:
            kot.waiter_name = None

        if kot.kitchen_station_id and str(kot.kitchen_station_id) in station_map:
            kot.station_name = station_map[str(kot.kitchen_station_id)]
        else:
            kot.station_name = "Main Kitchen"
    return kots

# Backward compatibility alias
attach_waiters_to_kots = attach_waiters_and_stations_to_kots


@method_decorator(never_cache, name='dispatch')
class KDSMainView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    permission_required = "kds.view"
    template_name = "ordering/kds.html"

    def get_context_data(self, **kwargs):
        from contexts.restaurant.models.kitchen import KitchenStation
        context = super().get_context_data(**kwargs)
        station_id = self.request.GET.get('station_id', '').strip()

        qs = KOT.objects.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING, KOTStatus.READY]
        ).prefetch_related('items', 'items__order_item').order_by('-created_at_kot')

        if station_id:
            qs = qs.filter(kitchen_station_id=station_id)

        context["kots"] = attach_waiters_and_stations_to_kots(list(qs))
        context["stations"] = KitchenStation.objects.filter(is_active=True).order_by('sort_order', 'name')
        context["selected_station_id"] = station_id
        context.update(get_kds_metrics(qs))
        return context


@method_decorator(never_cache, name='dispatch')
class KDSTicketListView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "kds.view"
    template_name = "ordering/partials/kds_board.html"
    context_object_name = "kots"

    def get_queryset(self):
        station_id = self.request.GET.get('station_id', '').strip()
        qs = KOT.objects.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING, KOTStatus.READY]
        ).prefetch_related('items', 'items__order_item').order_by('-created_at_kot')
        if station_id:
            qs = qs.filter(kitchen_station_id=station_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        station_id = self.request.GET.get('station_id', '').strip()
        kots_list = attach_waiters_and_stations_to_kots(list(context["kots"]))
        context["kots"] = kots_list
        context["selected_station_id"] = station_id
        context["is_htmx"] = self.request.headers.get('HX-Request') == 'true'
        context.update(get_kds_metrics(context["kots"]))
        return context


class KDSUpdateStatusView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "kds.update_status"
    
    def post(self, request, kot_id, status, *args, **kwargs):
        from django.db import transaction
        from contexts.ordering.realtime import broadcast_kds_update

        kot = get_object_or_404(KOT, id=kot_id)

        if status == 'PREPARING' and kot.status == KOTStatus.NEW:
            kot.status = KOTStatus.PREPARING
        elif status == 'READY' and kot.status == KOTStatus.PREPARING:
            kot.status = KOTStatus.READY

        kot.save(update_fields=['status', 'updated_at'])

        tenant_id = getattr(request, "tenant_id", None)
        friendly = {"PREPARING": "Preparing", "READY": "Ready"}.get(status, status.title())
        transaction.on_commit(
            lambda: broadcast_kds_update(
                tenant_id=tenant_id,
                message=f"Order #{kot.number} moved to {friendly}.",
                kot_number=kot.number,
                action=status,
            )
        )

        station_id = request.GET.get('station_id', '').strip()
        qs = KOT.objects.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING, KOTStatus.READY]
        ).prefetch_related('items', 'items__order_item').order_by('-created_at_kot')
        if station_id:
            qs = qs.filter(kitchen_station_id=station_id)
        
        kots_list = attach_waiters_and_stations_to_kots(list(qs))
        
        context = {
            "kots": kots_list,
            "updated_kot": kot,
            "action_status": status,
            "selected_station_id": station_id,
            "is_htmx": True
        }
        context.update(get_kds_metrics(qs))
        return render(request, "ordering/partials/kds_board.html", context)


class KDSBumpItemView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "kds.update_status"

    def post(self, request, item_id, *args, **kwargs):
        from django.db import transaction
        from contexts.ordering.realtime import broadcast_kds_update
        from contexts.ordering.models.kot import KOTItem

        kot_item = get_object_or_404(KOTItem, id=item_id)
        kot_item.is_completed = not kot_item.is_completed
        kot_item.save(update_fields=["is_completed", "updated_at"])

        tenant_id = getattr(request, "tenant_id", None)
        transaction.on_commit(
            lambda: broadcast_kds_update(
                tenant_id=tenant_id,
                message=f"Item '{kot_item.name_snapshot}' updated in Order #{kot_item.kot.number}.",
                kot_number=kot_item.kot.number,
                action="ITEM_BUMPED",
            )
        )

        station_id = request.GET.get('station_id', '').strip()
        qs = KOT.objects.filter(
            status__in=[KOTStatus.NEW, KOTStatus.PREPARING, KOTStatus.READY]
        ).prefetch_related('items', 'items__order_item').order_by('-created_at_kot')
        if station_id:
            qs = qs.filter(kitchen_station_id=station_id)

        kots_list = attach_waiters_and_stations_to_kots(list(qs))

        context = {
            "kots": kots_list,
            "selected_station_id": station_id,
            "is_htmx": True
        }
        context.update(get_kds_metrics(qs))
        return render(request, "ordering/partials/kds_board.html", context)


from contexts.restaurant.models.layout import DiningTable
from contexts.restaurant.domain.enums import TableStatus
from contexts.ordering.domain.enums import OrderStatus, OrderType


@method_decorator(never_cache, name='dispatch')
class POSTableMapView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.view"
    
    def get(self, request, *args, **kwargs):
        tables = DiningTable.objects.filter(is_active=True, is_deleted=False).order_by('number')
        return render(request, "ordering/partials/table_map_modal.html", {"tables": tables})


class POSSelectTableView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.create"
    
    def post(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(DiningTable, id=table_id)
        
        if table.status == TableStatus.VACANT:
            # Create a new order for this table
            # NOTE: We assume a default location_id for now as in POSAddToCartView
            location_id = "00000000-0000-0000-0000-000000000000" 
            if hasattr(request, 'tenant_id') and getattr(request, 'branch_id', None):
                location_id = request.branch_id
                
            order = Order.objects.create(
                location_id=location_id,
                table_id=table.id,
                type=OrderType.DINE_IN,
                created_by=request.user.id
            )
            # Mark table occupied
            table.status = TableStatus.OCCUPIED
            table.save(update_fields=['status'])
            
            request.session['active_order_id'] = str(order.id)
            
        elif table.status == TableStatus.OCCUPIED:
            # Find the active order for this table
            order = Order.objects.filter(
                table_id=table.id, 
                status=OrderStatus.OPEN
            ).first()
            if order:
                request.session['active_order_id'] = str(order.id)
            else:
                # Edge case: occupied but no open order found, reset it
                table.status = TableStatus.VACANT
                table.save(update_fields=['status'])
                if 'active_order_id' in request.session:
                    del request.session['active_order_id']
                order = None
                
        # Re-fetch order and render cart panel
        active_order = None
        order_id = request.session.get('active_order_id')
        if order_id:
            active_order = Order.objects.filter(id=order_id).first()
            
        return render(request, "ordering/partials/cart_panel.html", {"active_order": active_order})


from django.shortcuts import redirect

class POSTableMainView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    permission_required = "orders.view"
    template_name = "ordering/pos_tables.html"
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from contexts.employees.models import EmployeeProfile
        waiters = EmployeeProfile.objects.filter(is_active=True)
        waiter_map = {str(w.id): w.user.get_full_name() or w.user.email for w in waiters}
        
        tables = DiningTable.objects.filter(is_active=True, is_deleted=False).order_by('number')
        for table in tables:
            if table.assigned_waiter_id and str(table.assigned_waiter_id) in waiter_map:
                table.waiter_name = waiter_map[str(table.assigned_waiter_id)]
            else:
                table.waiter_name = None
                    
        context["tables"] = tables
        context["waiters"] = waiters
        
        return context


class POSTableActionView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.create"
    
    def post(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(DiningTable, id=table_id)
        
        if table.status == TableStatus.VACANT:
            location_id = "00000000-0000-0000-0000-000000000000" 
            if hasattr(request, 'tenant_id') and getattr(request, 'branch_id', None):
                location_id = request.branch_id
                
            order = Order.objects.create(
                location_id=location_id,
                table_id=table.id,
                type=OrderType.DINE_IN,
                created_by=request.user.id
            )
            table.status = TableStatus.OCCUPIED
            table.save(update_fields=['status'])
            
            request.session['active_order_id'] = str(order.id)
            
        elif table.status == TableStatus.OCCUPIED:
            order = Order.objects.filter(
                table_id=table.id, 
                status=OrderStatus.OPEN
            ).first()
            if order:
                request.session['active_order_id'] = str(order.id)
            else:
                table.status = TableStatus.VACANT
                table.save(update_fields=['status'])
                if 'active_order_id' in request.session:
                    del request.session['active_order_id']
                    
        return redirect('ordering:pos_main')


class TableTransferView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.update"
    
    def post(self, request, source_table_id, target_table_id, *args, **kwargs):
        source_table = get_object_or_404(DiningTable, id=source_table_id)
        target_table = get_object_or_404(DiningTable, id=target_table_id)
        
        # Ensure source is occupied and target is vacant
        if source_table.status != TableStatus.OCCUPIED or target_table.status != TableStatus.VACANT:
            return redirect('ordering:pos_tables_main')
            
        order = Order.objects.filter(
            table_id=source_table.id, 
            status=OrderStatus.OPEN
        ).first()
        
        if order:
            # Transfer the order
            order.table_id = target_table.id
            order.save(update_fields=['table_id'])
            
            # Update table statuses
            source_table.status = TableStatus.VACANT
            source_table.save(update_fields=['status'])
            
            target_table.status = TableStatus.OCCUPIED
            target_table.save(update_fields=['status'])
            
        return redirect('ordering:pos_tables_main')

class TransferTableModalView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "orders.view"
    
    def get(self, request, table_id, *args, **kwargs):
        source_table = get_object_or_404(DiningTable, id=table_id)
        vacant_tables = DiningTable.objects.filter(
            status=TableStatus.VACANT, 
            is_active=True, 
            is_deleted=False
        ).order_by('floor__sort_order', 'number')
        
        return render(request, "ordering/partials/transfer_table_modal.html", {
            "source_table": source_table,
            "vacant_tables": vacant_tables
        })


class PrintQueueView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "ordering.view_orders"
    template_name = "ordering/print_queue.html"
    context_object_name = "print_jobs"
    paginate_by = 50

    def get_queryset(self):
        from contexts.ordering.models.print_job import PrintJob
        # Ordering by -created_at for history
        return PrintJob.objects.filter(is_deleted=False).order_by("-created_at")


class ManualReprintView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "ordering.manage_orders"

    def post(self, request, job_id, *args, **kwargs):
        from contexts.ordering.models.print_job import PrintJob
        from contexts.ordering.services.printing import execute_print_job
        from contexts.ordering.domain.enums import PrintJobStatus

        job = get_object_or_404(PrintJob, id=job_id, is_deleted=False)
        
        # Reset retry count and mark as pending/printing
        job.retry_count = 0
        job.status = PrintJobStatus.PENDING
        job.error_message = ""
        job.save(update_fields=["retry_count", "status", "error_message", "updated_at"])

        # Execute inline for immediate feedback (or could trigger celery)
        success = execute_print_job(job)

        if success:
            from django.contrib import messages
            messages.success(request, f"Successfully reprinted {job.get_job_type_display()} for Order #{job.order.order_number}.")
        else:
            from django.contrib import messages
            messages.error(request, f"Reprint failed: {job.error_message}")

        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/ordering/print-queue/'))
