from django.db import migrations
from django.db.models import Max


def link_unmatched_groups(apps, schema_editor):
    Group = apps.get_model("suppliers", "VehicleGroup")
    Comparison = apps.get_model("suppliers", "VehicleComparisonClass")
    next_order = (Comparison.objects.aggregate(value=Max("display_order"))["value"] or 0) + 1
    groups = Group.objects.filter(
        is_active=True, comparison_classes__isnull=True
    ).select_related("supplier").order_by(
        "supplier__supplier_code", "display_order", "group_code"
    )
    for group in groups:
        code = f"SUP_{group.supplier.supplier_code}_{group.group_code}"[:40]
        comparison, _ = Comparison.objects.get_or_create(
            code=code,
            defaults={
                "name": f"{group.supplier.supplier_name} — {group.group_name} ({group.group_code})",
                "display_order": next_order,
                "is_active": True,
            },
        )
        comparison.vehicle_groups.add(group)
        next_order += 1


class Migration(migrations.Migration):
    dependencies = [("suppliers", "0015_kaizen_cross_border_499")]
    operations = [migrations.RunPython(link_unmatched_groups, migrations.RunPython.noop)]
