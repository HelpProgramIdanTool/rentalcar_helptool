"""Check saved after-hours charges before producing a customer-facing offer."""
from decimal import Decimal, InvalidOperation

from django.utils import timezone

from .services import _active_extra_rate, _after_hours_extra_requests, _quoted_extra_price
from .one_way import automatic_route_extras
from suppliers.models import SupplierExtra


def saved_fee_amount(lines, extra):
    """Old snapshots used names; new ones retain the stable extra identifier."""
    try:
        return sum((Decimal(str(line['price'])) for line in lines
                    if (str(line.get('extra_id')) == str(extra.pk)
                        or (not line.get('extra_id') and line.get('name') == extra.name))), Decimal(0))
    except (KeyError, InvalidOperation, TypeError):
        return None


def balanced_snapshot(option, snapshot):
    try:
        lines_total=sum((Decimal(str(line['price'])) for line in snapshot.get('lines',[])),Decimal(0))
        extras=Decimal(str(snapshot['extras_total']))
        total=Decimal(str(snapshot['base']))+extras+Decimal(str(snapshot.get('subagent_adjustment',0)))+option.manual_adjustment_amount
        return lines_total==extras and total==option.total_price_gross
    except (KeyError,InvalidOperation,TypeError,ValueError):
        return False


def quote_price_issues(quote):
    issues = []
    pickup_date = timezone.localtime(quote.pickup_datetime).date()
    for option in quote.options.filter(is_included=True).select_related('supplier'):
        supplier = option.supplier
        requests = _after_hours_extra_requests(quote, supplier)
        snapshot = option.calculation_snapshot or {}
        if snapshot.get('rental_country', 'PL') != quote.rental_country:
            issues.append(f'{supplier.supplier_name}: страна аренды изменена. Требуется пересчёт оферты.')
        route_requests, route_issues = automatic_route_extras(quote, supplier)
        issues.extend(route_issues)
        for extra in supplier.extras.filter(is_active=True,automatic_rule=SupplierExtra.AutomaticRule.DOMESTIC_ONE_WAY):
            quantity=route_requests.get(extra.extra_code,Decimal(0))
            rate=_active_extra_rate(extra,pickup_date,quote.rental_days) if quantity else None
            if quantity and rate is None:
                issues.append(f'{supplier.supplier_name}: не определён тариф возврата в другом городе.')
                continue
            expected=_quoted_extra_price(extra,rate,Decimal(quote.rental_days),quantity) if rate else Decimal(0)
            if saved_fee_amount(snapshot.get('lines',[]),extra) != expected:
                issues.append(f'{supplier.supplier_name}: доплата за возврат в другом городе должна составлять {expected:.2f} {rate.currency if rate else option.currency}. Требуется пересчёт.')
            elif quantity and not balanced_snapshot(option,snapshot):
                issues.append(f'{supplier.supplier_name}: доплата за возврат в другом городе не согласуется с итогом оферты. Требуется пересчёт.')
        for extra in supplier.extras.filter(is_active=True, extra_code__in=('OUT_OF_HOURS', 'NIGHT_SERVICE')):
            quantity = requests.get(extra.extra_code, Decimal(0))
            rate = _active_extra_rate(extra, pickup_date, quote.rental_days) if quantity else None
            prefix = f'{supplier.supplier_name} · {option.vehicle_group_name_snapshot}'
            if quantity and rate is None:
                issues.append(f'{prefix}: нет действующего тарифа обслуживания вне рабочих часов.')
                continue
            expected = _quoted_extra_price(extra, rate, Decimal(quote.rental_days), quantity) if rate else Decimal(0)
            saved = saved_fee_amount(snapshot.get('lines', []), extra)
            if saved != expected:
                issues.append(f'{prefix}: доплата за получение/возврат вне рабочих часов должна составлять {expected:.2f} {rate.currency if rate else option.currency}. Сохранённый расчёт не соответствует времени аренды и тарифу.')
                continue
            # A fee described in the snapshot must also be included in its sum.
            if quantity:
                try:
                    lines_total = sum((Decimal(str(line['price'])) for line in snapshot.get('lines', [])), Decimal(0))
                    extras_total = Decimal(str(snapshot['extras_total']))
                    total = Decimal(str(snapshot['base'])) + extras_total + Decimal(str(snapshot.get('subagent_adjustment', 0))) + option.manual_adjustment_amount
                    valid = lines_total == extras_total and total == option.total_price_gross
                except (KeyError, InvalidOperation, TypeError):
                    valid = False
                if not valid:
                    issues.append(f'{prefix}: итоговая сумма не совпадает с сохранёнными доплатами. Требуется пересчёт.')
    return issues
