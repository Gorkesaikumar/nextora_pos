import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from contexts.identity.models import User
user = User.objects.first()
membership = getattr(user, "memberships", None)
if membership and membership.exists():
    tenant = membership.first().tenant
    print("Tenant found:", tenant)
else:
    print("No tenant found for user", user)
