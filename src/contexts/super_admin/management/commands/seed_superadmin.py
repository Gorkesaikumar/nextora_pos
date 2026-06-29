import logging

from django.core.management.base import BaseCommand
from contexts.identity.models import User

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Seed the initial Super Admin account."

    def handle(self, *args, **options):
        email = "hangoverhours@gmail.com"
        password = "S@ikumar1234"
        
        self.stdout.write(self.style.WARNING(f"Attempting to seed Super Admin: {email}"))
        
        if User.objects.filter(email=email).exists():
            self.stdout.write(self.style.SUCCESS(f"Super Admin '{email}' already exists. Skipping creation."))
            return

        user = User.objects.create_superuser(
            email=email,
            password=password,
            full_name="Super Administrator"
        )
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created Super Admin '{email}'."))
