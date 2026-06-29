import logging
from uuid import UUID

from django.contrib.postgres.search import TrigramSimilarity
from django.db import connection
from django.db.models import Q

from contexts.catalog.models import Category, Product
from contexts.identity.models import Membership
from contexts.ordering.models import Invoice
from contexts.tenants.models import Tenant
from contexts.customers.models import Customer
from contexts.inventory.models.supplier import Supplier
from .providers import BaseSearchProvider, SearchRegistry

logger = logging.getLogger(__name__)


def _is_trigram_enabled() -> bool:
    if connection.vendor != "postgresql":
        return False
    if not hasattr(connection, "_has_trigram"):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm';")
                connection._has_trigram = bool(cursor.fetchone())
        except Exception:
            connection._has_trigram = False
    return connection._has_trigram


def _apply_fuzzy_search(queryset, query, fields, fallback_field):
    """Utility to perform Postgres Trigram search with standard Q fallback."""
    if _is_trigram_enabled():
        # Trigram search for PostgreSQL
        similarity = None
        for field in fields:
            field_similarity = TrigramSimilarity(field, query)
            if similarity is None:
                similarity = field_similarity
            else:
                similarity += field_similarity

        return (
            queryset.annotate(similarity=similarity)
            .filter(similarity__gt=0.1)
            .order_by("-similarity")
        )
    else:
        # Fallback for SQLite / unit testing / missing pg_trgm
        q_filter = Q()
        for field in fields:
            q_filter |= Q(**{f"{field}__icontains": query})
        return queryset.filter(q_filter)


class ProductSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        qs = Product.objects.filter(tenant_id=tenant_id, is_deleted=False)
        qs = _apply_fuzzy_search(qs, query, ["name", "sku", "description"], "name")
        
        results = []
        for p in qs[offset : offset + limit]:
            rank = getattr(p, "similarity", 0.5)
            results.append({
                "id": str(p.id),
                "type": "product",
                "title": p.name,
                "subtitle": f"SKU: {p.sku or 'N/A'}",
                "rank": float(rank),
                "url": f"/api/v1/catalog/products/{p.id}/"
            })
        return results


class CategorySearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        qs = Category.objects.filter(tenant_id=tenant_id, is_deleted=False)
        qs = _apply_fuzzy_search(qs, query, ["name"], "name")
        
        results = []
        for c in qs[offset : offset + limit]:
            rank = getattr(c, "similarity", 0.5)
            results.append({
                "id": str(c.id),
                "type": "category",
                "title": c.name,
                "subtitle": "Product Category",
                "rank": float(rank),
                "url": f"/api/v1/catalog/categories/{c.id}/"
            })
        return results


class InvoiceSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        qs = Invoice.objects.filter(tenant_id=tenant_id)
        qs = _apply_fuzzy_search(qs, query, ["number"], "number")
        
        results = []
        for inv in qs[offset : offset + limit]:
            rank = getattr(inv, "similarity", 0.5)
            results.append({
                "id": str(inv.id),
                "type": "invoice",
                "title": inv.number,
                "subtitle": f"Invoice | Date: {inv.created_at:%Y-%m-%d}",
                "rank": float(rank),
                "url": f"/api/v1/ordering/invoices/{inv.id}/"
            })
        return results


class EmployeeSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        # Filter memberships for active tenant and grab users
        qs = Membership.objects.filter(tenant_id=tenant_id, is_active=True)
        # Search against user full name and email
        qs = _apply_fuzzy_search(qs, query, ["user__full_name", "user__email"], "user__full_name")
        
        results = []
        for m in qs[offset : offset + limit]:
            rank = getattr(m, "similarity", 0.5)
            results.append({
                "id": str(m.user.id),
                "type": "employee",
                "title": m.user.full_name or m.user.email,
                "subtitle": f"Role: {m.role.name}",
                "rank": float(rank),
                "url": f"/api/v1/identity/users/{m.user.id}/"
            })
        return results


class RestaurantSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        # Platform/global tenant search
        qs = Tenant.objects.all()
        qs = _apply_fuzzy_search(qs, query, ["name", "slug"], "name")
        
        results = []
        for t in qs[offset : offset + limit]:
            rank = getattr(t, "similarity", 0.5)
            results.append({
                "id": str(t.id),
                "type": "restaurant",
                "title": t.name,
                "subtitle": f"Slug: {t.slug}",
                "rank": float(rank),
                "url": f"/api/v1/tenants/{t.id}/"
            })
        return results


class CustomerSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        qs = Customer.objects.filter(tenant_id=tenant_id, is_deleted=False)
        qs = _apply_fuzzy_search(qs, query, ["name", "phone", "email"], "name")
        
        results = []
        for c in qs[offset : offset + limit]:
            rank = getattr(c, "similarity", 0.5)
            results.append({
                "id": str(c.id),
                "type": "customer",
                "title": c.name,
                "subtitle": f"Phone: {c.phone} | Tier: {c.loyalty_tier.title()}",
                "rank": float(rank),
                "url": f"/api/v1/customers/{c.id}/"
            })
        return results


class SupplierSearchProvider(BaseSearchProvider):

    def search(self, query: str, tenant_id: UUID, limit: int, offset: int) -> list[dict]:
        qs = Supplier.objects.filter(tenant_id=tenant_id, is_deleted=False)
        qs = _apply_fuzzy_search(qs, query, ["name", "code", "phone", "email"], "name")
        
        results = []
        for s in qs[offset : offset + limit]:
            rank = getattr(s, "similarity", 0.5)
            results.append({
                "id": str(s.id),
                "type": "supplier",
                "title": s.name,
                "subtitle": f"Code: {s.code or 'N/A'}",
                "rank": float(rank),
                "url": f"/api/v1/inventory/suppliers/{s.id}/"
            })
        return results


# Register all implementations in the search registry
SearchRegistry.register("products", ProductSearchProvider())
SearchRegistry.register("categories", CategorySearchProvider())
SearchRegistry.register("invoices", InvoiceSearchProvider())
SearchRegistry.register("employees", EmployeeSearchProvider())
SearchRegistry.register("restaurants", RestaurantSearchProvider())
SearchRegistry.register("customers", CustomerSearchProvider())
SearchRegistry.register("suppliers", SupplierSearchProvider())
