from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("suppliers", "0006_add_location_phone"),
    ]

    operations = [
        migrations.CreateModel(
            name="VehicleGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("group_code", models.CharField(max_length=40)),
                ("group_name", models.CharField(max_length=120)),
                ("category", models.CharField(blank=True, max_length=80)),
                ("body_type", models.CharField(blank=True, choices=[("SEDAN", "Sedan"), ("HATCHBACK", "Hatchback"), ("SUV", "SUV"), ("ESTATE", "Estate / Wagon"), ("MINIVAN", "Minivan"), ("VAN", "Van"), ("PICKUP", "Pickup"), ("COUPE", "Coupe"), ("CABRIO", "Cabrio"), ("OTHER", "Other")], max_length=20)),
                ("transmission", models.CharField(choices=[("MANUAL", "Manual"), ("AUTOMATIC", "Automatic"), ("UNKNOWN", "Unknown")], default="UNKNOWN", max_length=10)),
                ("seats", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("doors", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("luggage_volume_liters", models.PositiveIntegerField(blank=True, null=True)),
                ("luggage_large", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("luggage_small", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("luggage_priority", models.PositiveSmallIntegerField(default=0)),
                ("cargo_note", models.CharField(blank=True, max_length=250)),
                ("fuel_type_note", models.CharField(blank=True, max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("internal_note", models.TextField(blank=True)),
                ("available_from", models.DateField(blank=True, null=True)),
                ("available_to", models.DateField(blank=True, null=True)),
                ("booking_open_from", models.DateField(blank=True, null=True)),
                ("supplier", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vehicle_groups", to="suppliers.supplier")),
            ],
            options={"ordering": ["supplier__supplier_name", "display_order", "group_name"]},
        ),
        migrations.CreateModel(
            name="VehicleModel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(blank=True, max_length=80)),
                ("model", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("vehicle_group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="models", to="suppliers.vehiclegroup")),
            ],
            options={"ordering": ["display_order", "brand", "model"]},
        ),
        migrations.AddConstraint(
            model_name="vehiclegroup",
            constraint=models.UniqueConstraint(fields=("supplier", "group_code"), name="unique_vehicle_group_code_per_supplier"),
        ),
        migrations.AddConstraint(
            model_name="vehiclemodel",
            constraint=models.UniqueConstraint(fields=("vehicle_group", "brand", "model"), name="unique_model_per_vehicle_group"),
        ),
    ]
