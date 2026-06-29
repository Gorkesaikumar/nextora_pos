import logging

from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.utils.text import slugify
from django.views.generic import CreateView, ListView, UpdateView, View
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
