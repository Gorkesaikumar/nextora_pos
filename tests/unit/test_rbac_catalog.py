import os
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

"""Pure-data tests for the permission catalog (no database)."""
from contexts.identity.permissions import (
    PERMISSIONS,
    ROLE_BLUEPRINTS,
    all_codes,
    resolve_blueprint_codes,
    tenant_codes,
)
from contexts.identity.permissions.catalog import PLATFORM_MODULES


def test_permission_codes_are_unique():
    codes = [p.code for p in PERMISSIONS]
    assert len(codes) == len(set(codes))


def test_all_nine_roles_present():
    expected = {
        "super_admin", "support", "company_owner", "branch_manager",
        "cashier", "kitchen_staff", "waiter", "inventory_manager", "accountant",
    }
    assert {b.code for b in ROLE_BLUEPRINTS} == expected


def test_super_admin_gets_every_permission():
    sa = next(b for b in ROLE_BLUEPRINTS if b.code == "super_admin")
    assert resolve_blueprint_codes(sa) == all_codes()


def test_company_owner_gets_all_tenant_permissions_but_no_platform():
    owner = next(b for b in ROLE_BLUEPRINTS if b.code == "company_owner")
    codes = resolve_blueprint_codes(owner)
    assert codes == tenant_codes()
    assert not any(c.startswith("platform.") for c in codes)


def test_tenant_codes_exclude_platform_module():
    platform_codes = {p.code for p in PERMISSIONS if p.module in PLATFORM_MODULES}
    assert platform_codes.isdisjoint(tenant_codes())
    assert platform_codes  # sanity: there ARE platform permissions


def test_blueprint_codes_exist_in_catalog():
    catalog = all_codes()
    for bp in ROLE_BLUEPRINTS:
        for code in resolve_blueprint_codes(bp):
            assert code in catalog, f"{bp.code} references unknown {code}"
