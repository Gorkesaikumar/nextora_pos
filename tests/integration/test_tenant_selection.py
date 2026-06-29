"""Workspace (tenant) selection flow.

Regression cover for the lockout where the picker queried
``employees.EmployeeProfile`` instead of ``identity.Membership``, so legitimate
owners saw "No active workspaces found" and could not get past login.
"""
import pytest
from django.urls import reverse

from contexts.identity.models import Membership
from contexts.tenants.models import Tenant

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def allow_all_hosts(settings):
    settings.ALLOWED_HOSTS = ["*"]
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }


@pytest.fixture
def owner(tenant, make_user, system_role):
    user = make_user()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("company_owner"), is_active=True
    )
    return user


def test_single_membership_auto_selects_and_lands_on_dashboard(client, owner, tenant):
    """A user with exactly one workspace skips the picker and goes straight in.

    This is the exact lockout scenario from the bug report: the user is a member
    via Membership (not EmployeeProfile) and must NOT see "No active workspaces".
    """
    client.force_login(owner)
    response = client.get(reverse("tenants:select_tenant"), HTTP_HOST="127.0.0.1")

    assert response.status_code == 302
    assert response.url == reverse("reporting:home")
    assert client.session["active_tenant_id"] == str(tenant.id)


def test_multiple_memberships_render_picker(
    client, tenant, other_tenant, make_user, system_role
):
    user = make_user()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("company_owner"), is_active=True
    )
    Membership.objects.create(
        user=user, tenant=other_tenant, role=system_role("company_owner"),
        is_active=True,
    )

    client.force_login(user)
    response = client.get(reverse("tenants:select_tenant"), HTTP_HOST="127.0.0.1")

    assert response.status_code == 200
    content = response.content.decode()
    assert tenant.name in content
    assert other_tenant.name in content
    assert "No active workspaces found" not in content


def test_set_tenant_records_choice_and_redirects(client, owner, tenant):
    client.force_login(owner)
    response = client.get(
        reverse("tenants:set_tenant", kwargs={"slug": tenant.slug}),
        HTTP_HOST="127.0.0.1",
    )

    assert response.status_code == 302
    assert response.url == reverse("reporting:home")
    assert client.session["active_tenant_id"] == str(tenant.id)


def test_set_tenant_rejects_workspace_user_does_not_belong_to(
    client, owner, other_tenant
):
    """Picking a slug you have no membership for must NOT grant access."""
    client.force_login(owner)
    response = client.get(
        reverse("tenants:set_tenant", kwargs={"slug": other_tenant.slug}),
        HTTP_HOST="127.0.0.1",
    )

    assert response.status_code == 302
    assert response.url == reverse("tenants:select_tenant")
    assert "active_tenant_id" not in client.session


def test_suspended_tenant_is_hidden_from_picker(
    client, tenant, other_tenant, make_user, system_role
):
    """A suspended/churned workspace must not appear as selectable."""
    other_tenant.status = Tenant.Status.SUSPENDED
    other_tenant.save(update_fields=["status"])

    user = make_user()
    Membership.objects.create(
        user=user, tenant=tenant, role=system_role("company_owner"), is_active=True
    )
    Membership.objects.create(
        user=user, tenant=other_tenant, role=system_role("company_owner"),
        is_active=True,
    )

    client.force_login(user)
    # Only one *usable* workspace remains -> auto-select it.
    response = client.get(reverse("tenants:select_tenant"), HTTP_HOST="127.0.0.1")

    assert response.status_code == 302
    assert client.session["active_tenant_id"] == str(tenant.id)
