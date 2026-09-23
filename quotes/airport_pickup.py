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


def airport_pickup_messages(quote, supplier_ids, language="Hebrew"):
    if quote.pickup_service != "AIRPORT":
        return {}
    code = airport_code_for_city(quote.pickup_city)
    locations = {
        location.supplier_id: location
        for location in SupplierLocation.objects.filter(
            airport_code=code, is_active=True, supports_pickup=True,
            supplier_id__in=supplier_ids,
        )
    } if code else {}
    wording = dict(AirportPickupWording.objects.values_list("method_code", "text_he"))
    if language == "English":
        wording = {
            "DESK": "Vehicle collection is at the rental company's airport desk.",
            "MEET": "A rental company representative will meet you at the airport.",
            "UNKNOWN": "The exact airport collection procedure will be confirmed with the booking.",
        }
    messages = {}
    for supplier_id in supplier_ids:
        location = locations.get(supplier_id)
        method = (
            "DESK" if location and location.has_rental_desk else
            "MEET" if location and location.supports_terminal_delivery else
            "UNKNOWN"
        )
        messages[supplier_id] = wording.get(method, "")
    return messages
