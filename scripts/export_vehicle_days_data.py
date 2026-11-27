"""Read-only aggregate export for 2026. No customer names, contacts or prices."""
import json
import re
from collections import defaultdict

from django.utils import timezone
from bookings.models import Booking
from bookings.geography import operation_time
from config.rental_duration import calculate_rental_days
from suppliers.models import VehicleGroup


def export_data(year=2026):
    def normalize(value):
        return ' '.join(re.findall(r'\w+', str(value or '').casefold()))

    groups=list(VehicleGroup.objects.select_related('supplier').prefetch_related('models'))
    aliases=defaultdict(set)
    by_id={group.pk:group for group in groups}
    rows={}

    def add_group(group):
        key=(group.supplier_id, str(group.pk))
        rows.setdefault(key,dict(group=group.group_name,code=group.group_code,
            supplier=str(group.supplier),examples=', '.join(str(m) for m in group.models.all() if m.is_active),
            days=0,bookings=0,winter=0,spring=0,summer=0,autumn=0,source='structured'))
        return key

    for group in groups:
        for alias in [group.group_name,group.group_code,str(group),f'{group.group_name} ({group.group_code})']:
            aliases[(group.supplier_id,normalize(alias))].add(group.pk)
        if group.is_active and group.show_in_offers and group.supplier.status=='ACTIVE':
            add_group(group)

    missing_date=missing_days=missing_group=unmatched=0
    for booking in Booking.objects.exclude(status__in=['DRAFT','CANCELLED','NO_SHOW']).select_related('supplier','vehicle_group'):
        pickup,_=operation_time(booking,'pickup')
        if not pickup:
            missing_date+=1
            continue
        if pickup.year!=year:
            continue
        days=booking.rental_days
        returned,_=operation_time(booking,'return')
        if not days and returned and returned>pickup:
            days=calculate_rental_days(pickup,returned)
        if not days or days<1:
            missing_days+=1
            continue
        group=by_id.get(booking.vehicle_group_id)
        raw=(booking.source_quote_snapshot or {}).get('historical_import',{}).get('raw',{})
        label=str(raw.get('D') or '').strip()
        if not group:
            matches=aliases.get((booking.supplier_id,normalize(label)),set())
            if len(matches)==1:
                group=by_id[next(iter(matches))]
        if group:
            key=add_group(group)
        elif label:
            unmatched+=1
            key=(booking.supplier_id,'raw:'+normalize(label))
            rows.setdefault(key,dict(group=label,code='',supplier=str(booking.supplier),examples='',
                days=0,bookings=0,winter=0,spring=0,summer=0,autumn=0,source='original import; models need checking'))
        else:
            missing_group+=1
            continue
        row=rows[key]
        row['days']+=int(days)
        row['bookings']+=1
        season=('winter' if pickup.month in (12,1,2) else 'spring' if pickup.month in (3,4,5)
                else 'summer' if pickup.month in (6,7,8) else 'autumn')
        row[season]+=int(days)
    return dict(year=year,created_at=timezone.now().isoformat(),basis='Full rental days by pickup year; future bookings included; cancelled/draft/no-show/archive excluded',
        rows=sorted(rows.values(),key=lambda row:(-row['days'],row['group'],row['supplier'])),
        quality=dict(missing_pickup_date_all_years=missing_date,missing_days_in_year=missing_days,
                     missing_group_in_year=missing_group,unmatched_original_group_bookings=unmatched))


if __name__=='__main__':
    print('VEHICLE_DAYS_EXPORT_BEGIN')
    print(json.dumps(export_data(),ensure_ascii=False,separators=(',',':')))
    print('VEHICLE_DAYS_EXPORT_END')
