from django.db import migrations

def seed(apps, schema_editor):
    Branch = apps.get_model('suppliers', 'SupplierLocalBranch')
    # The existing Prague branch identifies the supplier; no calculation codes.
    for branch in Branch.objects.filter(country__code='CZ', supplier__supplier_name__iexact='Car Free'):
        if not branch.offer_mode_label:
            branch.offer_mode_label = 'Car Free — аренда в Чехии'
            branch.offer_mode_help = 'Только местная аренда Car Free в Чехии. Выезд за границу означает выезд за пределы Чехии. Международная выдача/возврат оформляются в обычном режиме. Тарифы требуют подтверждения владельца.'
            branch.offer_mode_enabled = True
            branch.save(update_fields=['offer_mode_label','offer_mode_help','offer_mode_enabled'])

class Migration(migrations.Migration):
    dependencies = [('suppliers', '0060_supplierlocalbranch_offer_mode_enabled_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
