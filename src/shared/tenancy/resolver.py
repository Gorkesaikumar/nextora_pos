"""Tenant resolution from the request host (Redis-cached).

Resolution order:
  1. Custom domain (white-label)  -> tenant_domain.domain
  2. Subdomain slug               -> "<slug>.<TENANCY_BASE_DOMAIN>"

The host->tenant mapping is cached because it is read on EVERY request. Cache
is invalidated when domains/tenants change (event-driven, handled elsewhere).

Returns the tenant UUID and its status, or None when the host is unknown.
"""
import uuid
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

_CACHE_TTL = 300  # seconds
_CACHE_PREFIX = "tenancy:host:"


@dataclass(frozen=True)
class ResolvedTenant:
    tenant_id: uuid.UUID
    status: str


def resolve_from_host(host: str) -> ResolvedTenant | None:
    host = host.split(":")[0].lower().strip()  # drop port
    if not host:
        return None

    cache_key = f"{_CACHE_PREFIX}{host}"
    cached = cache.get(cache_key)
    if cached is not None:
        # Sentinel "0" caches a known-miss to avoid hammering the DB.
        if cached == "0":
            return None
        tid, status = cached.split("|", 1)
        return ResolvedTenant(uuid.UUID(tid), status)

    resolved = _lookup(host)
    cache.set(
        cache_key,
        "0" if resolved is None else f"{resolved.tenant_id}|{resolved.status}",
        _CACHE_TTL,
    )
    return resolved


def _lookup(host: str) -> ResolvedTenant | None:
    # Imported lazily to avoid an import cycle at app-load time.
    from contexts.tenants.models import Tenant, TenantDomain
    from shared.tenancy.context import bypass_tenant

    base_domain = settings.TENANCY_BASE_DOMAIN

    with bypass_tenant():  # resolution itself is a cross-tenant lookup
        # 1) Custom domain.
        domain = (
            TenantDomain.objects.filter(domain=host, is_verified=True)
            .select_related("tenant")
            .first()
        )
        if domain is not None:
            return ResolvedTenant(domain.tenant_id, domain.tenant.status)

        # 2) Subdomain slug.
        if base_domain and host.endswith(f".{base_domain}"):
            slug = host[: -len(base_domain) - 1]
            tenant = Tenant.objects.filter(slug=slug).first()
            if tenant is not None:
                return ResolvedTenant(tenant.id, tenant.status)

    return None
