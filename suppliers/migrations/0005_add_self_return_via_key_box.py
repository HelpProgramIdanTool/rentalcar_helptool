from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0004_add_address_delivery_location_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierlocation",
            name="supports_self_return_via_key_box",
            field=models.BooleanField(default=False),
        ),
    ]
