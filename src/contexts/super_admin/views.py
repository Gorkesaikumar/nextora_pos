import json
import datetime
from django.http import JsonResponse, StreamingHttpResponse, HttpResponse
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, Avg, Q, Prefetch
from django.db.models.functions import TruncDay
from django.utils import timezone
from .forms import PlatformAuthenticationForm
from .mixins import SuperAdminRequiredMixin


class PlatformLoginView(LoginView):
    template_name = "super_admin/login.html"
    form_class = PlatformAuthenticationForm
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy("super_admin:dashboard")

class PlatformLogoutView(LogoutView):
    next_page = reverse_lazy("super_admin:login")


def _get_date_window(time_filter: str, now):
    """Return (start_date, label) for the given filter string."""
    if time_filter == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0), "Today"
    elif time_filter == "last_7_days":
        return now - datetime.timedelta(days=7), "Last 7 Days"
    elif time_filter == "this_month":
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0), "This Month"
    elif time_filter == "this_year":
        return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0), "This Year"
    elif time_filter == "last_90_days":
        return now - datetime.timedelta(days=90), "Last 90 Days"
    else:  # last_30_days (default)
        return now - datetime.timedelta(days=30), "Last 30 Days"


def _get_dashboard_stats(time_filter="last_30_days"):
    """Single source of truth for all dashboard metrics. Returns a dict."""
    from contexts.tenants.models import Tenant, TenantCategory
    from contexts.identity.models import User
    from contexts.billing.models.subscription import Subscription
    from contexts.billing.domain.enums import SubscriptionStatus
    from contexts.ordering.models.order import Order

    now = timezone.now()
    start_date, filter_label = _get_date_window(time_filter, now)

    # ── Tenant metrics ───────────────────────────────────────────────────────
    tenants = Tenant.objects.all()
    total_restaurants = tenants.count()
    active_restaurants = tenants.filter(status=Tenant.Status.ACTIVE).count()
    trial_restaurants = tenants.filter(status=Tenant.Status.TRIAL).count()
    suspended_restaurants = tenants.filter(status=Tenant.Status.SUSPENDED).count()

    # ── User metrics ─────────────────────────────────────────────────────────
    total_users = User.objects.count()
    new_users_today = User.objects.filter(created_at__date=now.date()).count()

    # ── Subscription / Revenue metrics ───────────────────────────────────────
    # ponytail: MRR includes ACTIVE + TRIALING; ceiling = doesn't distinguish paid vs trial revenue
    all_subs = Subscription.all_objects
    live_subs = all_subs.filter(status__in=[SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING])
    active_subs = all_subs.filter(status=SubscriptionStatus.ACTIVE)

    mrr_data = live_subs.aggregate(mrr=Sum('price_amount'))
    mrr = mrr_data['mrr'] or 0
    arr = mrr * 12

    paid_subs = active_subs.count()
    trialing_subs = all_subs.filter(status=SubscriptionStatus.TRIALING).count()
    expired_subs = all_subs.filter(
        Q(status=SubscriptionStatus.CANCELED) |
        Q(status=SubscriptionStatus.EXPIRED)
    ).count()

    # ── Order metrics ────────────────────────────────────────────────────────
    total_orders = Order.all_objects.count()
    orders_today = Order.all_objects.filter(created_at__date=now.date()).count()
    orders_in_window = Order.all_objects.filter(created_at__gte=start_date).count()

    # ── Revenue trend (daily subscription revenue — activations in window) ───
    daily_revenue_qs = list(
        Subscription.all_objects
        .filter(created_at__gte=start_date)
        .annotate(day=TruncDay('created_at'))
        .values('day')
        .annotate(total=Sum('price_amount'))
        .order_by('day')
    )
    daily_rev_values = [float(x['total'] or 0) for x in daily_revenue_qs]
    daily_rev_labels = [x['day'].strftime('%b %d') for x in daily_revenue_qs]

    # ── Subscription plan distribution ──────────────────────────────────────
    sub_distribution = list(
        Subscription.all_objects
        .select_related('plan')
        .values('plan__name', 'plan__display_name')
        .annotate(count=Count('id'), revenue=Sum('price_amount'))
        .order_by('-count')
    )
    plan_labels = [x['plan__display_name'] or x['plan__name'] or 'Unknown' for x in sub_distribution]
    plan_counts = [x['count'] for x in sub_distribution]
    plan_revenue = [float(x['revenue'] or 0) for x in sub_distribution]

    # ── Category distribution ────────────────────────────────────────────────
    category_distribution = list(
        Tenant.objects.values('category')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    from contexts.tenants.models import TenantCategory
    for cat in category_distribution:
        cat['label'] = dict(TenantCategory.choices).get(cat['category'], cat['category'])

    return {
        "time_filter": time_filter,
        "filter_label": filter_label,
        "total_restaurants": total_restaurants,
        "active_restaurants": active_restaurants,
        "trial_restaurants": trial_restaurants,
        "suspended_restaurants": suspended_restaurants,
        "total_users": total_users,
        "new_users_today": new_users_today,
        "mrr": mrr,
        "arr": arr,
        "paid_subs": paid_subs,
        "trialing_subs": trialing_subs,
        "expired_subs": expired_subs,
        "total_orders": total_orders,
        "orders_today": orders_today,
        "orders_in_window": orders_in_window,
        "daily_revenue": json.dumps(daily_rev_values),
        "daily_revenue_labels": json.dumps(daily_rev_labels),
        "plan_labels": json.dumps(plan_labels),
        "plan_counts": json.dumps(plan_counts),
        "plan_revenue": json.dumps(plan_revenue),
        "sub_distribution": sub_distribution,
        "category_distribution": category_distribution,
    }


class PlatformDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        time_filter = self.request.GET.get("filter", "last_30_days")

        from contexts.tenants.models import Tenant
        from contexts.billing.models.payment import SubscriptionPayment

        stats = _get_dashboard_stats(time_filter)
        context.update(stats)

        # Recent data (not filter-dependent)
        context["recent_tenants"] = Tenant.objects.order_by('-created_at').select_related()[:5]
        context["recent_payments"] = (
            SubscriptionPayment.all_objects
            .select_related('tenant', 'invoice')
            .order_by('-created_at')[:5]
        )
        return context


class PlatformDashboardStatsView(SuperAdminRequiredMixin, TemplateView):
    """JSON endpoint for the auto-refresh polling. Returns all KPI values."""
    def get(self, request, *args, **kwargs):
        time_filter = request.GET.get("filter", "last_30_days")
        stats = _get_dashboard_stats(time_filter)
        # Return only serialisable scalars (strip JSON strings that are already encoded)
        payload = {k: v for k, v in stats.items() if not isinstance(v, list)}
        # Re-encode chart data as parsed lists for JSON response
        payload["daily_revenue"] = json.loads(stats["daily_revenue"])
        payload["daily_revenue_labels"] = json.loads(stats["daily_revenue_labels"])
        payload["plan_labels"] = json.loads(stats["plan_labels"])
        payload["plan_counts"] = json.loads(stats["plan_counts"])
        payload["plan_revenue"] = json.loads(stats["plan_revenue"])
        payload["mrr"] = float(stats["mrr"])
        payload["arr"] = float(stats["arr"])
        return JsonResponse(payload)


class PlatformExportReportView(SuperAdminRequiredMixin, TemplateView):
    """Render a print-ready HTML report. The browser's print dialog handles PDF creation."""
    template_name = "super_admin/export_report.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        time_filter = self.request.GET.get("filter", "last_30_days")
        stats = _get_dashboard_stats(time_filter)
        context.update(stats)
        context["generated_at"] = timezone.now()
        return context


from django.views.generic import ListView
from django.db.models import Q

class PlatformTenantListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/tenant_list.html"
    context_object_name = "tenants"
    paginate_by = 50

    def get_queryset(self):
        from contexts.tenants.models import Tenant
        qs = Tenant.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(slug__icontains=q) | Q(legal_name__icontains=q))
        
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.tenants.models import Tenant
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = Tenant.Status.choices
        return ctx

class PlatformUserListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/user_list.html"
    context_object_name = "users"
    paginate_by = 50

    def get_queryset(self):
        from contexts.identity.models import User
        from contexts.identity.models.rbac import Membership

        qs = User.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))

        status = self.request.GET.get("status", "").strip()
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)

        # Prefetch active memberships with role + tenant in one query
        mem_prefetch = Prefetch(
            "memberships",
            queryset=Membership.objects.filter(is_active=True).select_related("role", "tenant"),
            to_attr="active_memberships",
        )
        return qs.prefetch_related(mem_prefetch).order_by("-created_at")

    def get_context_data(self, **kwargs):
        from contexts.billing.models.subscription import Subscription
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")

        # 1. Build tenant_id → subscription map in 1 query (avoids N+1)
        sub_map = {
            str(s.tenant_id): s
            for s in Subscription.all_objects.only(
                "tenant_id", "status", "current_period_end", "trial_end", "grace_until"
            )
        }

        # 2. Attach subscription + primary membership directly onto each user object
        #    This lets the template use simple dot notation: user.sub_info / user.primary_membership
        for user in ctx["users"]:
            memberships = user.active_memberships  # from prefetch
            primary = memberships[0] if memberships else None
            user.primary_membership = primary
            if primary and primary.tenant:
                user.sub_info = sub_map.get(str(primary.tenant_id))
            else:
                user.sub_info = None

        return ctx



class PlatformSubscriptionListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/subscription_list.html"
    context_object_name = "subscriptions"
    paginate_by = 50

    def get_queryset(self):
        from contexts.billing.models.subscription import Subscription
        qs = Subscription.objects.select_related("tenant", "plan").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(tenant__name__icontains=q) | Q(plan__name__icontains=q))
        
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.billing.domain.enums import SubscriptionStatus
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = SubscriptionStatus.choices
        return ctx

class PlatformInvoiceListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 50

    def get_queryset(self):
        from contexts.billing.models.invoice import SubscriptionInvoice
        qs = SubscriptionInvoice.objects.select_related("tenant", "subscription__plan").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(tenant__name__icontains=q))
        
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.billing.domain.enums import InvoiceStatus
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = InvoiceStatus.choices
        return ctx

class PlatformFeatureFlagListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/feature_flag_list.html"
    context_object_name = "flags"
    paginate_by = 50

    def get_queryset(self):
        from contexts.features.models import FeatureFlag
        qs = FeatureFlag.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(key__icontains=q) | Q(name__icontains=q))
            
        return qs.order_by("key")

class PlatformPaymentListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/payment_list.html"
    context_object_name = "payments"
    paginate_by = 50

    def get_queryset(self):
        from contexts.billing.models.payment import SubscriptionPayment
        qs = SubscriptionPayment.objects.select_related("tenant", "invoice").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(provider_payment_id__icontains=q) | Q(tenant__name__icontains=q) | Q(invoice__number__icontains=q))
        
        status = self.request.GET.get("status", "").strip()
        if status:
            qs = qs.filter(status=status)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.billing.domain.enums import PaymentStatus
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["statuses"] = PaymentStatus.choices
        return ctx

class PlatformCouponListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/coupon_list.html"
    context_object_name = "coupons"
    paginate_by = 50

    def get_queryset(self):
        from contexts.customers.models import Coupon
        qs = Coupon.objects.select_related("tenant").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(code__icontains=q) | Q(tenant__name__icontains=q))
        
        is_active = self.request.GET.get("active", "").strip()
        if is_active == "true":
            qs = qs.filter(is_active=True)
        elif is_active == "false":
            qs = qs.filter(is_active=False)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_active"] = self.request.GET.get("active", "")
        return ctx

class PlatformAnalyticsView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/analytics.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Placeholder for platform-wide analytics
        return ctx

class PlatformReportListView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/report_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Placeholder for platform-wide reports
        return ctx

class PlatformMonitoringView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/monitoring.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Placeholder for platform monitoring (Celery, Redis, etc.)
        return ctx

class PlatformSettingsView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/settings.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Placeholder for platform settings
        return ctx

class PlatformAuditLogListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/audit_log_list.html"
    context_object_name = "logs"
    paginate_by = 50

    def get_queryset(self):
        from contexts.audit.models import AuditLog
        qs = AuditLog.all_objects.select_related("tenant").all()
        
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(action__icontains=q) | Q(entity_type__icontains=q) | Q(tenant__name__icontains=q))
            
        return qs.order_by("-occurred_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        return ctx

class PlatformNotificationListView(SuperAdminRequiredMixin, ListView):
    template_name = "super_admin/notification_list.html"
    context_object_name = "notifications"
    paginate_by = 50

    def get_queryset(self):
        from contexts.notifications.models import Notification
        qs = Notification.objects.select_related("tenant", "template").all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(channel__icontains=q) | Q(tenant__name__icontains=q) | Q(status__icontains=q))
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        return ctx

from django.shortcuts import get_object_or_404
from django.db.models import Sum, Count, Avg
from django.db.models.functions import TruncDay
from django.utils import timezone
import datetime
import json

class PlatformTenantDetailsView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/partials/tenant_details_modal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.tenants.models import Tenant
        from contexts.identity.models import User
        from contexts.audit.models import AuditLog
        from contexts.billing.models.subscription import Subscription
        from contexts.ordering.models.order import Order
        from contexts.customers.models import Customer
        from contexts.catalog.models.product import Product
        from contexts.restaurant.models.layout import DiningTable
        from contexts.restaurant.models.restaurant import Restaurant

        tenant_id = self.kwargs.get("tenant_id")
        tenant = get_object_or_404(Tenant, id=tenant_id)
        
        subscription = Subscription.objects.filter(tenant=tenant).order_by('-created_at').first()
        
        owner = User.objects.filter(memberships__tenant=tenant, memberships__role__code='owner').first()
        if not owner:
            owner = User.objects.filter(memberships__tenant=tenant).order_by('created_at').first()
            
        total_orders = Order.all_objects.filter(tenant=tenant).count()
        total_customers = Customer.objects.filter(tenant=tenant).count()
        total_staff = User.objects.filter(memberships__tenant=tenant).distinct().count()
        total_menu_items = Product.objects.filter(tenant=tenant).count()
        total_branches = Restaurant.objects.filter(tenant=tenant).count()
        total_tables = DiningTable.objects.filter(tenant=tenant).count()
        
        AuditLog.all_objects.create(
            tenant=tenant,
            actor_id=self.request.user.id,
            action="tenant_details.viewed",
            entity_type="Tenant",
            entity_id=tenant.id,
            ip_address=self.request.META.get("REMOTE_ADDR")
        )
        
        ctx.update({
            "tenant": tenant,
            "subscription": subscription,
            "owner": owner,
            "total_orders": total_orders,
            "total_customers": total_customers,
            "total_staff": total_staff,
            "total_menu_items": total_menu_items,
            "total_branches": total_branches,
            "total_tables": total_tables,
        })
        return ctx

class PlatformTenantRevenueView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/partials/revenue_analytics_modal.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from contexts.tenants.models import Tenant
        from contexts.audit.models import AuditLog
        from contexts.ordering.models.order import Order
        from contexts.ordering.models.payment import Payment
        from contexts.ordering.domain.enums import OrderStatus
        
        tenant_id = self.kwargs.get("tenant_id")
        tenant = get_object_or_404(Tenant, id=tenant_id)
        
        time_filter = self.request.GET.get("filter", "last_30_days")
        now = timezone.now()
        
        if time_filter == "today":
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "last_7_days":
            start_date = now - datetime.timedelta(days=7)
        elif time_filter == "this_month":
            start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        elif time_filter == "this_year":
            start_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        else: # last_30_days
            start_date = now - datetime.timedelta(days=30)
            
        orders_in_range = Order.all_objects.filter(tenant=tenant, created_at__gte=start_date)
        completed_orders = orders_in_range.filter(status=OrderStatus.SETTLED)
        cancelled_orders = orders_in_range.filter(status=OrderStatus.VOID)
        
        total_revenue = completed_orders.aggregate(s=Sum('total'))['s'] or 0
        total_orders_count = orders_in_range.count()
        completed_count = completed_orders.count()
        cancelled_count = cancelled_orders.count()
        aov = completed_orders.aggregate(a=Avg('total'))['a'] or 0
        
        total_refunds = cancelled_orders.aggregate(s=Sum('total'))['s'] or 0
        
        daily_revenue = list(
            completed_orders
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total_day=Sum('total'))
            .order_by('day')
        )
        daily_rev_values = [float(x['total_day']) for x in daily_revenue]
        daily_rev_labels = [x['day'].strftime('%b %d') for x in daily_revenue]
        
        payments = Payment.objects.filter(tenant=tenant, created_at__gte=start_date, kind='payment')
        payment_dist = list(
            payments
            .values('method')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        pay_labels = [x['method'] for x in payment_dist]
        pay_values = [x['count'] for x in payment_dist]
        
        days_in_range = max((now - start_date).days, 1)
        avg_daily = float(total_revenue) / days_in_range if days_in_range > 0 else 0
        
        tax_collected = completed_orders.aggregate(s=Sum('tax_amount'))['s'] or 0
        net_revenue = float(total_revenue) - float(tax_collected)
        
        AuditLog.all_objects.create(
            tenant=tenant,
            actor_id=self.request.user.id,
            action="revenue_analytics.viewed",
            entity_type="Tenant",
            entity_id=tenant.id,
            ip_address=self.request.META.get("REMOTE_ADDR")
        )
        
        ctx.update({
            "tenant": tenant,
            "filter": time_filter,
            "total_revenue": total_revenue,
            "total_orders_count": total_orders_count,
            "completed_count": completed_count,
            "cancelled_count": cancelled_count,
            "aov": aov,
            "avg_daily": avg_daily,
            "total_refunds": total_refunds,
            "tax_collected": tax_collected,
            "net_revenue": net_revenue,
            "daily_rev_values": json.dumps(daily_rev_values),
            "daily_rev_labels": json.dumps(daily_rev_labels),
            "pay_labels": json.dumps(pay_labels),
            "pay_values": json.dumps(pay_values),
        })
        return ctx
