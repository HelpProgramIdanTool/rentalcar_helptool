from decimal import Decimal

from django.db import migrations


DEPOSITS = {
    "01": {
        **{code: "500.00" for code in (
            "MCMR", "EDMR", "EDAR", "CDMR", "CLMR", "CDAR", "CLAR",
            "CLAH", "CWMR", "CWAR", "DLAR", "SWAR", "IFMR", "IFAR",
            "FFMR", "FFAR", "SPAR", "FVMR", "FVAR", "CVMR", "CKMR",
            "OKMR", "SVAR", "FCAH",
        )},
        **{code: "1000.00" for code in ("PLAR", "PFAR", "PFAH", "LFAR")},
    },
    "02": {
        **{code: "500.00" for code in (
            "EDMR", "CDMR", "CDAR", "CWAR", "SWAR", "SLAR", "IGAH",
            "IGMR", "IFAR", "FFAR", "FVAR", "SVAD", "PVMD", "PVAD", "SKMD",
        )},
        **{code: "2000.00" for code in ("RLAR", "PLAH", "RGAR", "PFBD", "LFBD")},
    },
    "03": {
        **{code: "500.00" for code in (
            "B-MANUAL", "B-AUTOMATIC", "C-CROSSOVER-AUTOMATIC",
            "C-STATION-WAGON-AUTOMATIC", "D-AUTOMATIC",
            "D-PREMIUM-AUTOMATIC", "SUV-BIG-AUTOMATIC", "SUV-MEDIUM-AUTOMATIC",
        )},
        **{code: "1500.00" for code in (
            "SUV-7-SEATER-AUTOMATIC", "E-AUTOMATIC",
            "SUV-MEDIUM-PREMIUM-AUTOMATIC", "BUS-9-SEATER-AUTOMATIC",
        )},
    },
}


def fill_deposits(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    for supplier_code, groups in DEPOSITS.items():
        for group_code, amount in groups.items():
            Group.objects.filter(
                supplier__supplier_code=supplier_code,
                group_code=group_code,
            ).update(deposit_amount=Decimal(amount), deposit_currency="PLN")


def clear_deposits(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    for supplier_code, groups in DEPOSITS.items():
        Group.objects.filter(
            supplier__supplier_code=supplier_code,
            group_code__in=groups,
        ).update(deposit_amount=None)


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0016_make_all_vehicle_groups_selectable")]
    operations = [migrations.RunPython(fill_deposits, clear_deposits)]
