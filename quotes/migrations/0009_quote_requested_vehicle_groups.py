from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("quotes", "0008_quote_option_deposit_and_payment_text"),
        ("suppliers", "0016_make_all_vehicle_groups_selectable"),
    ]
    operations = [
        migrations.AddField(
            model_name="quote",
            name="requested_vehicle_groups",
            field=models.ManyToManyField(
                blank=True,
                related_name="directly_requested_in_quotes",
                to="suppliers.vehiclegroup",
            ),
        ),
    ]
