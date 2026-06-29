"""Tenancy error hierarchy."""


class TenancyError(Exception):
    """Base class for all tenancy violations."""


class TenantNotResolved(TenancyError):
    """No tenant in context where one is required (likely a missing scope)."""


class CrossTenantAccess(TenancyError):
    """An attempt to write/read a row belonging to a different tenant.

    This is a security event — it should be logged and alerted on, not
    swallowed.
    """


class TenantInactive(TenancyError):
    """The resolved tenant exists but is suspended / churned."""
