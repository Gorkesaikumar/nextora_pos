import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.test import Client
from contexts.identity.models import User

client = Client()
user = User.objects.first()
if user:
    client.force_login(user)
    response = client.get("/billing/upgrade/")
    print(f"Status Code: {response.status_code}")
    if response.status_code == 500:
        print(response.content.decode('utf-8'))
    elif response.status_code == 302:
        print(f"Redirected to: {response.url}")
else:
    print("No user found")
