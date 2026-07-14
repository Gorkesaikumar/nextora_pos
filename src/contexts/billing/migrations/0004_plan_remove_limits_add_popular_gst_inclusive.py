"""
Migration: Remove business-irrelevant limit columns from Plan.
Add: gst_inclusive, is_popular, trial_eligible fields.

Business rationale: Nextora POS offers 100% of features on every plan.
There are no usage limits; plans differ only in duration and price.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0003_globaltrialconfig_subscriptionvisibilityconfig_and_more"),
    ]

    operations = [
        # ── Remove limit columns ───────────────────────────────────────────────
        migrations.RemoveField(model_name="plan", name="max_branches"),
        migrations.RemoveField(model_name="plan", name="max_employees"),
        migrations.RemoveField(model_name="plan", name="max_invoices_per_month"),
        migrations.RemoveField(model_name="plan", name="max_storage_mb"),

        # ── Add new pricing/display fields ────────────────────────────────────
        migrations.AddField(
            model_name="plan",
            name="gst_inclusive",
            field=models.BooleanField(
                default=True,
                help_text="If True, sale_price already includes GST. If False, GST is added on top.",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="is_popular",
            field=models.BooleanField(
                default=False,
                help_text="Show 'Popular' badge",
            ),
        ),
        migrations.AddField(
            model_name="plan",
            name="trial_eligible",
            field=models.BooleanField(
                default=True,
                help_text="Allow free trial for this plan",
            ),
        ),

        # ── Improve help_text on existing fields (no schema change) ───────────
        migrations.AlterField(
            model_name="plan",
            name="code",
            field=models.CharField(
                max_length=50,
                unique=True,
                help_text="URL-safe unique slug, e.g. 'monthly-pro'",
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="is_public",
            field=models.BooleanField(
                default=True,
                help_text="Visible to customers on Registration Wizard & Choose Plan pages",
            ),
        ),
        migrations.AlterField(
            model_name="plan",
            name="trial_days",
            field=models.PositiveIntegerField(
                default=0,
                help_text="Free trial duration in days (0 = no trial)",
            ),
        ),
    ]
