import os
import sys
import django
import uuid

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from contexts.restaurant.models.layout import DiningTable
from django.test import RequestFactory
from contexts.restaurant.views import TableUpdateView
from django.contrib.sessions.middleware import SessionMiddleware
from django.contrib.auth.middleware import AuthenticationMiddleware
from shared.tenancy.middleware import TenantResolutionMiddleware
from contexts.identity.models import User

# Get a table
table = DiningTable.all_objects.first()
if not table:
    print("No table found")
    exit()

print(f"Testing Update for Table {table.id}")

factory = RequestFactory()
url = f"/dashboard/restaurant/tables/{table.id}/edit/"

# Test GET
request = factory.get(url, HTTP_HX_REQUEST="true")
request.user = User.objects.first()
# Add session
middleware = SessionMiddleware(lambda r: None)
middleware.process_request(request)
request.session.save()

# We need to simulate the tenant middleware manually or add active_tenant_id
request.session["active_tenant_id"] = str(table.tenant_id)
request.tenant_id = table.tenant_id

view = TableUpdateView.as_view()
response = view(request, pk=table.id)
print(f"GET status: {response.status_code}")

# Test POST
data = {
    'number': table.number,
    'capacity': 10,
    'shape': table.shape,
    'status': table.status,
    'position_x': table.position_x,
    'position_y': table.position_y,
    'rotation': table.rotation,
    'is_active': 'on'
}
post_request = factory.post(url, data=data, HTTP_HX_REQUEST="true")
post_request.user = request.user
middleware.process_request(post_request)
post_request.session["active_tenant_id"] = str(table.tenant_id)
post_request.tenant_id = table.tenant_id

post_response = view(post_request, pk=table.id)
print(f"POST status: {post_response.status_code}")
if post_response.status_code == 200:
    print(post_response.rendered_content)

