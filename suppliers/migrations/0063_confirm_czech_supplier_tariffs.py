"""Owner confirmed on 21 November 2026: Czech Car Free uses the same prices."""
from django.db import migrations

def confirm(apps, schema_editor):
    Branch = apps.get_model('suppliers','SupplierLocalBranch')
    for branch in Branch.objects.filter(country__code='CZ', supplier__supplier_name__iexact='Car Free'):
        branch.offer_mode_pricing_confirmed=True
        branch.offer_mode_help=branch.offer_mode_help.replace(
            ' Тарифы требуют подтверждения владельца.',
            ' Используется тот же действующий ценник Car Free, что и для обычных оферт.')
        branch.save(update_fields=['offer_mode_pricing_confirmed','offer_mode_help'])

class Migration(migrations.Migration):
    dependencies=[('suppliers','0062_czech_offer_wording')]
    operations=[migrations.RunPython(confirm,migrations.RunPython.noop)]
