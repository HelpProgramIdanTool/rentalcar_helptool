from django.db import migrations, models
import django.core.validators
from decimal import Decimal


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="TaxRate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("country", models.CharField(max_length=100)),
                ("tax_name", models.CharField(default="VAT", max_length=50)),
                ("rate_percent", models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(Decimal("0.00")), django.core.validators.MaxValueValidator(Decimal("100.00"))])),
                ("valid_from", models.DateField()),
                ("valid_to", models.DateField(blank=True, null=True)),
                ("is_active", models.BooleanField(default=True)),
            ],
            options={
                "ordering": ["country", "tax_name", "-valid_from"],
                "constraints": [
                    models.UniqueConstraint(fields=("country", "tax_name", "valid_from"), name="unique_tax_rate_start_date"),
                    models.CheckConstraint(condition=models.Q(("rate_percent__gte", 0), ("rate_percent__lte", 100)), name="tax_rate_between_zero_and_one_hundred"),
                    models.CheckConstraint(condition=models.Q(("valid_to__isnull", True), ("valid_to__gte", models.F("valid_from")), _connector="OR"), name="tax_rate_end_not_before_start"),
                ],
            },
        ),
    ]
