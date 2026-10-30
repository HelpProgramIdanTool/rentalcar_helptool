from datetime import date
from django.db import migrations


def configure_availability(apps, schema_editor):
    group = apps.get_model('suppliers', 'VehicleGroup')
    group.objects.filter(supplier__supplier_code='02', group_code='SWAR').update(
        available_from=date(2027, 4, 1), is_active=True, show_in_offers=True)


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0043_disable_car_free_snow_chains')]
    operations = [migrations.RunPython(configure_availability, migrations.RunPython.noop)]
