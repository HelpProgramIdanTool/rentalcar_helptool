from django.db import migrations


def keep_existing_lists_standard(apps, schema_editor):
    PriceList = apps.get_model("suppliers", "PriceList")
    PriceList.objects.filter(supplier__supplier_code="01").update(audience="STANDARD")


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0025_configure_subagent_pricing")]
    operations = [
        migrations.RunPython(keep_existing_lists_standard, migrations.RunPython.noop),
    ]
