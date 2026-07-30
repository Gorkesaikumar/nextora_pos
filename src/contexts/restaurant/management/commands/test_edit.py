from django.core.management.base import BaseCommand
from django.test import Client
from contexts.restaurant.models.layout import DiningTable
from contexts.identity.models import User


class Command(BaseCommand):
    def handle(self, *args, **options):
        # We don't need TenancyMiddleware if we just use Client, because Client uses the real request stack which invokes middleware
        table = DiningTable.objects.raw('SELECT * FROM restaurant_table LIMIT 1')[0]
        from contexts.identity.models import Membership
        membership = Membership.objects.filter(tenant_id=table.tenant_id).first()
        user = membership.user

        
        client = Client()
        client.force_login(user)
        
        url = f'/dashboard/restaurant/{table.tenant_id}/tables/{table.id}/edit/'
        print(f'Fetching: {url}')
        
        response = client.get(url, HTTP_HX_REQUEST='true')
        print(f'Status: {response.status_code}')
        if response.status_code == 500:
            print(response.content.decode('utf-8')[:2000])
