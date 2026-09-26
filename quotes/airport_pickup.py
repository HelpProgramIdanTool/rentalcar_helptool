import unicodedata

from suppliers.models import AirportPickupWording, SupplierLocation


def _plain(value):
    return "".join(
        character for character in unicodedata.normalize("NFKD", value.casefold())
        if not unicodedata.combining(character)
    )


def airport_code_for_city(city):
    """Resolve only an unambiguous airport city from the supplier location data."""
    name = _plain(city).strip()
    if not name:
        return None
    codes = {
        location.airport_code for location in SupplierLocation.objects.filter(
            location_type=SupplierLocation.LocationType.AIRPORT,
            is_active=True,
        ).exclude(airport_code="")
        if _plain(location.city) == name
        or _plain(location.city).startswith((name + " ", name + "-"))
    }
    return next(iter(codes)) if len(codes) == 1 else None


def _airport_event_messages(quote, supplier_ids, side, language):
    if getattr(quote, f"{side}_service", "") != "AIRPORT":
        return {}
    code = airport_code_for_city(getattr(quote, f"{side}_city", ""))
    locations = {
        location.supplier_id: location
        for location in SupplierLocation.objects.filter(
            airport_code=code, is_active=True,
            supplier_id__in=supplier_ids,
        ).order_by("supplier_id", "id")
    } if code else {}
    text_field = "text_en" if language == "English" else "text_he"
    wording = dict(AirportPickupWording.objects.values_list("method_code", text_field))
    messages = {}
    for supplier_id in supplier_ids:
        location = locations.get(supplier_id)
        base_method = (
            "DESK" if location and location.has_rental_desk else
            "MEET" if location and location.supports_terminal_delivery else
            "UNKNOWN"
        )
        method = base_method if side == "pickup" else (
            "RETURN_DESK" if base_method == "DESK" else
            "RETURN_MEET" if base_method == "MEET" else
            "RETURN_UNKNOWN"
        )
        messages[supplier_id] = wording.get(method, "")
    return messages


def airport_pickup_messages(quote, supplier_ids, language="Hebrew"):
    return _airport_event_messages(quote, supplier_ids, "pickup", language)


def airport_service_messages(quote, supplier_ids, language="Hebrew"):
    pickup = _airport_event_messages(quote, supplier_ids, "pickup", language)
    returned = _airport_event_messages(quote, supplier_ids, "return", language)
    return {
        supplier_id: "\n".join(
            message for message in (
                pickup.get(supplier_id, ""), returned.get(supplier_id, "")
            ) if message
        )
        for supplier_id in supplier_ids
        if pickup.get(supplier_id) or returned.get(supplier_id)
    }
