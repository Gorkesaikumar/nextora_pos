"""Onboarding workspace provisioning — one atomic transaction creates everything
needed to land the new owner on the dashboard:

    User                   (identity)
    Tenant + Domain        (tenants)
    TenantConfiguration    (tenants)
    Branch                 (tenants)
    Subscription           (billing) — uses existing subscription_service
    Membership             (identity.rbac) — binds user to company_owner role

If any step fails the whole transaction rolls back; partial workspaces are not
acceptable for billing or RLS reasons.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.utils.text import slugify

from contexts.billing.services import subscription_service
from contexts.identity.models.rbac import Membership, Role
from contexts.tenants.models import Tenant, TenantConfiguration
from shared.tenancy import tenant_scope

User = get_user_model()


COMPANY_OWNER_ROLE_CODE = "company_owner"


class ProvisioningError(Exception):
    """Raised when the workspace can't be provisioned for a non-validation reason
    (e.g. seed roles missing, plan code unknown). The caller should map this to
    a non_field error on the wizard form.
    """


@dataclass(frozen=True)
class ProvisionedWorkspace:
    user: Any
    tenant: Tenant


def _unique_tenant_slug(base: str) -> str:
    """Derive a globally-unique tenant slug from the restaurant name. Tries the
    plain slug first, then appends an incrementing suffix on collision. Slug is
    limited to 63 chars (DB constraint).
    """
    base = slugify(base)[:55] or "workspace"
    candidate = base
    n = 1
    while Tenant.objects.filter(slug=candidate).exists():
        suffix = f"-{n}"
        candidate = f"{base[:63 - len(suffix)]}{suffix}"
        n += 1
        if n > 1000:  # pathological — refuse to loop forever
            raise ProvisioningError("Could not derive a unique workspace slug.")
    return candidate


def provision_workspace(
    *,
    account: dict,
    restaurant: dict,
    plan: dict,
    branch: dict,
) -> ProvisionedWorkspace:
    """Atomically create the workspace from validated wizard data.

    Parameters mirror the four wizard step dicts:

      account    — {first_name, last_name, email, phone, password}
      restaurant — {restaurant_name, business_type, country, state, city, postal_code}
      plan       — {plan_code, interval}
      branch     — {branch_name, branch_code, currency, timezone, gstin}

    Returns ``ProvisionedWorkspace`` with the freshly-created entities.
    """
    # Resolve the system company_owner role before opening the transaction so a
    # missing seed surfaces as a clean ProvisioningError rather than IntegrityError.
    try:
        owner_role = Role.objects.get(
            code=COMPANY_OWNER_ROLE_CODE, tenant__isnull=True
        )
    except Role.DoesNotExist as exc:
        raise ProvisioningError(
            "System role 'company_owner' is not seeded — run identity migrations."
        ) from exc

    with transaction.atomic():
        # 1. User -----------------------------------------------------------
        try:
            user = User.objects.create_user(
                email=account["email"],
                password=account["password"],
                full_name=f"{account['first_name']} {account['last_name']}".strip(),
            )
        except IntegrityError as exc:
            # Race with another concurrent signup using the same email.
            raise ProvisioningError("This email is already registered.") from exc

        # 2. Tenant + domain ------------------------------------------------
        tenant = Tenant.objects.create(
            slug=_unique_tenant_slug(restaurant["restaurant_name"]),
            name=restaurant["restaurant_name"],
            legal_name=restaurant["restaurant_name"],
            status=Tenant.Status.TRIAL,
            country=restaurant["country"],
            base_currency=branch["currency"],
            timezone=branch["timezone"],
        )

        # 3. Tenant scope active for everything tenant-aware ---------------
        # TenantConfiguration is auto-created by a post_save signal on Tenant —
        # we update it rather than insert a second row (UNIQUE constraint).
        with tenant_scope(tenant.id):
            TenantConfiguration.objects.filter(tenant=tenant).update(
                gst_number=branch.get("gstin") or "",
                currency=branch["currency"],
                timezone=branch["timezone"],
            )

            # 4. Subscription via the existing billing service ------------
            subscription_service.create_subscription(
                tenant_id=tenant.id,
                plan_code=plan["plan_code"],
                interval=plan["interval"],
                coupon_code=plan.get("coupon_code"),
            )
            
            # Seed default Tables for the new tenant
            from contexts.restaurant.models.layout import DiningTable
            DiningTable.objects.create(number="T1", capacity=2)
            DiningTable.objects.create(number="T2", capacity=4)
            DiningTable.objects.create(number="T3", capacity=4)
            DiningTable.objects.create(number="T4", capacity=6)

            # 5. Membership: user -> tenant (company-scope, no branch) ----
            Membership.objects.create(
                user=user,
                tenant=tenant,
                role=owner_role,
                is_active=True,
            )

        return ProvisionedWorkspace(user=user, tenant=tenant)


def _compose_address(restaurant: dict) -> str:
    parts = [
        restaurant.get("city"),
        restaurant.get("state"),
        restaurant.get("postal_code"),
        restaurant.get("country"),
    ]
    return ", ".join(p for p in parts if p)
