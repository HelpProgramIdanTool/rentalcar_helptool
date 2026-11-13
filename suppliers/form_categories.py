"""Explicit owner-approved website category membership, never guessed from names."""
from django.db import transaction
from .models import FormVehicleCategory, VehicleGroup


def category_map():
    categories = list(FormVehicleCategory.objects.filter(is_active=True).prefetch_related('vehicle_groups'))
    return {c.name: {g.pk for g in c.vehicle_groups.all()} for c in categories} if categories else None


def validate_mapping(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('mappings'), list):
        raise ValueError('Нужен файл утверждённых соответствий.')
    result = {}
    seen = set()
    for item in payload['mappings']:
        name = str(item['category']).strip()
        if not name or len(name)>200:
            raise ValueError('Некорректное название категории.')
        group = VehicleGroup.objects.get(supplier__supplier_name=item['supplier'], group_code=item['group_code'])
        key = (name, group.pk)
        if key in seen:
            raise ValueError('Повтор соответствия в файле.')
        seen.add(key)
        result.setdefault(name, set()).add(group.pk)
    if not result:
        raise ValueError('В файле нет соответствий.')
    return result


@transaction.atomic
def apply_mapping(payload):
    mapping = validate_mapping(payload)
    # Replace only this configuration; bookings, prices and historical offers stay intact.
    FormVehicleCategory.objects.exclude(name__in=mapping).update(is_active=False)
    for name, groups in mapping.items():
        category, _ = FormVehicleCategory.objects.update_or_create(name=name, defaults={'is_active':True})
        category.vehicle_groups.set(groups)
    approved_groups = set().union(*mapping.values())
    VehicleGroup.objects.filter(pk__in=approved_groups, is_active=True).update(show_in_offers=True)
    return {'categories':len(mapping), 'memberships':sum(map(len,mapping.values()))}
