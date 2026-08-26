from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0005_add_self_return_via_key_box"),
    ]

    operations = [
        migrations.AddField(
            model_name="supplierlocation",
            name="phone",
            field=models.CharField(blank=True, max_length=40),
        ),
    ]
