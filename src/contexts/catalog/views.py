import logging

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.utils.text import slugify
from django.views.generic import CreateView, ListView, UpdateView, View, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin

from contexts.catalog.exceptions import ValidationError as CatalogValidationError, ProductNotFound
from contexts.catalog.forms import CategoryForm, ProductForm
from contexts.catalog.models.category import Category
from contexts.catalog.models.product import Product
from contexts.catalog.services import product_service
from contexts.identity.permissions.mixins import TenantPermissionRequiredMixin

logger = logging.getLogger(__name__)

class CategoryListView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "catalog.view"
    model = Category
    template_name = "catalog/category_list.html"
    context_object_name = "categories"
    
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True, is_deleted=False).prefetch_related('subcategories')


class ProductListView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "catalog.view"
    model = Product
    template_name = "catalog/product_list.html"
    context_object_name = "products"

    def get_queryset(self):
        qs = super().get_queryset().filter(
            is_active=True, is_deleted=False
        ).select_related('category', 'tax_class').prefetch_related('variants')
        
        # Handle search
        q = self.request.GET.get('q')
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q))
            
        # Handle category filter
        category_id = self.request.GET.get('category')
        if category_id:
            qs = qs.filter(category_id=category_id)
            
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Category.objects.filter(is_active=True, is_deleted=False)
        context['current_q'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', '')
        return context


class ProductCreateView(TenantPermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = "catalog.manage"
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Create'
        context['category_form'] = CategoryForm()
        return context

    def form_valid(self, form):
        try:
            product = product_service.create_product(form.cleaned_data)
        except CatalogValidationError as exc:
            for field, error_msg in exc.errors.items():
                form.add_error(field if form.fields.get(field) else None, error_msg)
            return self.form_invalid(form)

        self.object = product
        messages.success(self.request, f'Product "{product.name}" created successfully.')
        return HttpResponseRedirect(reverse("catalog:product_list"))


class ProductUpdateView(TenantPermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = "catalog.manage"
    model = Product
    form_class = ProductForm
    template_name = "catalog/product_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['action'] = 'Edit'
        context['category_form'] = CategoryForm()
        return context

    def form_valid(self, form):
        try:
            product = product_service.update_product(self.object.id, form.cleaned_data)
        except CatalogValidationError as exc:
            for field, error_msg in exc.errors.items():
                form.add_error(field if form.fields.get(field) else None, error_msg)
            return self.form_invalid(form)

        self.object = product
        messages.success(self.request, f'Product "{product.name}" updated successfully.')
        return HttpResponseRedirect(reverse("catalog:product_list"))


class ProductDeleteView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "catalog.manage"

    def post(self, request, pk, *args, **kwargs):
        try:
            product_service.delete_product(pk)
            messages.success(self.request, 'Product deleted successfully.')
        except ProductNotFound:
            messages.error(self.request, 'Product not found.')
        except Exception as e:
            logger.exception("Unexpected error deleting product")
            messages.error(self.request, "Could not delete product. Please try again.")
            
        return HttpResponseRedirect(reverse("catalog:product_list"))



class CategoryCreateAjaxView(TenantPermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = "catalog.manage"
    model = Category
    form_class = CategoryForm

    def form_valid(self, form):
        form.instance.slug = slugify(form.cleaned_data['name'])
        try:
            category = form.save()
        except Exception:
            logger.exception("Unexpected error saving category")
            form.add_error(None, "Could not create category. Please try again.")
            return self.form_invalid(form)

        from django.template.loader import render_to_string

        categories = Category.objects.filter(is_active=True).order_by("name")
        options = ['<option value="">---------</option>']
        for cat in categories:
            selected = " selected" if cat.id == category.id else ""
            options.append(
                f'<option value="{escape(str(cat.id))}"{selected}>{escape(cat.name)}</option>'
            )
        options_html = "".join(options)

        select_oob_html = (
            '<select name="category" id="id_category" '
            'class="w-full h-11 pl-4 pr-10 bg-white border border-neutral-300 rounded-xl '
            'text-sm focus:ring-2 focus:ring-neutral-900/10 focus:border-neutral-900 '
            'transition-all dark:bg-neutral-dark-100 dark:border-neutral-dark-300 '
            'dark:text-white appearance-none cursor-pointer" hx-swap-oob="true">'
            f"{options_html}"
            "</select>"
        )

        toast_html = render_to_string(
            "catalog/partials/category_created_toast.html",
            {"category": category},
            request=self.request,
        )

        in_band_html = render_to_string(
            "catalog/partials/category_form_inner.html",
            {"category_form": CategoryForm()},
            request=self.request,
        )

        response = HttpResponse(in_band_html + select_oob_html + toast_html)
        response["HX-Trigger"] = "close-category-modal"
        return response

    def form_invalid(self, form):
        # 200 (not 422) so HTMX swaps the partial with field errors back into
        # the modal. HTMX only swaps 2xx responses by default.
        return render(
            self.request,
            "catalog/partials/category_form_inner.html",
            {"category_form": form},
        )


from django.db.models import Sum, Count, F
from contexts.catalog.models.modifier import ModifierGroup, Modifier
from contexts.catalog.forms import ModifierGroupForm, ModifierForm


class ModifierGroupListView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "catalog.view"
    model = ModifierGroup
    template_name = "catalog/modifier_group_list.html"
    context_object_name = "modifier_groups"

    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(is_deleted=False)
            .prefetch_related("modifiers")
            .order_by("sort_order", "name")
        )


class ModifierGroupCreateView(TenantPermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = "catalog.manage"
    model = ModifierGroup
    form_class = ModifierGroupForm
    template_name = "catalog/modifier_group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Modifier Group "{group.name}" created successfully.')
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierGroupUpdateView(TenantPermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = "catalog.manage"
    model = ModifierGroup
    form_class = ModifierGroupForm
    template_name = "catalog/modifier_group_form.html"

    def form_valid(self, form):
        group = form.save()
        messages.success(self.request, f'Modifier Group "{group.name}" updated successfully.')
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierGroupDeleteView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "catalog.manage"

    def post(self, request, pk, *args, **kwargs):
        group = ModifierGroup.objects.filter(pk=pk).first()
        if group:
            group.is_deleted = True
            group.save(update_fields=["is_deleted", "updated_at"])
            messages.success(request, f'Modifier Group "{group.name}" deleted.')
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierOptionManageView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "catalog.view"
    model = Modifier
    template_name = "catalog/modifier_options_manage.html"
    context_object_name = "modifiers"

    def get_queryset(self):
        qs = super().get_queryset().filter(group_id=self.kwargs["group_pk"], is_deleted=False)
        query = self.request.GET.get("q", "").strip()
        status = self.request.GET.get("status", "")
        if query:
            qs = qs.filter(name__icontains=query) | qs.filter(sku__icontains=query)
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        return qs.order_by("sort_order", "name")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        group = get_object_or_404(ModifierGroup, pk=self.kwargs["group_pk"], is_deleted=False)
        ctx["group"] = group
        ctx["search_query"] = self.request.GET.get("q", "")
        ctx["status_filter"] = self.request.GET.get("status", "")
        return ctx


class ModifierCreateView(TenantPermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = "catalog.manage"
    model = Modifier
    form_class = ModifierForm
    template_name = "catalog/modifier_option_form.html"

    def form_valid(self, form):
        from django.shortcuts import get_object_or_404
        group = get_object_or_404(ModifierGroup, pk=self.kwargs["group_pk"], is_deleted=False)
        mod = form.save(commit=False)
        mod.group = group
        mod.save()
        messages.success(self.request, f'Option "{mod.name}" added to "{group.name}".')
        return HttpResponseRedirect(reverse("catalog:modifier_option_manage", kwargs={"group_pk": group.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from django.shortcuts import get_object_or_404
        ctx["group"] = get_object_or_404(ModifierGroup, pk=self.kwargs["group_pk"], is_deleted=False)
        return ctx


class ModifierUpdateView(TenantPermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = "catalog.manage"
    model = Modifier
    form_class = ModifierForm
    template_name = "catalog/modifier_option_form.html"

    def form_valid(self, form):
        mod = form.save()
        messages.success(self.request, f'Option "{mod.name}" updated successfully.')
        return HttpResponseRedirect(reverse("catalog:modifier_option_manage", kwargs={"group_pk": mod.group_id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["group"] = self.object.group
        return ctx


class ModifierDeleteView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "catalog.manage"

    def post(self, request, pk, *args, **kwargs):
        mod = Modifier.objects.filter(pk=pk).first()
        if mod:
            group_id = mod.group_id
            mod.is_deleted = True
            mod.save(update_fields=["is_deleted", "updated_at"])
            messages.success(request, f'Option "{mod.name}" deleted.')
            return HttpResponseRedirect(reverse("catalog:modifier_option_manage", kwargs={"group_pk": group_id}))
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierCloneView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "catalog.manage"

    def post(self, request, pk, *args, **kwargs):
        mod = Modifier.objects.filter(pk=pk).first()
        if mod:
            clone = Modifier.objects.create(
                group=mod.group,
                name=f"{mod.name} (Copy)",
                description=mod.description,
                sku=f"{mod.sku}-CPY" if mod.sku else "",
                price_delta=mod.price_delta,
                price_type=mod.price_type,
                inventory_item=mod.inventory_item,
                quantity_consumed=mod.quantity_consumed,
                is_default=False,
                is_active=mod.is_active,
                sort_order=mod.sort_order + 1,
                color_code=mod.color_code,
                is_taxable=mod.is_taxable,
            )
            messages.success(request, f'Cloned option "{clone.name}" successfully.')
            return HttpResponseRedirect(reverse("catalog:modifier_option_manage", kwargs={"group_pk": mod.group_id}))
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierToggleStatusView(TenantPermissionRequiredMixin, LoginRequiredMixin, View):
    permission_required = "catalog.manage"

    def post(self, request, pk, *args, **kwargs):
        mod = Modifier.objects.filter(pk=pk).first()
        if mod:
            mod.is_active = not mod.is_active
            mod.save(update_fields=["is_active", "updated_at"])
            state_label = "Active" if mod.is_active else "Inactive"
            messages.success(request, f'Option "{mod.name}" marked as {state_label}.')
            return HttpResponseRedirect(reverse("catalog:modifier_option_manage", kwargs={"group_pk": mod.group_id}))
        return HttpResponseRedirect(reverse("catalog:modifier_group_list"))


class ModifierAnalyticsView(TenantPermissionRequiredMixin, LoginRequiredMixin, TemplateView):
    permission_required = "catalog.view"
    template_name = "catalog/modifier_analytics.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from contexts.ordering.models.order import OrderItemModifier, OrderItem

        top_modifiers = (
            OrderItemModifier.objects.values("name_snapshot")
            .annotate(
                total_qty=Sum("qty"),
                total_revenue=Sum(F("price_delta") * F("qty")),
            )
            .order_by("-total_qty")[:15]
        )

        total_mod_rev = (
            OrderItemModifier.objects.aggregate(
                rev=Sum(F("price_delta") * F("qty"))
            )["rev"]
            or 0
        )
        total_items = OrderItem.objects.count()
        items_with_mods = (
            OrderItem.objects.filter(modifiers__isnull=False).distinct().count()
        )
        attach_rate = (
            round((items_with_mods / total_items) * 100, 1) if total_items > 0 else 0
        )

        context.update(
            {
                "top_modifiers": top_modifiers,
                "total_modifier_revenue": total_mod_rev,
                "attach_rate": attach_rate,
                "total_items": total_items,
            }
        )
        return context


class ComboOfferListView(TenantPermissionRequiredMixin, LoginRequiredMixin, ListView):
    permission_required = "catalog.view"
    template_name = "catalog/combo_list.html"
    context_object_name = "combos"
    
    def get_queryset(self):
        from contexts.catalog.models import ComboOffer
        return ComboOffer.objects.filter(is_deleted=False).order_by("sort_order", "name")


class ComboOfferCreateView(TenantPermissionRequiredMixin, LoginRequiredMixin, CreateView):
    permission_required = "catalog.manage"
    template_name = "catalog/combo_form.html"
    
    def get_form_class(self):
        from contexts.catalog.forms import ComboOfferForm
        return ComboOfferForm
    
    def get_success_url(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id:
            return reverse("catalog:combo_list_tenant", kwargs={"tenant_id": tenant_id})
        return reverse("catalog:combo_list")
        
    def get_queryset(self):
        from contexts.catalog.models import ComboOffer
        return ComboOffer.objects.filter(is_deleted=False)

class ComboOfferUpdateView(TenantPermissionRequiredMixin, LoginRequiredMixin, UpdateView):
    permission_required = "catalog.manage"
    template_name = "catalog/combo_form.html"
    
    def get_form_class(self):
        from contexts.catalog.forms import ComboOfferForm
        return ComboOfferForm
    
    def get_success_url(self):
        tenant_id = getattr(self.request, 'tenant_id', None)
        if tenant_id:
            return reverse("catalog:combo_list_tenant", kwargs={"tenant_id": tenant_id})
        return reverse("catalog:combo_list")
        
    def get_queryset(self):
        from contexts.catalog.models import ComboOffer
        return ComboOffer.objects.filter(is_deleted=False)
