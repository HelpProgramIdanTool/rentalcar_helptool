from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0003_location_service_methods"),
    ]

    operations = [
        migrations.AlterField(
            model_name="supplierlocation",
            name="location_type",
            field=models.CharField(
                choices=[
                    ("BRANCH", "Branch"),
                    ("AIRPORT", "Airport"),
                    ("HOTEL_DELIVERY", "Hotel delivery"),
                    ("ADDRESS_DELIVERY", "Address delivery"),
                    ("SEASONAL_POINT", "Seasonal point"),
                    ("CUSTOM_POINT", "Custom point"),
                    ("OTHER", "Other"),
                ],
                default="BRANCH",
                max_length=20,
            ),
        ),
    ]
