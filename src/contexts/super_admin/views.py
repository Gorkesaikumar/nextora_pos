from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
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

class PlatformDashboardView(SuperAdminRequiredMixin, TemplateView):
    template_name = "super_admin/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        from contexts.tenants.models import Tenant, TenantCategory
        from contexts.identity.models import User
        from contexts.billing.models.subscription import Subscription
        from contexts.billing.domain.enums import SubscriptionStatus
        from contexts.ordering.models.order import Order
        from django.db.models import Sum, Count, Q
        from django.db import connection
        from django.utils import timezone
        
        now = timezone.now()
        
        # 1. Tenant Metrics
        tenants = Tenant.objects.all()
        active_restaurants = tenants.filter(status=Tenant.Status.ACTIVE).count()
        trial_restaurants = tenants.filter(status=Tenant.Status.TRIAL).count()
        suspended_restaurants = tenants.filter(status=Tenant.Status.SUSPENDED).count()
        
        # 2. User Metrics
        total_users = User.objects.count()
        new_users_today = User.objects.filter(created_at__date=now.date()).count()
        
        # 3. Revenue & Subscriptions (SaaS MRR)
        active_subs = Subscription.objects.filter(status=SubscriptionStatus.ACTIVE)
        mrr_data = active_subs.aggregate(mrr=Sum('price_amount'))
        mrr = mrr_data['mrr'] or 0
        arr = mrr * 12
        paid_subs = active_subs.count()
        expired_subs = Subscription.objects.filter(
            Q(status=SubscriptionStatus.CANCELED) | 
            Q(status=SubscriptionStatus.PAST_DUE, grace_until__lt=now)
        ).count()
        
        # 4. Global Ordering Metrics
        total_orders = Order.all_objects.count()
        orders_today = Order.all_objects.filter(created_at__date=now.date()).count()
        
        # 5. Database Size (Postgres only)
        db_size = "0 MB"
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT pg_size_pretty(pg_database_size(current_database()));")
                row = cursor.fetchone()
                if row:
                    db_size = row[0]
        except Exception:
            db_size = "Unknown"
            
        # 6. Pie Chart Data: Subscription Distribution
        sub_distribution = list(
            Subscription.objects.values('plan__name')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # 7. Pie Chart Data: Restaurant Categories
        category_distribution = list(
            Tenant.objects.values('category')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        # Convert choice values to labels
        for cat in category_distribution:
            cat_label = dict(TenantCategory.choices).get(cat['category'], cat['category'])
            cat['label'] = cat_label

        # 8. Time-Series Data (Revenue Trend - last 7 days)
        import json
        from django.db.models.functions import TruncDay
        from datetime import timedelta
        
        last_7_days = now - timedelta(days=7)
        daily_revenue = list(
            Subscription.objects.filter(status=SubscriptionStatus.ACTIVE, created_at__gte=last_7_days)
            .annotate(day=TruncDay('created_at'))
            .values('day')
            .annotate(total=Sum('price_amount'))
            .order_by('day')
        )
        
        # 9. Recent Onboarded Tenants
        recent_tenants = Tenant.objects.order_by('-created_at')[:5]

        # 10. Recent Payments
        from contexts.billing.models.payment import SubscriptionPayment
        recent_payments = SubscriptionPayment.all_objects.select_related('tenant').order_by('-created_at')[:5]

        context.update({
            "active_restaurants": active_restaurants,
            "trial_restaurants": trial_restaurants,
            "suspended_restaurants": suspended_restaurants,
            "total_users": total_users,
            "new_users_today": new_users_today,
            "mrr": mrr,
            "arr": arr,
            "paid_subs": paid_subs,
            "expired_subs": expired_subs,
            "total_orders": total_orders,
            "orders_today": orders_today,
            "db_size": db_size,
            "sub_distribution": sub_distribution,
            "category_distribution": category_distribution,
            "daily_revenue": json.dumps([float(x['total']) for x in daily_revenue] if daily_revenue else [0,0,0,0,0,0,0]),
            "daily_revenue_labels": json.dumps([x['day'].strftime('%b %d') for x in daily_revenue] if daily_revenue else ['-','-','-','-','-','-','-']),
            "recent_tenants": recent_tenants,
            "recent_payments": recent_payments,
        })
        
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
        qs = User.objects.all()
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(email__icontains=q) | Q(full_name__icontains=q))
        
        status = self.request.GET.get("status", "").strip()
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
            
        return qs.order_by("-created_at")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["current_q"] = self.request.GET.get("q", "")
        ctx["current_status"] = self.request.GET.get("status", "")
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
