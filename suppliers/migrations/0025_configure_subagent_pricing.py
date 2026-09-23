from decimal import Decimal

from django.db import migrations


def configure(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    kaizen = Supplier.objects.filter(supplier_code="01").first()
    if kaizen:
        kaizen.subagent_pricing_method = "DEDICATED"
        kaizen.subagent_markup_percent = Decimal("0")
        kaizen.save(update_fields=["subagent_pricing_method", "subagent_markup_percent"])

    one_rent = Supplier.objects.filter(supplier_code="02").first()
    if one_rent:
        one_rent.subagent_pricing_method = "PERCENT_TOTAL"
        one_rent.subagent_markup_percent = Decimal("4.00")
        one_rent.save(update_fields=["subagent_pricing_method", "subagent_markup_percent"])

    car_free = Supplier.objects.filter(supplier_code="03").first()
    if car_free:
        car_free.subagent_pricing_method = "STANDARD"
        car_free.subagent_markup_percent = Decimal("0")
        car_free.save(update_fields=["subagent_pricing_method", "subagent_markup_percent"])


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0024_pricelist_audience_supplier_subagent_markup_percent_and_more")]
    operations = [migrations.RunPython(configure, migrations.RunPython.noop)]
