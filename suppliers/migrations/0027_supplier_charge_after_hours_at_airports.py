from django.db import migrations, models


def configure_airport_after_hours(apps, schema_editor):
    Supplier = apps.get_model("suppliers", "Supplier")
    Supplier.objects.filter(supplier_code="01").update(
        charge_after_hours_at_airports=False
    )


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0026_keep_existing_kaizen_lists_standard")]

    operations = [
        migrations.AddField(
            model_name="supplier",
            name="charge_after_hours_at_airports",
            field=models.BooleanField(
                default=True,
                verbose_name="Брать доплату вне рабочих часов в аэропортах",
            ),
        ),
        migrations.RunPython(configure_airport_after_hours, migrations.RunPython.noop),
    ]
