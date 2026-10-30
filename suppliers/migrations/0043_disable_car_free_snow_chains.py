from django.db import migrations


def disable_unavailable_chains(apps, schema_editor):
    extra = apps.get_model('suppliers', 'SupplierExtra')
    extra.objects.filter(supplier__supplier_code='01', extra_code='SNOW_CHAINS').update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0042_disable_one_rent_gps')]
    operations = [migrations.RunPython(disable_unavailable_chains, migrations.RunPython.noop)]
