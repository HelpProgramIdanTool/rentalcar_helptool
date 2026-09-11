import datetime

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0020_carfree_premium_rate_sources")]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="regular_service_from",
            field=models.TimeField(default=datetime.time(8, 0)),
        ),
        migrations.AddField(
            model_name="supplier",
            name="regular_service_to",
            field=models.TimeField(default=datetime.time(20, 0)),
        ),
    ]
