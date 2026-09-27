from django.db import migrations, models


def configure_seven_seat_names(apps, schema_editor):
    VehicleGroup = apps.get_model("suppliers", "VehicleGroup")
    VehicleGroup.objects.filter(
        supplier__supplier_code__in=("01", "02"),
        group_code__in=("SVAR", "SVAD"),
    ).update(
        customer_name_he="רכב עם 7 מקומות — אוטומטי",
        customer_name_en="7-seat vehicle — automatic",
    )


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0028_airport_service_wording")]

    operations = [
        migrations.AddField(
            model_name="vehiclegroup",
            name="customer_name_en",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.AddField(
            model_name="vehiclegroup",
            name="customer_name_he",
            field=models.CharField(blank=True, max_length=150),
        ),
        migrations.RunPython(configure_seven_seat_names, migrations.RunPython.noop),
    ]
