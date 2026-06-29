"""Declarative permission catalog and default role blueprints.

IMPORTANT: this module is DATA, not authorization logic.
  * PERMISSIONS    — the catalog of capability codes, synced into the DB by
                     `manage.py sync_permissions`. Each context owns its codes.
  * ROLE_BLUEPRINTS— the DEFAULT permission set for each seeded system role,
                     applied by `manage.py seed_roles`. After seeding, admins
                     edit grants in the DB; the runtime never reads this file.

The token "*" in a blueprint means "every permission in the catalog" (used by
Super Admin). "*tenant" means every non-platform permission (Company Owner).
"""
from dataclasses import dataclass

from contexts.identity.models import Role


@dataclass(frozen=True)
class PermissionDef:
    code: str
    name: str
    module: str


# --- Permission catalog ----------------------------------------------------
# Grouped by module for readability; flattened on sync.
PERMISSIONS: tuple[PermissionDef, ...] = (
    # Ordering
    PermissionDef("orders.view", "View orders", "ordering"),
    PermissionDef("orders.create", "Create orders", "ordering"),
    PermissionDef("orders.update", "Update orders", "ordering"),
    PermissionDef("orders.void", "Void orders", "ordering"),
    PermissionDef("orders.discount", "Apply discounts", "ordering"),
    # Kitchen display
    PermissionDef("kds.view", "View kitchen display", "kitchen"),
    PermissionDef("kds.update_status", "Update preparation status", "kitchen"),
    # Payments
    PermissionDef("payments.view", "View payments", "payments"),
    PermissionDef("payments.capture", "Capture payments", "payments"),
    PermissionDef("payments.refund", "Refund payments", "payments"),
    # Invoicing
    PermissionDef("invoices.view", "View invoices", "invoicing"),
    PermissionDef("invoices.issue", "Issue invoices", "invoicing"),
    PermissionDef("invoices.void", "Void invoices", "invoicing"),
    # Catalog
    PermissionDef("catalog.view", "View catalog", "catalog"),
    PermissionDef("catalog.manage", "Manage catalog", "catalog"),
    # Inventory
    PermissionDef("inventory.view", "View inventory", "inventory"),
    PermissionDef("inventory.adjust", "Adjust stock", "inventory"),
    PermissionDef("inventory.manage", "Manage inventory", "inventory"),
    PermissionDef("purchase_orders.manage", "Manage purchase orders", "inventory"),
    # Reporting
    PermissionDef("reports.sales.view", "View sales reports", "reporting"),
    PermissionDef("reports.financial.view", "View financial reports", "reporting"),
    PermissionDef("reports.inventory.view", "View inventory reports", "reporting"),
    # Access / org admin
    PermissionDef("users.view", "View users", "identity"),
    PermissionDef("users.manage", "Manage users", "identity"),
    PermissionDef("roles.manage", "Manage roles & permissions", "identity"),
    PermissionDef("branches.view", "View branches", "tenants"),
    PermissionDef("branches.manage", "Manage branches", "tenants"),
    PermissionDef("billing.view", "View billing", "billing"),
    PermissionDef("billing.manage", "Manage billing", "billing"),
    # Platform (Super Admin / Support only)
    PermissionDef("platform.tenants.manage", "Manage tenants", "platform"),
    PermissionDef("platform.impersonate", "Impersonate tenant users", "platform"),
    PermissionDef("platform.support.view", "View support console", "platform"),
)

PLATFORM_MODULES = {"platform"}


def all_codes() -> set[str]:
    return {p.code for p in PERMISSIONS}


def tenant_codes() -> set[str]:
    """Every permission that is NOT platform-only."""
    return {p.code for p in PERMISSIONS if p.module not in PLATFORM_MODULES}


@dataclass(frozen=True)
class RoleBlueprint:
    code: str
    name: str
    scope: str
    permissions: tuple[str, ...]  # codes, or ("*",) / ("*tenant",)


# --- The nine enterprise roles --------------------------------------------
ROLE_BLUEPRINTS: tuple[RoleBlueprint, ...] = (
    RoleBlueprint(
        "super_admin", "Super Admin", Role.Scope.PLATFORM, ("*",)
    ),
    RoleBlueprint(
        "support", "Support", Role.Scope.PLATFORM,
        (
            "platform.support.view", "orders.view", "invoices.view",
            "payments.view", "users.view", "billing.view",
            "reports.sales.view", "reports.financial.view",
        ),
    ),
    RoleBlueprint(
        "company_owner", "Company Owner", Role.Scope.COMPANY, ("*tenant",)
    ),
    RoleBlueprint(
        "branch_manager", "Branch Manager", Role.Scope.BRANCH,
        (
            "orders.view", "orders.create", "orders.update", "orders.void",
            "orders.discount", "kds.view", "payments.view", "payments.capture",
            "payments.refund", "invoices.view", "invoices.issue",
            "catalog.view", "inventory.view", "inventory.adjust",
            "reports.sales.view", "users.view", "branches.view",
        ),
    ),
    RoleBlueprint(
        "cashier", "Cashier", Role.Scope.BRANCH,
        (
            "orders.view", "orders.create", "orders.update",
            "payments.view", "payments.capture",
            "invoices.view", "invoices.issue", "catalog.view",
        ),
    ),
    RoleBlueprint(
        "kitchen_staff", "Kitchen Staff", Role.Scope.BRANCH,
        ("kds.view", "kds.update_status", "orders.view"),
    ),
    RoleBlueprint(
        "waiter", "Waiter", Role.Scope.BRANCH,
        (
            "orders.view", "orders.create", "orders.update",
            "catalog.view", "payments.view",
        ),
    ),
    RoleBlueprint(
        "inventory_manager", "Inventory Manager", Role.Scope.COMPANY,
        (
            "inventory.view", "inventory.adjust", "inventory.manage",
            "purchase_orders.manage", "catalog.view", "catalog.manage",
            "reports.inventory.view",
        ),
    ),
    RoleBlueprint(
        "accountant", "Accountant", Role.Scope.COMPANY,
        (
            "invoices.view", "payments.view", "billing.view",
            "reports.financial.view", "reports.sales.view",
        ),
    ),
)


def resolve_blueprint_codes(blueprint: RoleBlueprint) -> set[str]:
    """Expand the wildcard tokens to concrete permission codes."""
    if blueprint.permissions == ("*",):
        return all_codes()
    if blueprint.permissions == ("*tenant",):
        return tenant_codes()
    return set(blueprint.permissions)
