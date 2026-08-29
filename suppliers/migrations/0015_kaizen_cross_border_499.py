from decimal import Decimal

from django.db import migrations


def set_kaizen_cross_border_rate(apps, schema_editor):
    ExtraRate = apps.get_model("suppliers", "SupplierExtraRate")
    ExtraRate.objects.filter(
        extra__supplier__supplier_code="01",
        extra__extra_code="CROSS_BORDER",
        is_active=True,
    ).update(
        amount_gross=Decimal("499.00"),
        calculation_type="PER_RENTAL",
        formula_config={},
        minimum_amount_gross=None,
        maximum_amount_gross=None,
    )


def restore_old_rate(apps, schema_editor):
    ExtraRate = apps.get_model("suppliers", "SupplierExtraRate")
    ExtraRate.objects.filter(
        extra__supplier__supplier_code="01",
        extra__extra_code="CROSS_BORDER",
        is_active=True,
    ).update(amount_gross=Decimal("299.00"))


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0014_vehicle_group_deposit")]
    operations = [
        migrations.RunPython(set_kaizen_cross_border_rate, restore_old_rate),
    ]
