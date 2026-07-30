import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextora.settings')
django.setup()

from django.test import Client
from contexts.restaurant.models.layout import DiningTable
from contexts.identity.models import Membership

tables = list(DiningTable.objects.raw('SELECT * FROM restaurant_table LIMIT 1'))
if not tables:
    print("No tables found")
    exit()

table = tables[0]
membership = Membership.objects.filter(tenant_id=table.tenant_id).first()
if not membership:
    print("No membership found")
    exit()

client = Client(SERVER_NAME='127.0.0.1')
client.force_login(membership.user)
url = f'/dashboard/restaurant/{table.tenant_id}/tables/{table.id}/edit/'
print(f'Fetching {url}')
res = client.get(url, HTTP_HX_REQUEST='true', SERVER_NAME='127.0.0.1')

print('Status:', res.status_code)
if res.status_code == 200:
    print('Content looks like:')
    print(res.content.decode('utf-8')[:500])
else:
    print('Error content:')
    print(res.content.decode('utf-8'))
