"""Count dated handovers and returns, without estimating dates from prices."""
import calendar
import re
from collections import defaultdict

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import never_cache

from suppliers.models import AnalyticsCity, Supplier, SupplierLocation
from .geography import Places, operation_time
from .models import Booking
from .statistics import can_view_statistics


class OperationsFilterForm(forms.Form):
    start = forms.DateField(label=_('С даты'), widget=forms.DateInput(attrs={'type': 'date'}))
    end = forms.DateField(label=_('По дату'), widget=forms.DateInput(attrs={'type': 'date'}))
    operation = forms.ChoiceField(label=_('Операции'), choices=[
        ('', _('Выдачи и возвраты')), ('pickup', _('Выдачи')), ('return', _('Возвраты'))], required=False)
    supplier = forms.ModelChoiceField(label=_('Фирма'), queryset=Supplier.objects.order_by('supplier_name'),
                                     required=False, empty_label=_('Все фирмы'))
    city = forms.ChoiceField(label=_('Город'), required=False)
    drafts = forms.BooleanField(label=_('Включить черновики'), required=False)

    def __init__(self, *args, cities, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['city'].choices = [('', _('Все города')), ('unknown', _('Не указано'))] + [
            (str(city.pk), city.label) for city in cities]

    def clean(self):
        data = super().clean()
        if data.get('start') and data.get('end') and data['start'] > data['end']:
            raise forms.ValidationError(_('Дата начала позже даты окончания.'))
        return data


def collect_events(bookings, places, start, end, *, operation='', city=''):
    events, undated = [], []
    sides = (operation,) if operation else ('pickup', 'return')
    for booking in bookings:
        for side in sides:
            place = places.resolve(booking, side)
            if city and place['city_key'] != city:
                continue
            time, from_source = operation_time(booking, side)
            raw = (booking.source_quote_snapshot or {}).get('historical_import', {}).get('raw', {})
            source_text = str(raw.get('B' if side == 'pickup' else 'C', ''))
            event = dict(booking=booking, side=side, time=time, from_source=from_source,
                         time_known=not from_source or bool(re.search(r'\d{1,2}:\d{2}', source_text)),
                         supplier_id=str(booking.supplier_id), supplier=str(booking.supplier),
                         city_key=place['city_key'],
                         city=str(_('Не указано')) if place['city_key']=='unknown' else place['city'],
                         place=place['place'])
            if time is None:
                undated.append(event)
            elif start <= time.date() <= end:
                events.append(event)
    return sorted(events, key=lambda e: (e['time'], e['supplier'], e['booking'].pk, e['side'])), undated


def summarize_events(events, *, daily=False):
    groups = defaultdict(lambda: dict(pickup=0, returns=0, total=0))
    for event in events:
        day = event['time'].date() if daily else None
        key = (day, event['supplier_id'], event['supplier'], event['city_key'], event['city'])
        row = groups[key]
        row['pickup' if event['side'] == 'pickup' else 'returns'] += 1
        row['total'] += 1
    return [dict(day=key[0], supplier_id=key[1], supplier=key[2], city_key=key[3], city=key[4], **counts)
            for key, counts in sorted(groups.items(), key=lambda pair: (pair[0][0] or '', pair[0][2], pair[0][4]))]


@login_required
@never_cache
def operations(request):
    if not can_view_statistics(request.user):
        raise PermissionDenied
    today = timezone.localdate()
    data = request.GET.copy()
    if not data:
        data.update(start=today.replace(day=1).isoformat(),
                    end=today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat())
    cities = list(AnalyticsCity.objects.all())
    form = OperationsFilterForm(data, cities=cities)
    events, undated, rows, daily = [], [], [], []
    totals = dict(pickup=0, returns=0, operations=0, bookings=0)
    if form.is_valid():
        filters = form.cleaned_data
        bookings = Booking.objects.exclude(status__in=[Booking.Status.CANCELLED, Booking.Status.NO_SHOW])
        if not filters['drafts']:
            bookings = bookings.exclude(status=Booking.Status.DRAFT)
        if filters['supplier']:
            bookings = bookings.filter(supplier=filters['supplier'])
        date_scope = Q(pk__in=[])
        for side in ((filters['operation'],) if filters['operation'] else ('pickup', 'return')):
            field = side + '_datetime'
            date_scope |= Q(**{field+'__date__range': (filters['start'], filters['end'])}) | Q(**{field+'__isnull': True})
        bookings = bookings.filter(date_scope)
        places = Places(cities, SupplierLocation.objects.filter(location_type='AIRPORT'))
        events, undated = collect_events(bookings.select_related('supplier', 'pickup_location', 'return_location'),
            places, filters['start'], filters['end'], operation=filters['operation'], city=filters['city'])
        rows, daily = summarize_events(events), summarize_events(events, daily=True)
        totals = dict(pickup=sum(e['side']=='pickup' for e in events),
                      returns=sum(e['side']=='return' for e in events), operations=len(events),
                      bookings=len({e['booking'].pk for e in events}))

        def detail_url(row, side):
            query = data.copy()
            for key, value in dict(supplier=row['supplier_id'], city=row['city_key'], operation=side, details='1').items():
                query[key] = value
            if row['day']:
                query['start'] = query['end'] = row['day'].isoformat()
            return reverse('quotes:operations') + '?' + query.urlencode() + '#operations-details'

        for row in rows + daily:
            row['pickup_url'] = detail_url(row, 'pickup')
            row['return_url'] = detail_url(row, 'return')
    return render(request, 'bookings/operations.html', dict(form=form, rows=rows, daily=daily,
        totals=totals, events=events, undated=undated, show_details=data.get('details')=='1', active_menu='statistics'))
