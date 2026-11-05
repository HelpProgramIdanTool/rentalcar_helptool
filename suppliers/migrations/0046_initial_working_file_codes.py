from django.db import migrations


def populate(apps, schema_editor):
    Supplier = apps.get_model('suppliers', 'Supplier')
    for code, alias in [('01', 'K'), ('02', 'O'), ('03', 'C'), ('MM_CARS', 'M')]:
        Supplier.objects.filter(supplier_code=code, working_file_code__isnull=True).update(working_file_code=alias)


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0045_supplier_working_file_code')]
    operations = [migrations.RunPython(populate, migrations.RunPython.noop)]
