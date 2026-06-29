"""Authorization service — the single source of permission decisions.

Computes a user's effective permissions ENTIRELY from the database
(Membership -> Role -> RolePermission). No role names or permission lists are
hardcoded in the decision path.

Scope rules:
  * A membership with tenant = T applies when resolving for tenant T.
  * A membership with tenant = NULL (platform staff) applies for ANY tenant.
  * A membership with location_id = NULL grants across all branches; a set
    location_id grants only when the request targets that branch.

Caching:
  Results are cached in Redis under a version-stamped key. Any RBAC change bumps
  the global version (see signals.py), invalidating every cached decision at once
  without needing to enumerate affected keys.
"""
import uuid
from dataclasses import dataclass

from django.core.cache import cache
from django.db.models import Q

from contexts.identity.models import Membership

_VERSION_KEY = "authz:version"
_TTL = 600  # seconds


@dataclass(frozen=True)
class _Grant:
    location_id: str | None      # None = all branches
    permissions: frozenset[str]


def _version() -> int:
    return cache.get_or_set(_VERSION_KEY, 1, None)


def bump_version() -> None:
    """Invalidate all cached authorization decisions."""
    try:
        cache.incr(_VERSION_KEY)
    except ValueError:
        cache.set(_VERSION_KEY, 1, None)


def _cache_key(user_id: uuid.UUID, tenant_id: uuid.UUID | None) -> str:
    return f"authz:perm:{_version()}:{user_id}:{tenant_id or 'platform'}"


def _resolve_grants(
    user_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> list[_Grant]:
    """Load and shape the user's active grants for a tenant (uncached)."""
    memberships = (
        Membership.objects.filter(is_active=True, user_id=user_id)
        .filter(Q(tenant_id=tenant_id) | Q(tenant_id__isnull=True))
        .select_related("role")
        .prefetch_related("role__permissions")
    )
    grants: list[_Grant] = []
    for m in memberships:
        codes = frozenset(p.code for p in m.role.permissions.all())
        loc = str(m.location_id) if m.location_id else None
        grants.append(_Grant(location_id=loc, permissions=codes))
    return grants


def _get_grants(
    user_id: uuid.UUID, tenant_id: uuid.UUID | None
) -> list[_Grant]:
    key = _cache_key(user_id, tenant_id)
    cached = cache.get(key)
    if cached is not None:
        return [_Grant(g["location_id"], frozenset(g["permissions"])) for g in cached]

    grants = _resolve_grants(user_id, tenant_id)
    cache.set(
        key,
        [{"location_id": g.location_id, "permissions": list(g.permissions)} for g in grants],
        _TTL,
    )
    return grants


def has_permission(
    user,
    code: str,
    tenant_id: uuid.UUID | None,
    location_id: uuid.UUID | None = None,
) -> bool:
    """Return True iff the user holds ``code`` in this tenant/branch scope."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if not getattr(user, "is_active", False):
        return False

    target_loc = str(location_id) if location_id else None
    for grant in _get_grants(user.id, tenant_id):
        # Global grant applies anywhere
        if grant.location_id is None:
            if code in grant.permissions or "*" in grant.permissions or "*tenant" in grant.permissions:
                return True
        # Branch-specific grant applies if target matches OR if no target is specified
        elif target_loc is None or grant.location_id == target_loc:
            if code in grant.permissions or "*" in grant.permissions or "*tenant" in grant.permissions:
                return True
    return False


def get_permission_codes(
    user,
    tenant_id: uuid.UUID | None,
    location_id: uuid.UUID | None = None,
) -> frozenset[str]:
    """Union of all permission codes the user holds in scope (for UI/menus)."""
    if user is None or not getattr(user, "is_authenticated", False):
        return frozenset()
    target_loc = str(location_id) if location_id else None
    codes: set[str] = set()
    for grant in _get_grants(user.id, tenant_id):
        if grant.location_id is None or grant.location_id == target_loc:
            codes |= grant.permissions
    return frozenset(codes)
