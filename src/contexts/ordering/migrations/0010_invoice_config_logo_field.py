# Generated manually — adds logo ImageField to InvoiceConfiguration

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("ordering", "0009_invoicesnapshot_invoiceconfiguration"),
    ]

    operations = [
        migrations.AddField(
            model_name="invoiceconfiguration",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Restaurant logo displayed on receipt",
                null=True,
                upload_to="logos/",
            ),
        ),
    ]
