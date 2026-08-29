from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0001_initial"),
        ("suppliers", "0012_vehicle_comparison_classes"),
    ]
    operations = [
        migrations.AddField(
            model_name="quote",
            name="requested_vehicle_classes",
            field=models.ManyToManyField(blank=True, related_name="quotes", to="suppliers.vehiclecomparisonclass"),
        ),
    ]
