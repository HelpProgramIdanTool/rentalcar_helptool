from decimal import Decimal, InvalidOperation
from django.utils.translation import gettext as _
from config.driver_fees import YOUNG_DRIVER_CODES


def young_driver_names(booking):
    return [' '.join(filter(None, (driver.first_name, driver.last_name))).strip() or '[driver name missing]'
            for driver in booking.drivers.all() if driver.young_driver_status]


def young_driver_price_error(booking, extras):
    manager = getattr(booking, 'drivers', None)
    if manager is None:
        return ''
    count = sum(driver.young_driver_status for driver in manager.all())
    request = booking.source_quote_snapshot.get('request', {})
    declared = sum(value is True for key, value in request.items()
                   if key.startswith('driver_') and key.endswith('_young'))
    fees = [item for item in extras if item.included_in_total
            and getattr(getattr(item, 'extra', None), 'extra_code', '') in YOUNG_DRIVER_CODES]
    if not count and not declared and not fees:
        return ''
    error = _('Доплата за молодых/новых водителей не соответствует отмеченным водителям. Проверьте тариф и пересчитайте заказ перед отправкой.')
    if not count or (declared and declared != count) or len(fees) != 1:
        return error
    fee = fees[0]
    if fee.quantity != count or not booking.rental_days:
        return error
    from types import SimpleNamespace
    from quotes.services import _quoted_extra_price
    rate = SimpleNamespace(calculation_type=fee.calculation_type_snapshot,
        amount_gross=fee.unit_price_gross_snapshot, minimum_amount_gross=fee.minimum_amount_gross_snapshot,
        maximum_amount_gross=fee.maximum_amount_gross_snapshot, formula_config=fee.formula_snapshot)
    try:
        expected = _quoted_extra_price(fee.extra, rate, Decimal(booking.rental_days), Decimal(count))
        if fee.calculated_price_gross != expected:
            return error
    except (InvalidOperation, TypeError, ValueError):
        return error
    return ''


def booking_price_error(booking, *, extras=None, body=''):
    error = 'Итог заказа не совпадает с расчётом или расчёт не завершён. Пересчитайте заказ перед передачей поставщику. Письмо не отправлено.'
    if '[please verify breakdown]' in body or '[price requires confirmation]' in body:
        return error
    extras = list(booking.extras.all()) if extras is None else extras
    young_error = young_driver_price_error(booking, extras)
    if young_error:
        return young_error
    if body:
        names = young_driver_names(booking) if getattr(booking, 'drivers', None) is not None else []
        if names:
            required = f'Young/new drivers ({len(names)}): ' + ' // '.join(names)
            if required not in body:
                return _('В письме отсутствует описание молодых/новых водителей. Добавьте строку:') + ' ' + required
    if any(item.included_in_total and not item.calculation_complete for item in extras):
        return error
    try:
        expected = booking.vehicle_price_gross + sum((item.calculated_price_gross for item in extras if item.included_in_total),Decimal(0)) + booking.manual_adjustment_amount + booking.subagent_price_adjustment_amount
        if not expected.is_finite() or expected != booking.total_price_gross:
            return error
        reviewed = booking.source_quote_snapshot.get('total')
        if reviewed is not None and Decimal(str(reviewed)) != booking.total_price_gross:
            return error
        if booking.source_quote_snapshot.get('currency',booking.currency) != booking.currency:
            return error
    except (InvalidOperation, TypeError, ValueError):
        return error
    return ''


def amount_text(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def price_breakdown(booking, extras):
    """Describe saved prices only; never reprice a supplier request."""
    base = booking.vehicle_price_gross
    daily = booking.vehicle_daily_rate_gross_snapshot
    days = booking.rental_days
    parts = [amount_text(base)]
    if daily is not None and days and days > 1 and daily * days == base:
        parts = [f"{days}x{amount_text(daily)}"]
    included = [item.calculated_price_gross for item in extras
                if item.included_in_total and item.calculation_complete]
    included.extend([booking.manual_adjustment_amount, booking.subagent_price_adjustment_amount])
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
        hotel_field = 'hotel_name' if side == 'pickup' else 'return_hotel_name'
        hotel = getattr(booking, hotel_field, '') or ''
        parts = list(dict.fromkeys(part.strip() for part in (hotel, address, city) if part and part.strip()))
        if not hotel and not address:
            parts.insert(0, '[street address]')
        return ', '.join(parts)
    return ", ".join(filter(None, [getattr(booking, f"{side}_location_text"), address]))
