from decimal import Decimal


def amount_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def price_breakdown(booking, extras):
    """Describe saved prices only; never reprice a supplier request."""
    base = booking.vehicle_price_gross
    daily = booking.vehicle_daily_rate_gross_snapshot
    days = booking.rental_days
    parts = [amount_text(base)]
    if daily is not None and days and daily * days == base:
        parts = [f"{days}x{amount_text(daily)}"]
    included = [item.calculated_price_gross for item in extras
                if item.included_in_total and item.calculation_complete]
    if base + sum(included, Decimal("0")) != booking.total_price_gross:
        return f"Total: {amount_text(booking.total_price_gross)} {booking.currency} [please verify breakdown]"
    parts.extend(amount_text(price) for price in included if price != 0)
    return "+".join(parts) + "=" + amount_text(booking.total_price_gross) + " " + booking.currency


def supplier_location(booking, side):
    request = booking.source_quote_snapshot.get("request", {})
    city = request.get(f"{side}_city", "")
    service = request.get(f"{side}_service", "")
    address = getattr(booking, f"{side}_address")
    if city and service == "AIRPORT":
        return f"{city} Airport"
    if city and service == "CITY_BRANCH":
        return f"{city} city branch"
    if city and service == "ADDRESS":
        return f"{address or '[street address]'}, {city}"
    return ", ".join(filter(None, [getattr(booking, f"{side}_location_text"), address]))
