import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from contexts.restaurant.models.layout import DiningTable
from django.test import Client

client = Client()

table = DiningTable.all_objects.first()
if not table:
    print("No table")
    exit()

print(f"Testing POST for table {table.id}")
from contexts.identity.models import User
user = User.objects.first()
client.force_login(user)

url = f'/dashboard/restaurant/tables/{table.id}/edit/'

# Simulate a valid form submission
data = {
    'number': table.number,
    'capacity': 8,
    'shape': table.shape,
    'status': table.status,
    'position_x': table.position_x,
    'position_y': table.position_y,
    'rotation': table.rotation,
    'is_active': 'on' if table.is_active else ''
}

response = client.post(url, data=data, HTTP_X_TENANT_ID=str(table.tenant_id), HTTP_HX_REQUEST="true")
print(f"POST response status: {response.status_code}")
if response.status_code == 200:
    print("Form errors occurred. Response content:")
    print(response.content.decode('utf-8'))
elif response.status_code == 204:
    print("Update successful (204 No Content).")
    
    # Reload and check
    table.refresh_from_db()
    print(f"New capacity: {table.capacity}")
else:
    print(f"Unexpected status: {response.status_code}")
