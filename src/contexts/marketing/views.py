from django.views.generic import TemplateView
from django.shortcuts import redirect

class HomeView(TemplateView):
    template_name = "marketing/home.html"
    
    def dispatch(self, request, *args, **kwargs):
        # Redirect authenticated users to the dashboard instead of the public homepage
        if request.user.is_authenticated:
            return redirect('reporting:home')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from contexts.tenants.models import Tenant
        from contexts.ordering.models.order import Order
        from contexts.billing.models.plan import Plan
        
        # Calculate real-time stats
        context['tenant_count'] = Tenant.objects.filter(status='ACTIVE').count()
        context['order_count'] = Order.all_objects.count()
        
        # Fetch dynamic pricing plans
        plans = Plan.objects.filter(is_active=True, is_public=True).prefetch_related('plan_features').order_by('display_order')
        
        plan_data = []
        global_discount = 16
        if plans.exists():
            global_discount = max(p.yearly_discount_percentage for p in plans)
            
        for plan in plans:
            monthly_price = int(plan.sale_price) if not plan.custom_pricing else 0
            yearly_price = int(monthly_price * (1 - (plan.yearly_discount_percentage / 100.0)))
            
            plan_data.append({
                'code': plan.code,
                'name': plan.display_name or plan.name,
                'description': plan.description,
                'monthly_price': monthly_price,
                'yearly_price': yearly_price,
                'is_popular': plan.is_popular,
                'custom_pricing': plan.custom_pricing,
                'features': plan.plan_features.filter(is_included=True).order_by('display_order')
            })
            
        context['pricing_plans'] = plan_data
        context['global_discount'] = global_discount
        return context
