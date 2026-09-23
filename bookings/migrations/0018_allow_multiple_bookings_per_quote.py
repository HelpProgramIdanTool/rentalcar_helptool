from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("bookings", "0017_booking_subagent_price_adjustment_amount"),
        ("quotes", "0018_quote_sub_agent"),
    ]

    operations = [
        migrations.AlterField(
            model_name="booking",
            name="source_quote",
            field=models.ForeignKey(
                blank=True,
                editable=False,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="quotes.quote",
            ),
        ),
    ]
