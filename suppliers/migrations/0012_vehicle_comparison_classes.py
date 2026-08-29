from django.db import migrations, models


MAPPINGS = [
    (10, "B_MANUAL", "B — хетчбэк, механика", [("03", "B-MANUAL"), ("01", "EDMR"), ("02", "EDMR")]),
    (20, "B_AUTO", "B — хетчбэк, автомат", [("03", "B-AUTOMATIC"), ("01", "EDAR")]),
    (30, "C_MANUAL_HATCH", "C — хетчбэк, механика", [("01", "CDMR"), ("02", "CDMR")]),
    (40, "C_MANUAL_SEDAN", "C — седан, механика", [("01", "CLMR"), ("02", "CDMR")]),
    (50, "C_AUTO_HATCH", "C — хетчбэк, автомат", [("01", "CDAR"), ("02", "CDAR")]),
    (60, "C_AUTO_SEDAN", "C — седан, автомат", [("01", "CLAR"), ("02", "CDAR")]),
    (70, "C_WAGON_AUTO", "C — универсал, автомат", [("03", "C-STATION-WAGON-AUTOMATIC"), ("01", "CWAR"), ("02", "CWAR")]),
    (80, "D_SEDAN_AUTO", "D — седан, автомат", [("03", "D-AUTOMATIC"), ("01", "DLAR"), ("02", "SLAR")]),
    (90, "D_WAGON_AUTO", "D — универсал, автомат", [("01", "SWAR"), ("02", "SWAR")]),
    (100, "SUV_SMALL_AUTO", "SUV малый — автомат", [("03", "C-CROSSOVER-AUTOMATIC"), ("02", "IGAH")]),
    (110, "SUV_MEDIUM_AUTO", "SUV средний — автомат", [("03", "SUV-MEDIUM-AUTOMATIC"), ("01", "IFAR"), ("02", "IFAR")]),
    (120, "SUV_BIG_AUTO", "SUV большой — автомат", [("03", "SUV-BIG-AUTOMATIC"), ("01", "FFAR"), ("02", "FFAR")]),
    (130, "SUV_7_AUTO", "SUV, 7 мест — автомат", [("03", "SUV-7-SEATER-AUTOMATIC"), ("01", "SVAR"), ("02", "FVAR")]),
    (140, "PREMIUM_SEDAN_AUTO", "Премиум седан — автомат", [("03", "E-AUTOMATIC"), ("01", "PLAR"), ("02", "PLAH")]),
    (150, "PREMIUM_SUV_AUTO", "Премиум SUV — автомат", [("03", "SUV-MEDIUM-PREMIUM-AUTOMATIC"), ("01", "PFAR"), ("02", "PFBD")]),
    (160, "PASSENGER_VAN_AUTO", "Пассажирский van, 8–9 мест — автомат", [("03", "BUS-9-SEATER-AUTOMATIC"), ("01", "FVAR"), ("02", "PVAD")]),
]


def seed_classes(apps, schema_editor):
    Comparison = apps.get_model("suppliers", "VehicleComparisonClass")
    Group = apps.get_model("suppliers", "VehicleGroup")
    for order, code, name, group_keys in MAPPINGS:
        comparison, _ = Comparison.objects.get_or_create(
            code=code, defaults={"name": name, "display_order": order}
        )
        for supplier_code, group_code in group_keys:
            group = Group.objects.filter(
                supplier__supplier_code=supplier_code, group_code=group_code
            ).first()
            if group:
                comparison.vehicle_groups.add(group)


def unseed_classes(apps, schema_editor):
    apps.get_model("suppliers", "VehicleComparisonClass").objects.filter(
        code__in=[item[1] for item in MAPPINGS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0011_pricelist_pricedayrange_priceseason_vehiclerate_and_more")]
    operations = [
        migrations.CreateModel(
            name="VehicleComparisonClass",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=40, unique=True)),
                ("name", models.CharField(max_length=120)),
                ("display_order", models.PositiveSmallIntegerField(default=0)),
                ("is_active", models.BooleanField(default=True)),
                ("vehicle_groups", models.ManyToManyField(blank=True, related_name="comparison_classes", to="suppliers.vehiclegroup")),
            ],
            options={"ordering": ["display_order", "name"]},
        ),
        migrations.RunPython(seed_classes, unseed_classes),
    ]
