from django.db import migrations


def enable_chains(apps, schema_editor):
    Extra = apps.get_model('suppliers', 'SupplierExtra')
    Rate = apps.get_model('suppliers', 'SupplierExtraRate')
    alias = schema_editor.connection.alias
    extras = Extra.objects.using(alias).filter(supplier__supplier_name__iexact='Kaizen Rent', extra_code='SNOW_CHAINS')
    for extra in extras:
        if Rate.objects.using(alias).filter(extra_id=extra.pk,is_active=True).exists():
            Extra.objects.using(alias).filter(pk=extra.pk).update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [('suppliers','0049_formvehiclecategory')]
    operations = [migrations.RunPython(enable_chains, migrations.RunPython.noop)]
