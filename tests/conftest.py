"""Shared pytest fixtures for the test suite.

Tests run inside the dockerised stack (`make test`) where Postgres is available.
The authorization cache is swapped to local-memory so tests are isolated and do
not require Redis.
"""
import pytest
from django.core.management import call_command


@pytest.fixture(autouse=True)
def _locmem_cache(settings):
    settings.CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "authz-tests",
        }
    }
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def seeded(db):
    """Seed the permission catalog and the nine system roles."""
    call_command("seed_roles")


@pytest.fixture
def tenant(db):
    from contexts.tenants.models import Tenant

    return Tenant.objects.create(slug="acme", name="Acme", base_currency="USD")


@pytest.fixture
def other_tenant(db):
    from contexts.tenants.models import Tenant

    return Tenant.objects.create(slug="globex", name="Globex", base_currency="USD")


@pytest.fixture
def make_user(db):
    from django.contrib.auth import get_user_model

    user_model = get_user_model()
    counter = {"n": 0}

    def _make(email: str | None = None):
        counter["n"] += 1
        return user_model.objects.create_user(
            email=email or f"user{counter['n']}@example.com",
            password="testpass123",
        )

    return _make


@pytest.fixture
def active_tenant(tenant):
    """Bind the tenant in context so tenant-scoped managers/saves work."""
    from shared.tenancy import set_current_tenant
    from shared.tenancy.context import clear_current_tenant

    set_current_tenant(tenant.id)
    yield tenant
    clear_current_tenant()


@pytest.fixture
def system_role(seeded):
    from contexts.identity.models import Role

    def _get(code: str) -> Role:
        return Role.objects.get(code=code, tenant__isnull=True)

    return _get
