"""Geography and pickup workload, read-only and independent of Excel exports."""
import calendar
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseBadRequest
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from suppliers.models import AnalyticsCity, SupplierLocation
from .models import Booking
from .statistics import can_view_statistics

UNKNOWN='Не указано'
SERVICE_LABELS={'AIRPORT':'Аэропорт','BRANCH':'Офис','CITY_BRANCH':'Офис',
                'ADDRESS':'Адрес / доставка','ADDRESS_DELIVERY':'Адрес / доставка',
                'HOTEL_DELIVERY':'Гостиница','HOTEL':'Гостиница','OTHER':'Место не уточнено'}


def fold(text):
    text=str(text or '').casefold().replace('ł','l')
    text=''.join(c for c in unicodedata.normalize('NFKD',text) if not unicodedata.combining(c))
    return ' '.join(re.findall(r'\w+',text))


def pickup_time(booking):
    if booking.pickup_datetime:
        return timezone.localtime(booking.pickup_datetime), False
    raw=(booking.source_quote_snapshot or {}).get('historical_import',{}).get('raw',{})
    text=str(raw.get('B','')).strip().lstrip("`'")
    match=re.match(r'(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]+\s*(\d{2,4})(?!\d)(?:\s*[,;]?\s*(\d{1,2}):(\d{2}))?',text)
    if match:
        d,m,y,h,minute=match.groups()
        y=int(y)
        try:
            return timezone.make_aware(datetime(y+2000 if y<100 else y,int(m),int(d),int(h or 0),int(minute or 0))),True
        except ValueError:
            pass
    return None,False


class Places:
    def __init__(self,cities,airports=()):
        self.cities=list(cities)
        self.aliases=defaultdict(set)
        self.by_id={str(city.pk):city for city in self.cities}
        for city in self.cities:
            for value in [city.name,city.label,*(city.aliases if isinstance(city.aliases,list) else [])]:
                if fold(value):
                    self.aliases[fold(value)].add(str(city.pk))
        self.patterns=[(alias,re.compile(r'(?<!\w)'+re.escape(alias)+r'(?!\w)'),ids)
                       for alias,ids in self.aliases.items()]
        self.airports=list(airports)

    def find(self,text,exact=False):
        text=fold(text)
        if not text:
            return None
        if exact:
            ids=self.aliases.get(text,set())
            return self.by_id[next(iter(ids))] if len(ids)==1 else None
        matches=[]
        for alias,pattern,ids in self.patterns:
            if pattern.search(text):
                matches.append((alias,ids))
        if not matches:
            return None
        # Prefer a specific name (e.g. Kraków Balice) over contained aliases.
        longest=max(len(alias) for alias,ids in matches)
        longest_aliases=[alias for alias,ids in matches if len(alias)==longest]
        ids=set().union(*(ids for alias,ids in matches if len(alias)==longest))
        if any(not other_ids.issubset(ids) and not any(alias in long for long in longest_aliases)
               for alias,other_ids in matches):
            return None
        return self.by_id[next(iter(ids))] if len(ids)==1 else None

    def resolve(self,booking,side):
        snapshot=booking.source_quote_snapshot or {}
        request=snapshot.get('request',{})
        raw=snapshot.get('historical_import',{}).get('raw',{})
        location=getattr(booking,side+'_location',None)
        explicit=request.get(side+'_city','')
        text=(getattr(booking,side+'_location_text','') or getattr(booking,side+'_address','')
              or request.get(side+'_address','') or raw.get('B' if side=='pickup' else 'C',''))
        city=self.find(explicit,exact=True) if explicit and explicit!='OTHER' else None
        country=city.country if city else ''
        source='Город в заказе' if city else ''
        if not city and explicit=='OTHER':
            city=self.find(getattr(booking,side+'_address','') or request.get(side+'_address','') or text)
            if city:
                country=city.country
                source='Город найден в адресе другого места'
        if not city and location:
            city=self.find(location.city,exact=True)
            country=location.country
            source='Место из справочника'
        if not city:
            city=self.find(text)
            if city:
                country=city.country
                source='Город найден в сохранённом тексте'
        foreign=None if not country else fold(country) not in ('poland','polska','pl','польша','פולין')
        service=request.get(side+'_service') or (location.location_type if location else '')
        if service not in SERVICE_LABELS or service=='OTHER':
            if re.search(r'hotel|מלון|гостиниц|отел',str(text),re.I):
                service='HOTEL'
            elif re.search(r'airport|airpport|lotnisko|аэропорт|נמל תעופה',str(text),re.I):
                service='AIRPORT'
            else:
                service='OTHER'
        label=city.label if city else (location.city if location and location.city else UNKNOWN)
        key=str(city.pk) if city else 'unknown'
        airport=(location.airport_code if location and service=='AIRPORT'
                 and city and self.find(location.city,exact=True)==city else '')
        if not airport and city and service=='AIRPORT':
            codes={a.airport_code for a in self.airports if a.airport_code and self.find(a.city,exact=True)==city}
            found={code for code in codes if re.search(r'\b'+re.escape(code)+r'\b',str(text),re.I)}
            if len(found)==1:
                airport=found.pop()
            elif len(codes)==1:
                airport=codes.pop()
        if service=='AIRPORT':
            place=f'{label} · Аэропорт'+(f' {airport}' if airport else ' (не уточнён)')
        else:
            detail=(getattr(booking,'hotel_name' if side=='pickup' else 'return_hotel_name','')
                    or (getattr(booking,side+'_address','') or request.get(side+'_address','')
                        if service in ('ADDRESS','ADDRESS_DELIVERY','HOTEL','HOTEL_DELIVERY') else '')
                    or (location.location_name if location and service not in ('ADDRESS','ADDRESS_DELIVERY','HOTEL') else '') or str(text))
            detail=re.sub(r'^\s*\d{1,2}[/.-]\d{1,2}[/.-]+\d{2,4}\s*[,;]?\s*(?:\d{1,2}:\d{2})?\s*[,;]?\s*','',detail)
            place=f'{label} · {SERVICE_LABELS[service]}'+(f' · {detail}' if detail else '')
        return dict(city=label,city_key=key,country=country or UNKNOWN,foreign=foreign,
                    place=place,place_key=fold(place),source=source or 'Не определено')


def cross_border(booking):
    request=(booking.source_quote_snapshot or {}).get('request',{})
    if request.get('cross_border_requested') is True:
        return True
    if any(e.extra.extra_code=='CROSS_BORDER' for e in booking.extras.all()):
        return True
    if request.get('cross_border_requested') is False:
        return False
    raw=(booking.source_quote_snapshot or {}).get('historical_import',{}).get('raw',{})
    services=str(raw.get('F','')).strip()
    if not services:
        return None
    if re.search(r'(?:no|without|not requested)\s+(?:cross[ -]?border|border crossing|travel abroad)',services,re.I):
        return False
    return bool(re.search(r'cross[ -]?border|border crossing|travel abroad|выезд за границ|יציאה לחו',services,re.I))


def analyze(records):
    cities=Counter()
    counts=Counter()
    for record in records:
        cities[(record['pickup']['city_key'],record['pickup']['city'])]+=1
        start,end=record['pickup']['foreign'],record['return']['foreign']
        counts['foreign_pickup']+=start is True
        counts['foreign_return']+=end is True
        counts['foreign_either']+=start is True or end is True
        counts['unknown_country']+=start is None or end is None
        counts['cross_border']+=record['cross_border'] is True
        counts['unknown_cross_border']+=record['cross_border'] is None
        counts['drafts']+=record['draft']
    return dict(counts=counts,cities=[dict(key=key,label=label,count=count)
        for (key,label),count in sorted(cities.items(),key=lambda item:(-item[1],item[0][1]))],total=len(records))


def month_grid(records,month,today):
    daily=defaultdict(list)
    for record in records:
        day=record['time'].date() if record['time'] else None
        if day and (day.year,day.month)==(month.year,month.month) and day>=today:
            daily[day].append(record)
    weeks=[]
    for week in calendar.Calendar(firstweekday=0).monthdatescalendar(month.year,month.month):
        cells=[]
        for day in week:
            items=daily[day]
            groups=Counter((r['supplier'],r['pickup']['place']) for r in items)
            cells.append(dict(date=day,current=day.month==month.month,today=day==today,
                count=sum(not r['draft'] for r in items),drafts=sum(r['draft'] for r in items),
                groups=[dict(supplier=firm,place=place,count=count) for (firm,place),count in sorted(groups.items())]))
        weeks.append(cells)
    return weeks


@login_required
@never_cache
def geography(request):
    if not can_view_statistics(request.user):
        raise PermissionDenied
    today=timezone.localdate()
    try:
        year=int(request.GET.get('year',today.year))
        month=date.fromisoformat(request.GET.get('month',today.strftime('%Y-%m'))+'-01')
        day=date.fromisoformat(request.GET['day']) if request.GET.get('day') else None
        if not 2000<=year<=2100 or not 2000<=month.year<=2100:
            raise ValueError
    except (ValueError,TypeError):
        return HttpResponseBadRequest('Проверьте год, месяц и дату.')
    show_drafts=request.GET.get('drafts')=='1'
    places=Places(AnalyticsCity.objects.all(),SupplierLocation.objects.filter(location_type='AIRPORT'))
    all_records=[]
    bookings=Booking.objects.exclude(status__in=['CANCELLED','NO_SHOW']).select_related(
        'supplier','pickup_location','return_location').prefetch_related('extras__extra')
    suppliers={}
    for booking in bookings:
        time,source_date=pickup_time(booking)
        suppliers[str(booking.supplier_id)]=str(booking.supplier)
        all_records.append(dict(booking=booking,time=time,date_from_source=source_date,
            time_known=not source_date or bool(re.search(r'\d{1,2}:\d{2}',str(
                (booking.source_quote_snapshot or {}).get('historical_import',{}).get('raw',{}).get('B','')))),
            supplier=str(booking.supplier),supplier_id=str(booking.supplier_id),
            pickup=places.resolve(booking,'pickup'),return_=places.resolve(booking,'return'),
            cross_border=cross_border(booking),draft=booking.status=='DRAFT'))
    for record in all_records:
        record['return']=record.pop('return_')
    supplier=request.GET.get('supplier','')
    city=request.GET.get('city','')
    location=request.GET.get('location','')
    filtered=[r for r in all_records if (not supplier or r['supplier_id']==supplier)
              and (not city or r['pickup']['city_key']==city)
              and (show_drafts or not r['draft'])]
    yearly=[r for r in filtered if r['time'] and r['time'].year==year]
    calendar_records=[r for r in filtered if r['booking'].status not in ('COMPLETED','SETTLED','ACTIVE')]
    locations=sorted({r['pickup']['place'] for r in calendar_records if r['time'] and r['time'].date()>=today})
    if location:
        calendar_records=[r for r in calendar_records if r['pickup']['place']==location]
    summary=analyze(yearly)
    params=dict(year=year,month=month.strftime('%Y-%m'))
    if supplier: params['supplier']=supplier
    if city: params['city']=city
    if show_drafts: params['drafts']='1'
    if location: params['location']=location
    def url(**updates):
        return reverse('quotes:geography')+'?'+urlencode({**params,**updates})
    weeks=month_grid(calendar_records,month,today)
    for week in weeks:
        for cell in week:
            cell['url']=url(day=cell['date'].isoformat())+'#pickup-details'
    for item in summary['cities']:
        item['url']=url(metric='all',detail_city=item['key'])+'#analysis-details'
    metrics=[('foreign_pickup','Получение вне Польши'),('foreign_return','Возврат вне Польши'),
        ('foreign_either','Получение или возврат вне Польши'),('cross_border','Запрошен выезд за границу'),
        ('unknown_country','Страна получения или возврата неизвестна'),('unknown_cross_border','Запрос выезда не указан')]
    cards=[dict(key=key,label=label,count=summary['counts'][key],url=url(metric=key)+'#analysis-details') for key,label in metrics]
    metric=request.GET.get('metric','')
    detail_city=request.GET.get('detail_city','')
    def matches(record):
        if detail_city and record['pickup']['city_key']!=detail_city:
            return False
        flags=dict(foreign_pickup=record['pickup']['foreign'] is True,
            foreign_return=record['return']['foreign'] is True,
            foreign_either=record['pickup']['foreign'] is True or record['return']['foreign'] is True,
            cross_border=record['cross_border'] is True,
            unknown_country=record['pickup']['foreign'] is None or record['return']['foreign'] is None,
            unknown_cross_border=record['cross_border'] is None)
        return metric=='all' or flags.get(metric,False)
    details=([r for r in filtered if r['time'] is None] if metric=='unknown_date' else
             [r for r in yearly if matches(r)] if metric else [])
    day_records=[r for r in calendar_records if r['time'] and r['time'].date()==day and day>=today] if day else []
    day_records.sort(key=lambda r:(r['time'],r['supplier'],r['booking'].pk))
    groups=Counter((r['supplier'],r['pickup']['place']) for r in day_records)
    prev=(month-timedelta(days=1)).replace(day=1)
    following=(month.replace(day=28)+timedelta(days=4)).replace(day=1)
    return render(request,'bookings/geography.html',dict(active_menu='statistics',year=year,month=month,updated=timezone.now(),
        show_drafts=show_drafts,supplier=supplier,city=city,location=location,locations=locations,
        supplier_choices=sorted(suppliers.items(),key=lambda v:v[1]),
        city_choices=sorted({(r['pickup']['city_key'],r['pickup']['city']) for r in all_records},key=lambda v:v[1]),
        summary=summary,cards=cards,weeks=weeks,previous_url=url(month=prev.strftime('%Y-%m')),
        next_url=url(month=following.strftime('%Y-%m')),day=day,day_records=day_records,
        day_groups=[dict(supplier=k[0],place=k[1],count=v) for k,v in sorted(groups.items())],
        metric=metric,details=details,unknown_dates=sum(r['time'] is None for r in filtered),
        unknown_dates_url=url(metric='unknown_date')+'#analysis-details',
        future_drafts=sum(r['draft'] and r['time'] is not None and r['time'].date()>=today for r in all_records)))
