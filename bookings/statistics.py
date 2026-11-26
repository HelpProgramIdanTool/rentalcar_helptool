"""Read-only turnover reports; supplier statements and bookings never overlap."""
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.cache import never_cache

from employees.models import Employee
from reconciliation.models import Reconciliation, Row
from reconciliation.services import money, row_net
from .models import Booking
from .statistics_dates import reference_rates, resolve_return


def can_view_statistics(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    employee = Employee.objects.filter(login_user=user).first()
    if employee:
        return employee.status == Employee.Status.ACTIVE and employee.role in (
            Employee.Role.OWNER_ADMIN, Employee.Role.ADMIN)
    return user.is_staff


def booking_summary(records, today):
    """Records are already restricted to the selected return year."""
    def empty():
        return dict(count=0, gross=Decimal(0), elapsed=Decimal(0), future=Decimal(0), zero=0)
    suppliers, months, totals, monthly_totals = defaultdict(empty), defaultdict(empty), defaultdict(empty), defaultdict(empty)
    for item in records:
        amount = Decimal(item['gross'])
        currency = item['currency']
        keys = (totals[currency], suppliers[(item['supplier'], currency)],
                months[(item['month'], item['supplier'], currency)], monthly_totals[(item['month'], currency)])
        for value in keys:
            value['count'] += 1
            value['gross'] += amount
            value['elapsed' if item['return_date'] <= today else 'future'] += amount
            value['zero'] += amount == 0
    def finish(value):
        return {**value, 'average': money(value['gross'] / value['count'])}
    return {
        'totals': [dict(currency=key, **finish(value)) for key, value in sorted(totals.items())],
        'suppliers': [dict(supplier=key[0], currency=key[1], **finish(value))
                      for key, value in sorted(suppliers.items())],
        'months': [dict(month=key[0], supplier=key[1], currency=key[2], **finish(value))
                   for key, value in sorted(months.items())],
        'month_totals': [dict(month=key[0], currency=key[1], **finish(value)) for key,value in sorted(monthly_totals.items())],
        'month_sections': [dict(month=month, rows=[dict(supplier=k[1],currency=k[2],**finish(v)) for k,v in sorted(months.items()) if k[0]==month],
                              totals=[dict(currency=k[1],**finish(v)) for k,v in sorted(monthly_totals.items()) if k[0]==month])
                           for month in sorted({k[0] for k in months})],
    }


def supplier_summary(batches):
    result = []
    for batch in batches:
        rows = [row for row in batch.rows.all() if row.supplier_lines]
        gross = Decimal(0)
        net = Decimal(0)
        missing_gross = missing_net = lines = 0
        for row in rows:
            lines += len(row.supplier_lines)
            value = row_net(row, batch.vat, rounded=False)
            if value is None:
                missing_net += 1
            else:
                net += value
            for line in row.supplier_lines:
                if line.get('gross') in (None, ''):
                    missing_gross += 1
                else:
                    gross += Decimal(line['gross'])
        if rows:
            result.append(dict(batch=batch, lines=lines,
                gross=None if missing_gross else money(gross),
                net=None if missing_net else money(net),
                missing_net=missing_net, missing_gross=missing_gross))
    return result


@login_required
@never_cache
def statistics(request):
    if not can_view_statistics(request.user):
        raise PermissionDenied
    today = timezone.localdate()
    try:
        year = int(request.GET.get('year', today.year))
        if not 2000 <= year <= 9998:
            raise ValueError
    except (TypeError, ValueError):
        return HttpResponseBadRequest('Укажите год от 2000 до 9998.')
    active = Booking.objects.exclude(status__in=[Booking.Status.DRAFT,
        Booking.Status.CANCELLED, Booking.Status.NO_SHOW])
    basis=request.GET.get('booking_date_basis','pickup')
    if basis not in ('pickup','return'):
        return HttpResponseBadRequest('Выберите дату получения или возврата.')
    field=basis+'_datetime'
    year_bookings=active.filter(**{field+'__date__gte':date(year,1,1),field+'__date__lt':date(year+1,1,1)})
    confirmed=[Booking.Status.CONFIRMED,Booking.Status.ACTIVE,Booking.Status.COMPLETED,Booking.Status.SETTLED]
    counts=dict(count=Count('pk'),confirmed=Count('pk',filter=Q(status__in=confirmed)),
                waiting=Count('pk',filter=Q(status=Booking.Status.WAITING_CONFIRMATION)),
                changes=Count('pk',filter=Q(status=Booking.Status.UPDATE_PENDING)))
    supplier_counts=list(year_bookings.order_by('supplier__supplier_name','supplier_id').values('supplier_id','supplier__supplier_name').annotate(**counts))
    month_counts=list(year_bookings.annotate(month=TruncMonth(field)).values('month').annotate(count=Count('pk')).order_by('month'))
    from .group_statistics import top_rental_groups
    from config.rental_duration import calculate_rental_days
    group_records = []
    for booking in year_bookings.select_related('supplier', 'vehicle_group'):
        group = booking.vehicle_group
        legacy = booking.source_quote_snapshot.get('historical_import', {}).get('raw', {}).get('D', '')
        label = f'{group.group_name} ({group.group_code})' if group else str(legacy or '').strip()
        days = booking.rental_days
        if not days and booking.pickup_datetime and booking.return_datetime and booking.return_datetime > booking.pickup_datetime:
            days = calculate_rental_days(booking.pickup_datetime, booking.return_datetime)
        group_records.append(dict(supplier_id=booking.supplier_id, supplier=str(booking.supplier),
            group_key=group.pk if group else label, group=label, days=days,
            month=timezone.localtime(booking.pickup_datetime).month if booking.pickup_datetime else None))
    top_groups, group_statistics_missing = top_rental_groups(group_records)
    years={today.year,today.year+1,year}
    for date_field in ('pickup_datetime','return_datetime'):
        years.update(y for y in Booking.objects.order_by().values_list(date_field+'__year',flat=True).distinct() if y and 2000<=y<=9998)
    selected = active.filter(return_datetime__date__gte=date(year, 1, 1),
                             return_datetime__date__lt=date(year + 1, 1, 1))
    records = []
    for booking in selected.select_related('supplier'):
        returned = timezone.localtime(booking.return_datetime).date()
        records.append(dict(supplier=str(booking.supplier), currency=booking.currency,
            gross=booking.total_price_gross, return_date=returned, month=returned.month))
    missing = list(active.filter(return_datetime=None).select_related('supplier'))
    references = reference_rates(active.exclude(return_datetime=None)) if missing else {}
    by_booking, by_number = defaultdict(list), defaultdict(list)
    for row in Row.objects.select_related('reconciliation').filter(reconciliation__supplier_id__in={b.supplier_id for b in missing}):
        if row.own:
            by_booking[row.booking_id].append(row.own)
            by_number[(row.reconciliation.supplier_id, row.number)].append(row.own)
    recovered, unresolved = [], []
    for booking in missing:
        evidence = resolve_return(booking, by_booking[booking.pk] +
            by_number[(booking.supplier_id, booking.supplier_booking_number)], references)
        detail = dict(booking=booking, **evidence)
        if evidence['return_date'] is None:
            unresolved.append(detail)
        elif evidence['return_date'].year == year:
            recovered.append(detail)
    additional_records = [dict(supplier=str(item['booking'].supplier), currency=item['booking'].currency,
        gross=item['booking'].total_price_gross, return_date=item['return_date'], month=item['return_date'].month)
        for item in recovered]
    batches = Reconciliation.objects.filter(month__year=year).select_related('supplier').prefetch_related('rows')
    context = booking_summary(records + additional_records, today)
    context.update(recovered=recovered, unresolved=unresolved,
        documented=booking_summary(records, today)['totals'],
        unresolved_amounts=booking_summary([dict(supplier=str(item['booking'].supplier),
            currency=item['booking'].currency, gross=item['booking'].total_price_gross,
            return_date=today, month=today.month) for item in unresolved], today)['totals'])
    context.update(active_menu='statistics', year=year, updated=timezone.now(),
        year_choices=sorted(years),booking_date_basis=basis,booking_counts=year_bookings.aggregate(**counts),
        booking_suppliers=supplier_counts,booking_months=month_counts,
        top_groups=top_groups,group_statistics_missing=group_statistics_missing,
        reports=supplier_summary(batches), missing_dates=active.filter(return_datetime=None).count(),
        drafts=Booking.objects.filter(status=Booking.Status.DRAFT, return_datetime__year=year).count())
    return render(request, 'bookings/statistics.html', context)
