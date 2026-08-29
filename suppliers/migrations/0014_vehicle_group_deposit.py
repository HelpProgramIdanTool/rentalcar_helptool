from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0013_vehicle_group_rate_source")]
    operations = [
        migrations.AddField(
            model_name="vehiclegroup",
            name="deposit_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text="Card authorization amount for this vehicle group.",
                max_digits=10,
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name="vehiclegroup",
            name="deposit_currency",
            field=models.CharField(default="PLN", max_length=3),
        ),
    ]
