from datetime import date
from decimal import Decimal

from django.db import migrations


def add_car_free_snow_chains(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    SupplierExtra = apps.get_model("suppliers", "SupplierExtra")
    SupplierExtraRate = apps.get_model("suppliers", "SupplierExtraRate")

    supplier = Supplier.objects.filter(supplier_code="03").first()
    if supplier is None:
        return
    extra, _ = SupplierExtra.objects.update_or_create(
        supplier=supplier,
        extra_code="SNOW_CHAINS",
        defaults={
            "name": "Snow chains",
            "category": "EQUIPMENT",
            "description": "Snow chains: 25 PLN per day, maximum 250 PLN per rental.",
            "is_mandatory": False,
            "is_active": True,
        },
    )
    SupplierExtraRate.objects.update_or_create(
        extra=extra,
        rate_code="DEFAULT",
        defaults={
            "calculation_type": "PER_DAY",
            "amount_gross": Decimal("25.00"),
            "currency": "PLN",
            "days_from": None,
            "days_to": None,
            "minimum_amount_gross": None,
            "maximum_amount_gross": Decimal("250.00"),
            "valid_from": date(2026, 1, 1),
            "valid_to": None,
            "priority": 0,
            "formula_config": {},
            "is_active": True,
            "note": "Confirmed by Idan.",
        },
    )


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0017_fill_vehicle_group_deposits")]
    operations = [
        migrations.RunPython(add_car_free_snow_chains, migrations.RunPython.noop),
    ]
