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
        
        # Calculate real-time stats
        context['tenant_count'] = Tenant.objects.filter(status='ACTIVE').count()
        context['order_count'] = Order.all_objects.count()
        return context
