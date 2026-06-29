"""Idempotent demo/dev data seeding.

Repeatable bootstrap for local/QA environments — never run in production.
Kept thin: it should call application services / factories, never inline
business rules, so seeding can't drift from real behaviour.
"""
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Seed demo data for development and QA (idempotent)."

    def handle(self, *args, **options) -> None:
        if not settings.DEBUG:
            raise CommandError("seed_demo refuses to run with DEBUG=False.")

        user_model = get_user_model()
        admin, created = user_model.objects.get_or_create(
            email="admin@nextora.local",
            defaults={"full_name": "Demo Admin", "is_staff": True, "is_superuser": True},
        )
        if created:
            admin.set_password("admin12345")  # noqa: S106 — dev-only fixed creds
            admin.save(update_fields=["password"])
            self.stdout.write(self.style.SUCCESS("Created demo admin."))
        else:
            self.stdout.write("Demo admin already exists; nothing to do.")
