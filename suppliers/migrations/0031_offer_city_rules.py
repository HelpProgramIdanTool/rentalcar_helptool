from django.db import migrations


def seed(apps, schema_editor):
    City = apps.get_model("suppliers", "OfferCity")
    Rule = apps.get_model("suppliers", "CityServiceRule")
    Supplier = apps.get_model("suppliers", "Supplier")
    Extra = apps.get_model("suppliers", "SupplierExtra")
    Group = apps.get_model("suppliers", "VehicleGroup")
    car_free = Supplier.objects.filter(supplier_name="Car Free").first()
    extra = Extra.objects.filter(supplier=car_free, extra_code="FOREIGN_CITY_DELIVERY", is_active=True).first() if car_free else None
    cities = [
        ("Pardubice", "Pardubice", "Czech Republic"),
        ("Budapest", "Будапешт", "Hungary"), ("Vienna", "Вена", "Austria"),
        ("Bratislava", "Братислава", "Slovakia"), ("Prague", "Прага", "Czech Republic"),
        ("Berlin", "Берлин", "Germany"), ("Vilnius", "Вильно (Вильнюс)", "Lithuania"),
    ]
    for order, (name, label, country) in enumerate(cities):
        city, _ = City.objects.get_or_create(name=name, defaults={"label": label, "country": country, "display_order": order})
        if car_free and name in {"Prague", "Pardubice"}:
            Rule.objects.get_or_create(city=city, supplier=car_free)
        elif car_free and extra and name in {"Budapest", "Vienna", "Bratislava", "Berlin"}:
            Rule.objects.get_or_create(city=city, supplier=car_free, defaults={"extra": extra})
    if car_free:
        Group.objects.filter(supplier=car_free, group_code="SUV-MEDIUM-AUTOMATIC").update(show_in_offers=False)


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0030_offercity_vehiclegroup_show_in_offers_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
