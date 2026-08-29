import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("quotes", "0005_quote_requested_suppliers"), ("suppliers", "0013_vehicle_group_rate_source")]
    operations = [
        migrations.CreateModel(
            name="QuoteOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("supplier_name_snapshot", models.CharField(max_length=120)), ("vehicle_group_name_snapshot", models.CharField(max_length=120)), ("vehicle_models_snapshot", models.TextField(blank=True)),
                ("total_price_gross", models.DecimalField(decimal_places=2, max_digits=12)), ("currency", models.CharField(default="PLN", max_length=3)), ("calculation_snapshot", models.JSONField(default=dict)),
                ("display_order", models.PositiveSmallIntegerField(default=0)), ("is_included", models.BooleanField(default=True)), ("is_selected_by_customer", models.BooleanField(default=False)), ("created_at", models.DateTimeField(auto_now_add=True)),
                ("comparison_class", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quote_options", to="suppliers.vehiclecomparisonclass")), ("quote", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="options", to="quotes.quote")), ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quote_options", to="suppliers.supplier")), ("vehicle_group", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quote_options", to="suppliers.vehiclegroup")),
            ], options={"ordering": ["display_order", "total_price_gross"]},
        ),
        migrations.AddConstraint(model_name="quoteoption", constraint=models.UniqueConstraint(fields=("quote", "vehicle_group"), name="one_option_per_quote_vehicle_group")),
    ]
