from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0004_quote_structured_locations"),
        ("suppliers", "0012_vehicle_comparison_classes"),
    ]
    operations = [
        migrations.AddField(
            model_name="quote",
            name="requested_suppliers",
            field=models.ManyToManyField(blank=True, related_name="requested_in_quotes", to="suppliers.supplier"),
        ),
    ]
