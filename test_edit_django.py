import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.test import Client
from contexts.restaurant.models.layout import DiningTable
from contexts.identity.models import User

# Get any user and table
user = User.objects.first()
table = DiningTable.objects.first()

if not table:
    print("No tables found")
    sys.exit(0)
    
if not user:
    print("No users found")
    sys.exit(0)

print(f"Testing edit for table {table.id} in tenant {table.tenant_id}")

client = Client()
client.force_login(user)

url = f"/dashboard/restaurant/{table.tenant_id}/tables/{table.id}/edit/"
print(f"Fetching {url}")

response = client.get(url, HTTP_HX_REQUEST="true")
print(f"Status: {response.status_code}")

if response.status_code == 500:
    print(response.content.decode('utf-8'))
