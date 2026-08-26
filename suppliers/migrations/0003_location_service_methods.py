from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0002_supplierlocation"),
    ]

    operations = [
        migrations.RenameField(
            model_name="supplierlocation",
            old_name="supports_delivery",
            new_name="supports_address_delivery",
        ),
        migrations.AddField(
            model_name="supplierlocation",
            name="has_rental_desk",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="supplierlocation",
            name="supports_terminal_delivery",
            field=models.BooleanField(default=False),
        ),
    ]
