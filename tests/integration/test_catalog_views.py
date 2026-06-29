import pytest
from django.urls import reverse
from django.utils.text import slugify
from contexts.catalog.models import Category, Product
from contexts.audit.models import AuditLog
from contexts.catalog.forms import ProductForm, CategoryForm
from shared.tenancy import tenant_context

pytestmark = pytest.mark.django_db

@pytest.fixture(autouse=True)
def use_plain_staticfiles(settings):
    settings.ALLOWED_HOSTS = ['*']
    settings.STORAGES = {
        "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }

@pytest.fixture
def employee_user(tenant, make_user, system_role):
    from contexts.identity.models import Membership
    user = make_user()
    role = system_role("company_owner")
    Membership.objects.create(user=user, tenant=tenant, role=role, is_active=True)
    return user

def test_product_create_view_get(client, active_tenant, employee_user):
    client.force_login(employee_user)
    url = reverse("catalog:product_create")
    response = client.get(url, HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert response.status_code == 200
    assert "form" in response.context
    assert "category_form" in response.context
    assert isinstance(response.context["form"], ProductForm)
    assert isinstance(response.context["category_form"], CategoryForm)


def test_product_create_view_post_success(client, active_tenant, employee_user):
    client.force_login(employee_user)
    category = Category.objects.create(name="Beverages", slug="beverages")
    
    url = reverse("catalog:product_create")
    post_data = {
        "name": "Classic Lemonade",
        "sku": "LEM-001",
        "category": str(category.id),
        "type": "food",
        "base_price": "120.00",
        "currency": "INR",
        "description": "Fresh lemons and sugar",
        "is_active": True,
        "track_inventory": True,
    }
    
    response = client.post(url, post_data, HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    if response.status_code == 200:
        print("Form Errors:", response.context["form"].errors)
    assert response.status_code == 302
    assert response.url == reverse("catalog:product_list")
    
    with tenant_context(active_tenant.id):
        # Verify product is saved in database under active tenant
        product = Product.objects.get(sku="LEM-001")
        assert product.tenant_id == active_tenant.id
        assert product.name == "Classic Lemonade"
        assert product.base_price == 120.00
        
        # Verify audit log was recorded by the service layer
        assert AuditLog.all_objects.filter(
            action="product.created", entity_id=product.id
        ).exists()


def test_product_create_view_post_validation_error(client, active_tenant, employee_user):
    client.force_login(employee_user)
    url = reverse("catalog:product_create")
    # Missing required category
    post_data = {
        "name": "Classic Lemonade",
        "sku": "LEM-001",
        "type": "food",
        "base_price": "120.00",
        "currency": "INR",
    }
    response = client.post(url, post_data, HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert response.status_code == 200
    form = response.context["form"]
    assert not form.is_valid()
    assert "category" in form.errors


def test_product_update_view_post_success(client, active_tenant, employee_user):
    client.force_login(employee_user)
    category = Category.objects.create(name="Beverages", slug="beverages")
    product = Product.objects.create(
        category=category,
        name="Classic Lemonade",
        sku="LEM-001",
        base_price=120.00,
        currency="INR"
    )
    
    url = reverse("catalog:product_update", kwargs={"pk": product.id})
    post_data = {
        "name": "Classic Lemonade Updated",
        "sku": "LEM-001",
        "category": str(category.id),
        "type": "food",
        "base_price": "130.00",
        "currency": "INR",
        "description": "Updated desc",
        "is_active": True,
        "track_inventory": True,
    }
    
    response = client.post(url, post_data, HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    if response.status_code == 200:
        print("Form Errors Update:", response.context["form"].errors)
    assert response.status_code == 302
    
    with tenant_context(active_tenant.id):
        # Reload and assert changes
        product.refresh_from_db()
        assert product.name == "Classic Lemonade Updated"
        assert product.base_price == 130.00
        
        # Verify audit log recorded update
        assert AuditLog.all_objects.filter(
            action="product.updated", entity_id=product.id
        ).exists()


def test_category_create_ajax_success(client, active_tenant, employee_user):
    client.force_login(employee_user)
    url = reverse("catalog:category_create_ajax")
    post_data = {
        "name": "Desi Desserts",
        "description": "Sweet Indian treats"
    }
    
    response = client.post(url, post_data, HTTP_HX_REQUEST="true", HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert response.status_code == 200
    content = response.content.decode()
    
    # Should close modal
    assert response.headers.get("HX-Trigger") == "close-category-modal"
    
    with tenant_context(active_tenant.id):
        # Should contain OOB select update with new category pre-selected
        category = Category.objects.get(slug="desi-desserts")
        assert f'value="{category.id}" selected' in content
        assert 'id="id_category"' in content
        assert 'hx-swap-oob="true"' in content
    
    # Should contain OOB toast notification
    assert 'id="toast-region"' in content
    assert 'hx-swap-oob="beforeend"' in content
    assert 'Category "Desi Desserts" created successfully!' in content
    
    # Should render clean fresh form in-band to reset fields
    assert 'name="name"' in content
    assert 'value="Desi Desserts"' not in content  # input field reset


def test_category_create_ajax_validation_duplicate_name(client, active_tenant, employee_user):
    client.force_login(employee_user)
    Category.objects.create(name="Drinks", slug="drinks")
    
    url = reverse("catalog:category_create_ajax")
    # Try creating same name
    post_data = {
        "name": "Drinks",
        "description": "Duplicate drinks"
    }
    
    response = client.post(url, post_data, HTTP_HX_REQUEST="true", HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert response.status_code == 200
    content = response.content.decode()
    
    # Should NOT trigger close-modal
    assert "close-category-modal" not in response.headers
    
    # Should show validation error in-band
    assert 'A category with the name &quot;Drinks&quot; already exists.' in content
    # Should not have selection options
    assert 'hx-swap-oob="true"' not in content


def test_product_create_does_not_duplicate_on_silent_redirect_crash(
    client, active_tenant, employee_user
):
    """Regression: form_valid used to leave self.object=None, so get_success_url()
    raised AttributeError; the bare except clause swallowed it as a non-field
    error while the @transaction.atomic block had already committed the row.
    Users hit "Save" again and created duplicates. Both must be impossible now.
    """
    client.force_login(employee_user)
    category = Category.objects.create(name="Beverages", slug="beverages")
    url = reverse("catalog:product_create")
    payload = {
        "name": "Iced Tea",
        "sku": "ICE-001",
        "category": str(category.id),
        "type": "food",
        "base_price": "80.00",
        "currency": "INR",
        "description": "",
        "is_active": True,
        "track_inventory": True,
    }

    first = client.post(url, payload, HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert first.status_code == 302, (
        "Create must redirect on success — otherwise the user thinks save failed "
        "and clicks again, creating duplicates."
    )
    assert first.url == reverse("catalog:product_list")

    with tenant_context(active_tenant.id):
        assert Product.objects.filter(sku="ICE-001").count() == 1


def test_category_create_ajax_escapes_html_in_oob_response(
    client, active_tenant, employee_user
):
    """Regression: OOB select/toast were built with raw f-string interpolation
    of the category name — a name containing HTML/script tags landed in the
    response unescaped, giving a tenant member stored-XSS against any other
    user who opened the product form. Must be HTML-escaped now.
    """
    client.force_login(employee_user)
    payload = {"name": "<script>alert(1)</script>Hack", "description": ""}
    response = client.post(
        reverse("catalog:category_create_ajax"),
        payload,
        HTTP_HX_REQUEST="true",
        HTTP_HOST=f"{active_tenant.slug}.nextora.app",
    )
    body = response.content.decode()
    assert response.status_code == 200
    assert "<script>alert(1)</script>" not in body
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in body


def test_tenant_isolation_in_category_validation(client, active_tenant, other_tenant, employee_user):
    # Create "Snacks" category in other tenant
    with tenant_context(other_tenant.id):
        Category.objects.create(name="Snacks", slug="snacks")
        
    client.force_login(employee_user) # Active tenant
    url = reverse("catalog:category_create_ajax")
    post_data = {
        "name": "Snacks", # Same name as other tenant, should be ALLOWED in active tenant
        "description": "My tenant snacks"
    }
    
    response = client.post(url, post_data, HTTP_HX_REQUEST="true", HTTP_HOST=f"{active_tenant.slug}.nextora.app")
    assert response.status_code == 200
    assert response.headers.get("HX-Trigger") == "close-category-modal"
    
    with tenant_context(active_tenant.id):
        # Assert category is saved under active tenant
        assert Category.objects.filter(tenant_id=active_tenant.id, slug="snacks").exists()
