"""DB-driven authorization tests.

These prove the decision is computed from database rows (Membership + grants),
honours branch/company/platform scope, blocks cross-tenant access, and reacts
to live grant changes — i.e. nothing is hardcoded.
"""
import uuid

import pytest

from contexts.identity.models import Membership, Permission, Role, RolePermission
from contexts.identity.permissions import PERMISSIONS, all_codes
from contexts.identity.services.authorization import (
    get_permission_codes,
    has_permission,
)

pytestmark = pytest.mark.django_db


# --- Seeding ---------------------------------------------------------------
def test_seed_creates_catalog_and_roles(seeded):
    assert Permission.objects.count() == len(PERMISSIONS)
    assert Role.objects.filter(tenant__isnull=True, is_system=True).count() == 9
    super_admin = Role.objects.get(code="super_admin", tenant__isnull=True)
    assert set(super_admin.permissions.values_list("code", flat=True)) == all_codes()


# --- Company scope ---------------------------------------------------------
def test_company_owner_has_tenant_permissions(tenant, make_user, system_role):
    user = make_user()
    Membership.objects.create(user=user, tenant=tenant, role=system_role("company_owner"))

    assert has_permission(user, "orders.void", tenant.id)
    assert has_permission(user, "billing.manage", tenant.id)
    # Company owner must NOT hold platform permissions.
    assert not has_permission(user, "platform.tenants.manage", tenant.id)


def test_company_scope_applies_to_any_branch(tenant, make_user, system_role):
    user = make_user()
    Membership.objects.create(user=user, tenant=tenant, role=system_role("accountant"))
    some_branch = uuid.uuid4()
    # location_id is NULL on the membership -> applies to every branch.
    assert has_permission(user, "reports.financial.view", tenant.id, some_branch)


# --- Branch scope ----------------------------------------------------------
def test_branch_manager_scoped_to_their_branch(tenant, make_user, system_role):
    user = make_user()
    branch_a = uuid.uuid4()
    branch_b = uuid.uuid4()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("branch_manager"),
        location_id=branch_a,
    )

    assert has_permission(user, "orders.void", tenant.id, branch_a)      # in branch
    assert not has_permission(user, "orders.void", tenant.id, branch_b)  # other branch
    assert not has_permission(user, "orders.void", tenant.id, None)      # unscoped req


def test_cashier_cannot_void_orders(tenant, make_user, system_role):
    user = make_user()
    branch = uuid.uuid4()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("cashier"), location_id=branch
    )

    assert has_permission(user, "payments.capture", tenant.id, branch)
    assert not has_permission(user, "orders.void", tenant.id, branch)


# --- Cross-tenant protection ----------------------------------------------
def test_membership_does_not_leak_across_tenants(
    tenant, other_tenant, make_user, system_role
):
    user = make_user()
    Membership.objects.create(user=user, tenant=tenant, role=system_role("company_owner"))

    assert has_permission(user, "orders.void", tenant.id)
    assert not has_permission(user, "orders.void", other_tenant.id)


# --- Platform scope --------------------------------------------------------
def test_super_admin_platform_membership_spans_all_tenants(
    tenant, other_tenant, make_user, system_role
):
    user = make_user()
    # Platform membership: tenant = None.
    Membership.objects.create(user=user, tenant=None, role=system_role("super_admin"))

    assert has_permission(user, "platform.tenants.manage", tenant.id)
    assert has_permission(user, "orders.void", tenant.id)
    assert has_permission(user, "orders.void", other_tenant.id)


# --- Live, database-driven changes ----------------------------------------
def test_grant_changes_take_effect_without_code_change(
    tenant, make_user, system_role
):
    user = make_user()
    cashier = system_role("cashier")
    branch = uuid.uuid4()
    Membership.objects.create(
        user=user, tenant=tenant, role=cashier, location_id=branch
    )
    assert not has_permission(user, "orders.void", tenant.id, branch)

    # Grant the capability in the DB (sends signal -> cache invalidated).
    void_perm = Permission.objects.get(code="orders.void")
    RolePermission.objects.create(role=cashier, permission=void_perm)
    assert has_permission(user, "orders.void", tenant.id, branch)

    # Revoke it again.
    RolePermission.objects.filter(role=cashier, permission=void_perm).delete()
    assert not has_permission(user, "orders.void", tenant.id, branch)


def test_inactive_membership_is_ignored(tenant, make_user, system_role):
    user = make_user()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("company_owner"), is_active=False
    )
    assert not has_permission(user, "orders.void", tenant.id)


def test_get_permission_codes_returns_union(tenant, make_user, system_role):
    user = make_user()
    Membership.objects.create(user=user, tenant=tenant, role=system_role("waiter"))
    codes = get_permission_codes(user, tenant.id)
    assert "orders.create" in codes
    assert "payments.refund" not in codes


# --- Provisioning ----------------------------------------------------------
def test_provision_clones_non_platform_roles(tenant, seeded):
    from contexts.identity.services.provisioning import provision_tenant_roles

    created = provision_tenant_roles(tenant.id)
    # 7 non-platform roles (9 minus super_admin + support).
    assert len(created) == 7
    assert "super_admin" not in created
    cashier = Role.objects.get(tenant=tenant, code="cashier")
    assert cashier.permissions.filter(code="payments.capture").exists()
