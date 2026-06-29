"""Seed the three public subscription plans + their INR monthly/yearly prices.

Idempotent — safe to re-run; uses code as the natural key.
"""
from decimal import Decimal

from django.db import migrations


PLANS = [
    {
        "code": "starter",
        "name": "Starter",
        "description": "Perfect for single outlet restaurants getting started",
        "trial_days": 14,
        "grace_days": 7,
        "max_branches": 1,
        "max_employees": 5,
        "max_invoices_per_month": 1000,
        "max_storage_mb": 1024,
        "features": {
            "kds": True,
            "inventory": False,
            "reports_basic": True,
            "api_access": False,
            "white_label": False,
        },
        "prices": [
            ("monthly", Decimal("699.00"), "INR"),
            ("yearly", Decimal("8388.00"), "INR"),
        ],
    },
    {
        "code": "growth",
        "name": "Growth",
        "description": "Ideal for growing restaurants with multiple outlets",
        "trial_days": 14,
        "grace_days": 7,
        "max_branches": 3,
        "max_employees": 15,
        "max_invoices_per_month": 5000,
        "max_storage_mb": 5120,
        "features": {
            "kds": True,
            "inventory": True,
            "reports_basic": True,
            "reports_advanced": True,
            "api_access": False,
            "white_label": False,
        },
        "prices": [
            ("monthly", Decimal("1199.00"), "INR"),
            ("yearly", Decimal("14388.00"), "INR"),
        ],
    },
    {
        "code": "professional",
        "name": "Professional",
        "description": "Best for established restaurants that want full control",
        "trial_days": 14,
        "grace_days": 7,
        "max_branches": 10,
        "max_employees": 30,
        "max_invoices_per_month": 10000,
        "max_storage_mb": 10240,
        "features": {
            "kds": True,
            "inventory": True,
            "reports_basic": True,
            "reports_advanced": True,
            "api_access": True,
            "white_label": False,
        },
        "prices": [
            ("monthly", Decimal("1999.00"), "INR"),
            ("yearly", Decimal("23988.00"), "INR"),
        ],
    },
    {
        "code": "enterprise",
        "name": "Enterprise",
        "description": "For large chains & enterprises with custom needs",
        "trial_days": 14,
        "grace_days": 14,
        "max_branches": None,
        "max_employees": None,
        "max_invoices_per_month": None,
        "max_storage_mb": None,
        "features": {
            "kds": True,
            "inventory": True,
            "reports_basic": True,
            "reports_advanced": True,
            "api_access": True,
            "white_label": True,
            "dedicated_support": True,
        },
        "prices": [
            ("monthly", Decimal("0.00"), "INR"),
            ("yearly", Decimal("0.00"), "INR"),
        ],
    },
]


def seed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    PlanPrice = apps.get_model("billing", "PlanPrice")

    for raw in PLANS:
        spec = {k: v for k, v in raw.items() if k != "prices"}
        plan, _ = Plan.objects.update_or_create(
            code=spec["code"],
            defaults={**spec, "is_active": True, "is_public": True},
        )
        for interval, amount, currency in raw["prices"]:
            PlanPrice.objects.update_or_create(
                plan=plan, interval=interval, currency=currency,
                defaults={"amount": amount},
            )


def unseed_plans(apps, schema_editor):
    Plan = apps.get_model("billing", "Plan")
    Plan.objects.filter(code__in=[p["code"] for p in PLANS]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_plans, unseed_plans),
    ]
