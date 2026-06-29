from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, TemplateView, View, CreateView, UpdateView, DeleteView
from django.shortcuts import render, get_object_or_404

from contexts.restaurant.models.branch import Branch
from contexts.restaurant.models.layout import DiningTable

class BranchListView(LoginRequiredMixin, ListView):
    model = Branch
    template_name = "restaurant/branch_list.html"
    context_object_name = "branches"
    
    def get_queryset(self):
        # Show both active and archived branches in list (use archive status badge)
        return super().get_queryset().filter(is_deleted=False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = list(context['branches'])
        
        # Aggregate dashboard metrics
        from django.db.models import Sum, Count
        from django.utils import timezone
        from contexts.ordering.models.order import Order
        from contexts.employees.models import EmployeeProfile
        from contexts.inventory.models.warehouse import Warehouse
        from contexts.inventory.models.item import InventoryItem
        
        today = timezone.localdate()
        orders = Order.objects.filter(opened_at__date=today, status='SETTLED')
        
        # Today's Sales per Branch
        sales_by_branch = {
            str(item['location_id']): item['total_sales'] 
            for item in orders.values('location_id').annotate(total_sales=Sum('total'))
        }
        
        # Employees per Branch
        emps = EmployeeProfile.objects.filter(is_active=True)
        emps_by_branch = {
            str(item['location_id']): item['count']
            for item in emps.values('location_id').annotate(count=Count('id'))
        }
        
        # Inventory Value per Branch
        items = InventoryItem.objects.filter(is_deleted=False)
        val_by_wh = {}
        for item in items:
            val = (item.quantity_on_hand or 0) * (item.average_cost or 0)
            val_by_wh[item.warehouse_id] = val_by_wh.get(item.warehouse_id, 0) + val
            
        whs = Warehouse.objects.filter(is_deleted=False)
        inv_by_branch = {}
        for wh in whs:
            if wh.branch_id:
                branch_str = str(wh.branch_id)
                inv_by_branch[branch_str] = inv_by_branch.get(branch_str, 0) + val_by_wh.get(wh.id, 0)
                
        # Enrich branch objects with aggregated statistics
        for b in branches:
            b.today_sales = sales_by_branch.get(str(b.id), 0.0)
            b.emp_count = emps_by_branch.get(str(b.id), 0)
            b.inv_value = inv_by_branch.get(str(b.id), 0.0)
            
        # Dashboard aggregates
        context.update({
            'total_branches': len(branches),
            'active_branches': sum(1 for b in branches if b.is_active and not b.is_archived),
            'total_sales_sum': sum(b.today_sales for b in branches),
            'total_staff_sum': sum(b.emp_count for b in branches),
            'branches': branches
        })
        return context


from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.http import HttpResponse, HttpResponseRedirect
from contexts.restaurant.forms import BranchForm

class BranchCreateView(LoginRequiredMixin, CreateView):
    model = Branch
    form_class = BranchForm
    template_name = "restaurant/partials/branch_form_modal.html"
    success_url = reverse_lazy('restaurant:branch_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        if not Branch.objects.filter(is_deleted=False, is_default=True).exists():
            form.instance.is_default = True
            
        if form.cleaned_data.get('is_default'):
            Branch.objects.filter(is_deleted=False).update(is_default=False)
            
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return response


class BranchUpdateView(LoginRequiredMixin, UpdateView):
    model = Branch
    form_class = BranchForm
    template_name = "restaurant/partials/branch_form_modal.html"
    success_url = reverse_lazy('restaurant:branch_list')

    def form_valid(self, form):
        if form.cleaned_data.get('is_default'):
            Branch.objects.filter(is_deleted=False).exclude(id=self.object.id).update(is_default=False)
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return response


class BranchDeleteView(LoginRequiredMixin, DeleteView):
    model = Branch
    success_url = reverse_lazy('restaurant:branch_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return HttpResponseRedirect(self.get_success_url())


class BranchArchiveView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        branch = get_object_or_404(Branch, id=pk)
        branch.is_archived = True
        branch.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return HttpResponseRedirect(reverse_lazy('restaurant:branch_list'))


class BranchToggleStatusView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        branch = get_object_or_404(Branch, id=pk)
        branch.is_active = not branch.is_active
        branch.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return HttpResponseRedirect(reverse_lazy('restaurant:branch_list'))


class BranchSetDefaultView(LoginRequiredMixin, View):
    def post(self, request, pk, *args, **kwargs):
        Branch.objects.filter(is_deleted=False).update(is_default=False)
        branch = get_object_or_404(Branch, id=pk)
        branch.is_default = True
        branch.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'branchListChanged'})
        return HttpResponseRedirect(reverse_lazy('restaurant:branch_list'))


from contexts.catalog.models.routing import Printer
from contexts.restaurant.forms import PrinterForm

class PrinterListView(LoginRequiredMixin, ListView):
    model = Printer
    template_name = "restaurant/printer_list.html"
    context_object_name = "printers"

    def get_queryset(self):
        qs = super().get_queryset().filter(is_deleted=False)
        branch_id = self.request.GET.get('branch')
        if branch_id:
            qs = qs.filter(location_id=branch_id)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = {b.id: b.name for b in Branch.objects.filter(is_deleted=False)}
        for p in context['printers']:
            p.branch_name = branches.get(p.location_id, "Global / All Branches")
        context['branches'] = Branch.objects.filter(is_deleted=False)
        
        # Printer Dashboard Counts
        printers_list = list(context['printers'])
        context.update({
            'total_printers': len(printers_list),
            'online_printers': sum(1 for p in printers_list if p.status == 'online' and p.is_active),
            'offline_printers': sum(1 for p in printers_list if p.status == 'offline' or not p.is_active)
        })
        return context


class PrinterCreateView(LoginRequiredMixin, CreateView):
    model = Printer
    form_class = PrinterForm
    template_name = "restaurant/partials/printer_form_modal.html"
    success_url = reverse_lazy('restaurant:printer_list')

    def form_valid(self, form):
        form.instance.tenant_id = self.request.tenant_id
        if form.cleaned_data.get('is_default'):
            Printer.objects.filter(is_deleted=False).update(is_default=False)
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'printerListChanged'})
        return response


class PrinterUpdateView(LoginRequiredMixin, UpdateView):
    model = Printer
    form_class = PrinterForm
    template_name = "restaurant/partials/printer_form_modal.html"
    success_url = reverse_lazy('restaurant:printer_list')

    def form_valid(self, form):
        if form.cleaned_data.get('is_default'):
            Printer.objects.filter(is_deleted=False).exclude(id=self.object.id).update(is_default=False)
        response = super().form_valid(form)
        if self.request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'printerListChanged'})
        return response


class PrinterDeleteView(LoginRequiredMixin, DeleteView):
    model = Printer
    success_url = reverse_lazy('restaurant:printer_list')

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.save()
        if request.htmx:
            return HttpResponse(status=204, headers={'HX-Trigger': 'printerListChanged'})
        return HttpResponseRedirect(self.get_success_url())


class PrinterTestPrintView(LoginRequiredMixin, View):
    def get(self, request, pk, *args, **kwargs):
        printer = get_object_or_404(Printer, id=pk)
        receipt = {
            'printer_name': printer.name,
            'connection': f"{printer.connection_type.upper()} ({printer.ip_address or 'USB Connection'})",
            'timestamp': timezone.now().strftime("%Y-%m-%d %H:%M:%S"),
            'test_lines': [
                "NEXTORA POS - SYSTEM DIAGNOSTIC",
                "===============================",
                f"PRINTER TYPE: {printer.get_kind_display().upper()}",
                f"PAPER WIDTH: {printer.paper_width}",
                f"PORT: {printer.port}",
                "===============================",
                "STATUS: ONLINE - SUCCESS",
                "-------------------------------",
                "TEST PATTERN:",
                "0123456789 ABCDEFGHIJKLMNOP",
                "-------------------------------",
                "Simulated Test Print Complete."
            ]
        }
        return render(request, "restaurant/partials/printer_test_modal.html", {"receipt": receipt})


class TableListView(LoginRequiredMixin, ListView):
    model = DiningTable
    template_name = "restaurant/table_list.html"
    context_object_name = "tables"

    def get_queryset(self):
        qs = super().get_queryset().filter(
            is_active=True, is_deleted=False
        ).select_related('branch')
        
        # Search by table number
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(number__icontains=q)
            
        # Filter by status
        status_filter = self.request.GET.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
            
        return qs.order_by('branch__name', 'number')


from django.views.generic import CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from contexts.restaurant.forms import DiningTableForm
from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin

class TableCreateView(LoginRequiredMixin, CreateView):
    model = DiningTable
    form_class = DiningTableForm
    template_name = "restaurant/partials/table_form_modal.html"
    success_url = reverse_lazy('restaurant:table_list')

    def form_valid(self, form):
        from contexts.restaurant.models.branch import Branch
        first_branch = Branch.objects.first()
        if not first_branch:
            from contexts.restaurant.models.restaurant import Restaurant
            rest = Restaurant.objects.first()
            if not rest:
                rest = Restaurant.objects.create(name="Default Concept", slug="default-concept", is_default=True)
            first_branch = Branch.objects.create(restaurant=rest, name="Main Branch", code="MAIN")
        
        form.instance.branch = first_branch
        response = super().form_valid(form)
        if self.request.htmx:
            from django.http import HttpResponse
            return HttpResponse(status=204, headers={'HX-Trigger': 'tableListChanged'})
        return response

class TableUpdateView(LoginRequiredMixin, UpdateView):
    model = DiningTable
    form_class = DiningTableForm
    template_name = "restaurant/partials/table_form_modal.html"
    success_url = reverse_lazy('restaurant:table_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        if self.request.htmx:
            from django.http import HttpResponse
            return HttpResponse(status=204, headers={'HX-Trigger': 'tableListChanged'})
        return response

class TableDeleteView(LoginRequiredMixin, DeleteView):
    model = DiningTable
    success_url = reverse_lazy('restaurant:table_list')

    def delete(self, request, *args, **kwargs):
        # Soft delete logic
        self.object = self.get_object()
        self.object.is_deleted = True
        self.object.save()
        if request.htmx:
            from django.http import HttpResponse
            return HttpResponse(status=204, headers={'HX-Trigger': 'tableListChanged'})
        from django.http import HttpResponseRedirect
        return HttpResponseRedirect(self.get_success_url())

from django.db.models import Count, Avg, F, Q, ExpressionWrapper, fields
from django.utils import timezone
from datetime import timedelta
from django.db import models

from contexts.tenants.models import Tenant
from contexts.ordering.models.order import Order

class TableAnalyticsView(LoginRequiredMixin, TemplateView):
    template_name = "restaurant/table_analytics.html"
    permission_required = "restaurant.view_reports"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # 1. Occupancy Rate
        total_tables = DiningTable.objects.filter(is_active=True, is_deleted=False).count()
        occupied_tables = DiningTable.objects.filter(is_active=True, is_deleted=False, status='occupied').count()
        occupancy_rate = int((occupied_tables / total_tables * 100)) if total_tables > 0 else 0
        
        # 2. Avg Turnaround Time (from settled orders in last 7 days)
        seven_days_ago = timezone.now() - timedelta(days=7)
        orders = Order.objects.filter(
            table_id__isnull=False, 
            status='SETTLED', 
            created_at__gte=seven_days_ago
        )
        
        # Approximation: we don't have settled_at explicitly in Order model currently,
        # but we can simulate average duration based on KOT timestamps or just use a placeholder
        # For a real implementation, we'd calculate: Avg(F('settled_at') - F('created_at'))
        avg_turnaround_minutes = 45 # Placeholder until settled_at is available
        
        # 3. Most Popular Table
        popular_tables = Order.objects.filter(
            table_id__isnull=False, 
            created_at__gte=seven_days_ago
        ).values('table_id').annotate(order_count=Count('id')).order_by('-order_count')[:5]
        
        # Map UUIDs back to Table objects
        table_ids = [p['table_id'] for p in popular_tables]
        tables = {t.id: t for t in DiningTable.objects.filter(id__in=table_ids)}
        
        popular_table_stats = []
        for p in popular_tables:
            if p['table_id'] in tables:
                popular_table_stats.append({
                    'table': tables[p['table_id']],
                    'count': p['order_count']
                })
                
        context.update({
            'occupancy_rate': occupancy_rate,
            'occupied_tables': occupied_tables,
            'vacant_tables': total_tables - occupied_tables,
            'total_tables': total_tables,
            'avg_turnaround_minutes': avg_turnaround_minutes,
            'popular_tables': popular_table_stats
        })
        
        return context

class TableQRModalView(LoginRequiredMixin, View):
    
    def get(self, request, table_id, *args, **kwargs):
        table = get_object_or_404(DiningTable, id=table_id)
        
        # The URL that the QR code will point to when scanned by a customer
        # For now, it points to a hypothetical customer ordering app
        # Replace 'example.com' with your actual domain later
        tenant = Tenant.objects.get(id=request.tenant_id)
        ordering_url = f"https://order.nextora.com/{tenant.slug}/table/{table.id}"
        
        from urllib.parse import quote
        qr_image_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote(ordering_url)}"
        
        
        return render(request, "restaurant/partials/table_qr_modal.html", {
            "table": table,
            "qr_image_url": qr_image_url,
            "ordering_url": ordering_url
        })
