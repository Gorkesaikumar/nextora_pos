import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nextora.settings')
django.setup()

from django.test import Client
from contexts.identity.models import Membership

membership = Membership.objects.first()
if not membership:
    print("No membership found")
    exit()

client = Client(SERVER_NAME='127.0.0.1')
client.force_login(membership.user)
url = f'/dashboard/restaurant/{membership.tenant_id}/tables/create/'
print(f'Fetching {url}')
res = client.get(url, HTTP_HX_REQUEST='true', SERVER_NAME='127.0.0.1')

print('Status:', res.status_code)
if res.status_code == 200:
    print('Content looks like:')
    print(res.content.decode('utf-8')[:500])
else:
    print('Error content:')
    print(res.content.decode('utf-8'))
