from django.core.management.base import BaseCommand
from django.test import Client
from contexts.restaurant.models.layout import DiningTable
from contexts.identity.models import User

class Command(BaseCommand):
    help = 'Test TableUpdateView GET request'

    def handle(self, *args, **options):
        table = DiningTable.all_objects.first()
        if not table:
            self.stdout.write(self.style.ERROR('No table found'))
            return

        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('No user found'))
            return

        client = Client()
        client.force_login(user)

        # Set session active_tenant_id
        session = client.session
        session['active_tenant_id'] = str(table.tenant_id)
        session.save()

        url = f'/dashboard/restaurant/tables/{table.id}/edit/'
        self.stdout.write(f'Testing GET {url}')
        
        response = client.get(url, HTTP_HX_REQUEST="true")
        
        self.stdout.write(f'Status: {response.status_code}')
        if response.status_code == 200:
            self.stdout.write(self.style.SUCCESS('Successfully fetched modal'))
            # Print first 200 chars of response
            self.stdout.write(response.content.decode('utf-8')[:200])
        else:
            self.stdout.write(self.style.ERROR('Failed to fetch modal'))
            self.stdout.write(response.content.decode('utf-8')[:500])
