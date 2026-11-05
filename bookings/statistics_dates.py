"""Date evidence for reports only. Never writes inferred dates into bookings."""
import re
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from statistics import median

from django.utils import timezone


def source_date(value):
    if not value:
        return None
    value = str(value).strip()
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        pass
    match = re.match(r'(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]+\s*(\d{2,4})(?!\d)', value)
    if match:
        day, month, year = map(int, match.groups())
        try:
            return date(year + 2000 if year < 100 else year, month, day)
        except ValueError:
            pass
    return None


def category(booking):
    if booking.vehicle_group_id:
        return ('group', booking.vehicle_group_id)
    snapshot = booking.source_quote_snapshot or {}
    raw = snapshot.get('historical_import', {}).get('raw', {})
    label = snapshot.get('request', {}).get('vehicle_note') or raw.get('D', '')
    label = ' '.join(str(label).upper().split())
    return ('label', label) if label else None


def reference_rates(bookings):
    samples = defaultdict(list)
    for booking in bookings:
        if not (booking.pickup_datetime and booking.return_datetime and category(booking)):
            continue
        seconds = (booking.return_datetime - booking.pickup_datetime).total_seconds()
        if seconds <= 0:
            continue
        days = max(Decimal(1), Decimal(str(seconds)) / Decimal(86400))
        amount = booking.vehicle_price_gross or booking.total_price_gross
        if amount > 0:
            samples[(booking.supplier_id, booking.currency, category(booking))].append(amount / days)
    return {key: (median(values), len(values)) for key, values in samples.items()}


def resolve_return(booking, sources, rates):
    """Prefer agreeing source dates, then saved duration, then amount/rate estimate."""
    raw = (booking.source_quote_snapshot or {}).get('historical_import', {}).get('raw', {})
    pickup = timezone.localtime(booking.pickup_datetime).date() if booking.pickup_datetime else source_date(raw.get('B'))
    candidates = set()
    for source in sources:
        start = source_date(source.get('pickup')) or source_date(source.get('pickup_raw')) or pickup
        end = source_date(source.get('return')) or source_date(source.get('return_raw'))
        if end and (not start or end > start):
            candidates.add(end)
        if not pickup and start:
            pickup = start
    raw_end = source_date(raw.get('C'))
    if raw_end and (not pickup or raw_end > pickup):
        candidates.add(raw_end)
    if len(candidates) == 1:
        return dict(return_date=candidates.pop(), basis='Дата из исходных записей', estimated=False)
    if len(candidates) > 1:
        return dict(return_date=None, basis='В источниках разные даты возврата', estimated=False)
    if not pickup:
        return dict(return_date=None, basis='Нет даты получения и надёжной даты возврата', estimated=False)
    if booking.rental_days:
        days, basis = booking.rental_days, 'Оценка по сохранённому числу дней'
    else:
        saved = booking.vehicle_daily_rate_gross_snapshot
        empirical = rates.get((booking.supplier_id, booking.currency, category(booking)))
        rate = saved if saved and saved > 0 else empirical[0] if empirical else None
        amount = booking.vehicle_price_gross or booking.total_price_gross
        if not rate or amount <= 0:
            return dict(return_date=None, basis='Нет подходящего тарифа или положительной суммы', estimated=False)
        days = max(1, int((amount / rate).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
        basis = (f'Оценка по сумме / сохранённому тарифу {rate:.2f}' if saved else
                 f'Оценка по сумме / медиане {rate:.2f} {booking.currency}/день ({empirical[1]} заказов той же категории)')
    try:
        end = pickup + timedelta(days=days)
    except (OverflowError, ValueError):
        return dict(return_date=None, basis='Не удалось оценить срок', estimated=False)
    return dict(return_date=end, basis=basis, estimated=True)
