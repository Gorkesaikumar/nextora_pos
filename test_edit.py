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

print(f"Testing GET for table {table.id}")
# We have to bypass login or just login as a user
from contexts.identity.models import User
user = User.objects.first()
client.force_login(user)

url = f'/dashboard/restaurant/tables/{table.id}/edit/'
response = client.get(url, HTTP_X_TENANT_ID=str(table.tenant_id))
print(f"GET response status: {response.status_code}")
if response.status_code == 200:
    print("GET Success")
else:
    print(response.content)

