import os
import sys
import django

sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from contexts.restaurant.models.layout import DiningTable

table = DiningTable.all_objects.first()
if table:
    print(f"Table ID: {table.id}")
    print(f"Table Number: {table.number}")
    print(f"Table Capacity: {table.capacity}")
    print(f"Tenant: {table.tenant_id}")
else:
    print("No tables found")
