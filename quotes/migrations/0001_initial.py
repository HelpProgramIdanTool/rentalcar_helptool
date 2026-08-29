import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [("customers", "0001_initial"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="QuoteNumberSequence",
            fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("year", models.PositiveIntegerField(unique=True)), ("last_number", models.PositiveIntegerField(default=0))],
        ),
        migrations.CreateModel(
            name="Quote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("quote_number", models.CharField(editable=False, max_length=20, unique=True)),
                ("status", models.CharField(choices=[("DRAFT", "Draft"), ("SENT", "Sent"), ("ACCEPTED", "Accepted"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled"), ("CLOSED", "Closed")], default="DRAFT", max_length=20)),
                ("language", models.CharField(blank=True, max_length=50)), ("pickup_datetime", models.DateTimeField()), ("return_datetime", models.DateTimeField()), ("rental_days", models.PositiveIntegerField(editable=False)),
                ("pickup_location_text", models.CharField(max_length=300)), ("return_location_text", models.CharField(max_length=300)), ("cross_border_requested", models.BooleanField(default=False)), ("driver_count", models.PositiveSmallIntegerField(default=1)), ("vehicle_request", models.CharField(blank=True, max_length=200)), ("customer_notes", models.TextField(blank=True)), ("internal_notes", models.TextField(blank=True)), ("created_at", models.DateTimeField(auto_now_add=True)), ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="created_quotes", to=settings.AUTH_USER_MODEL)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="quotes", to="customers.customer")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
