import django.db.models.deletion
from django.db import migrations, models


def connect_car_free_suv_rate(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    tariff_group = Group.objects.filter(
        supplier__supplier_code="03", group_code="SUV-MEDIUM-AUTOMATIC"
    ).first()
    big_group = Group.objects.filter(
        supplier__supplier_code="03", group_code="SUV-BIG-AUTOMATIC"
    ).first()
    if tariff_group and big_group:
        big_group.rate_source_group = tariff_group
        big_group.save(update_fields=["rate_source_group"])


def disconnect_car_free_suv_rate(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    Group.objects.filter(
        supplier__supplier_code="03", group_code="SUV-BIG-AUTOMATIC"
    ).update(rate_source_group=None)


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0012_vehicle_comparison_classes")]
    operations = [
        migrations.AddField(
            model_name="vehiclegroup",
            name="rate_source_group",
            field=models.ForeignKey(
                blank=True,
                help_text="Tariff group to use when a price list has a broader group name.",
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="groups_using_this_rate",
                to="suppliers.vehiclegroup",
            ),
        ),
        migrations.RunPython(connect_car_free_suv_rate, disconnect_car_free_suv_rate),
    ]
