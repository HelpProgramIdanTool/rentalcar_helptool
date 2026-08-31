from django.db import migrations


CAR_FREE_LUGGAGE_LITERS = {
    "B-MANUAL": 280,
    "B-AUTOMATIC": 280,
    "C-CROSSOVER-AUTOMATIC": 380,
    "C-STATION-WAGON-AUTOMATIC": 575,
    "D-AUTOMATIC": 460,
    "D-PREMIUM-AUTOMATIC": 524,
    "SUV-BIG-AUTOMATIC": 460,
    "SUV-7-SEATER-AUTOMATIC": 570,
    "E-AUTOMATIC": 540,
    "BUS-9-SEATER-AUTOMATIC": 980,
}


def add_car_free_luggage(apps, schema_editor):
    VehicleGroup = apps.get_model("suppliers", "VehicleGroup")
    for group_code, liters in CAR_FREE_LUGGAGE_LITERS.items():
        VehicleGroup.objects.filter(
            supplier__supplier_code="03", group_code=group_code
        ).update(luggage_volume_liters=liters)


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0018_add_car_free_snow_chains")]
    operations = [
        migrations.RunPython(add_car_free_luggage, migrations.RunPython.noop),
    ]
