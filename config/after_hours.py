from django.utils import timezone


def is_after_hours(supplier, value):
    local_time = timezone.localtime(value).time().replace(tzinfo=None)
    return not supplier.regular_service_from <= local_time <= supplier.regular_service_to


def needs_after_hours_charge(supplier, value, location=None):
    """Use one after-hours decision in offers and orders."""
    if not is_after_hours(supplier, value):
        return False
    if location and not supplier.charge_after_hours_at_airports:
        return False
    return True
