"""Private, local-only calculator adapter. Works on an isolated SQLite copy."""
import os
import sys
import sqlite3
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]

def initialise():
    sys.path.insert(0,str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE','config.settings')
    from django.conf import settings
    config=settings.DATABASES['default']
    if config['ENGINE']!='django.db.backends.sqlite3':
        raise RuntimeError('Design calculator requires a local SQLite source. No remote database is accessed.')
    source=Path(config['NAME']).resolve()
    target=ROOT/'private_uploads'/'partner-design-prices'/'preview.sqlite3'
    target.parent.mkdir(parents=True,exist_ok=True)
    # Rebuild only our isolated copy. The source is opened read-only.
    with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as src:
        with sqlite3.connect(target) as dst:
            src.backup(dst)
    settings.DATABASES['default']={**config,'NAME':target}
    import django
    django.setup()
    from django.core.management import call_command
    with open(target.parent/'migration.log','w',encoding='utf-8') as log:
        call_command('migrate',interactive=False,verbosity=0,stdout=log,stderr=log)
    # The old local source predates the approved 14-category mapping. Restore the
    # owner's reviewed mapping ONLY into this private design copy, not the source.
    import json
    mapping=ROOT/'private_uploads'/'vehicle-category-mapping'/'20261113'/'corrected-mappings.json'
    if mapping.exists():
        from suppliers.models import FormVehicleCategory, VehicleGroup
        rows=json.loads(mapping.read_text(encoding='utf-8'))['mappings']
        for row in rows:
            category,_=FormVehicleCategory.objects.get_or_create(name=row['category'],defaults={'is_active':True})
            group=VehicleGroup.objects.filter(supplier__supplier_name=row['supplier'],group_code=row['group_code']).first()
            if group:group.form_categories.add(category)
    return source.stat().st_mtime

def calculate(payload):
    from django.core.exceptions import ValidationError
    from partners.services import calculate_options
    from quotes.forms import FirstInquiryForm
    from suppliers.models import OfferCity
    cities={v for v,label in FirstInquiryForm.CITY_CHOICES if v and v!='OTHER'}
    cities.update(OfferCity.objects.filter(is_active=True).values_list('name',flat=True))
    for side in ['pickup','return']:
        if payload.get(side+'City') not in cities:
            raise ValueError('יש לבחור עיר מהרשימה; מסלול מיוחד מועבר לעידן.')
        if payload.get(side+'Service') not in {'AIRPORT','ADDRESS','CITY_BRANCH'}:
            raise ValueError('יש לבחור מקום קבלה והחזרה.')
    zone=ZoneInfo('Europe/Warsaw')
    def stamp(side):
        date=datetime.strptime(payload[side+'Date'],'%d.%m.%Y')
        clock=payload[side+'Time']
        if clock not in {v for v,label in FirstInquiryForm.TIME_CHOICES}:raise ValueError('נא לבחור שעה במרווחים של חצי שעה.')
        hour,minute=map(int,clock.split(':'))
        return date.replace(hour=hour,minute=minute,tzinfo=zone).isoformat()
    data=dict(pickup_datetime=stamp('pickup'),return_datetime=stamp('return'),
              pickup_city=payload['pickupCity'],return_city=payload['returnCity'],
              pickup_service=payload['pickupService'],return_service=payload['returnService'],
              pickup_address=payload.get('pickupAddress',''),return_address=payload.get('returnAddress',''),
              cross_border=bool(payload.get('crossBorder')),drivers=1,
              seats=int(payload.get('seats') or 0),gps=bool(payload.get('gps')),chains=bool(payload.get('chains')))
    if payload.get('driverOk') is False or payload.get('creditOk') is False:
        raise ValueError('תנאי נהג / כרטיס מיוחדים דורשים בדיקה של עידן בתצוגה זו.')
    if data['seats']<0 or data['seats']>9:raise ValueError('נא לבדוק את מספר הכיסאות.')
    rows=calculate_options(data)
    result=[]
    for group_id,row in rows.items():
        if not row:continue
        group=row['group']
        desired={'אוטומטית':'AUTOMATIC','ידנית':'MANUAL'}.get(payload.get('gear'))
        if desired and group.transmission!=desired:continue
        result.append(dict(id=str(group_id),company=row['supplier'].supplier_name,
            group=group.customer_name_he or group.group_name,models=row['models'] or '',
            total=str(row['total']),currency=row['currency'],deposit=str(row['deposit_amount']),
            depositCurrency=row['deposit_currency'],categories=list(group.form_categories.filter(is_active=True).values_list('name',flat=True))))
    return dict(options=result,source='local_price_lists',message='מחושב לפי המחירונים בבסיס המקומי. אינו אישור זמינות או אימות למחירוני השרת.')
