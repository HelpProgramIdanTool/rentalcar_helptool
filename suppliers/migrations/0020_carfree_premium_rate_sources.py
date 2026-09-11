from django.db import migrations


RATE_SOURCE_MAPPINGS = {
    "D-PREMIUM-AUTOMATIC": "D-AUTOMATIC",
    "SUV-MEDIUM-PREMIUM-AUTOMATIC": "E-AUTOMATIC",
}


def connect_premium_rate_sources(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    for premium_code, tariff_code in RATE_SOURCE_MAPPINGS.items():
        tariff_group = Group.objects.filter(
            supplier__supplier_code="03", group_code=tariff_code
        ).first()
        if tariff_group:
            Group.objects.filter(
                supplier__supplier_code="03", group_code=premium_code
            ).update(rate_source_group=tariff_group)


def disconnect_premium_rate_sources(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    Group.objects.filter(
        supplier__supplier_code="03",
        group_code__in=RATE_SOURCE_MAPPINGS,
    ).update(rate_source_group=None)


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0019_car_free_luggage_capacity")]
    operations = [
        migrations.RunPython(
            connect_premium_rate_sources,
            disconnect_premium_rate_sources,
        )
    ]
