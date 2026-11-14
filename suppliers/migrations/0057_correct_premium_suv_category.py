from django.db import migrations


def correct(apps, schema_editor):
    Group = apps.get_model('suppliers', 'VehicleGroup')
    Category = apps.get_model('suppliers', 'FormVehicleCategory')
    groups = Group.objects.filter(supplier__supplier_name__iexact='MM Cars', group_name__iexact='PREMIUM SUV')
    if groups.exists():
        category, _ = Category.objects.get_or_create(name='רכב פרמיום SUV בינוני')
        through = Category.vehicle_groups.through
        for group in groups:
            through.objects.filter(vehiclegroup_id=group.pk).exclude(formvehiclecategory_id=category.pk).delete()
            through.objects.get_or_create(vehiclegroup_id=group.pk, formvehiclecategory_id=category.pk)


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0056_seed_rental_countries')]
    operations = [migrations.RunPython(correct, migrations.RunPython.noop)]
