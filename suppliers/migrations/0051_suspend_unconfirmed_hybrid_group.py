from django.db import migrations


def suspend_group(apps, schema_editor):
    Group = apps.get_model('suppliers', 'VehicleGroup')
    Group.objects.using(schema_editor.connection.alias).filter(
        supplier__supplier_name__iexact='Kaizen Rent', group_code='PFAH'
    ).update(is_active=False, show_in_offers=False)


class Migration(migrations.Migration):
    dependencies = [('suppliers','0050_enable_kaizen_chains')]
    # Do not reactivate automatically: the owner must first confirm the tariff.
    operations = [migrations.RunPython(suspend_group, migrations.RunPython.noop)]
