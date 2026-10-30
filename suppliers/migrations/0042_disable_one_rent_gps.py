from django.db import migrations


def disable_unavailable_gps(apps, schema_editor):
    extra = apps.get_model('suppliers', 'SupplierExtra')
    extra.objects.filter(supplier__supplier_code='02', extra_code__in=['GPS', 'NAVIGATION']).update(is_active=False)


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0041_pricelist_repeat_annually')]
    operations = [migrations.RunPython(disable_unavailable_gps, migrations.RunPython.noop)]
