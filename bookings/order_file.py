"""Reviewed Excel exchange. No email sending, deletions, repricing or payments."""
import hashlib
import json
import re
import sqlite3
import subprocess
from collections import defaultdict
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import Path
from uuid import uuid4
from zipfile import ZipFile, BadZipFile

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.worksheet.datavalidation import DataValidation

from customers.models import Customer
from reconciliation.models import Row
from reconciliation.parsing import identifier
from suppliers.models import Supplier
from .models import Booking, BookingHistoryEvent, OrderFileSync

FIELDS = ('firm','name','pickup','return','group','gross','services','phone','email','number','status','period')
HEADINGS = ['Фирма','Клиент / водители','Получение — исходная запись','Возврат — исходная запись',
    'Класс автомобиля','Сумма с НДС','Дополнительные услуги','Телефон','Email','Номер поставщика',
    'Исходный J','Исходный K','Исходный L','Исходный M','Исходный N','Статус','Учтён за период',
    'Проверить / примечания','Дата начала для сортировки','Исходный файл','Исходный лист',
    'Исходная строка','ID строки источника','ID заказа программы','Валюта']
COLUMNS = dict(zip(FIELDS, [0,1,2,3,4,5,6,7,8,9,15,16]))


def normalize(value):
    return ' '.join(str(value or '').replace('\u200b','').split())


def trip_date(value):
    value = normalize(value).lstrip("`'")
    match = re.match(r'(\d{1,2})\s*[/.-]\s*(\d{1,2})\s*[/.-]+\s*(\d{2,4})(?!\d)(?:\s*[,;]?\s*(\d{1,2}):(\d{2}))?', value)
    if not match:
        return None
    day, month, year, hour, minute = match.groups()
    year=int(year)
    try:
        return timezone.make_aware(datetime(year+2000 if year<100 else year,int(month),int(day),int(hour or 0),int(minute or 0)))
    except ValueError:
        return None


def merge_fields(base, excel, database):
    merged, conflicts = {}, []
    for key in FIELDS:
        left,right=excel.get(key,''),database.get(key,'')
        if left==right:
            merged[key]=left
        elif base is not None and left==base.get(key,''):
            merged[key]=right
        elif base is not None and right==base.get(key,''):
            merged[key]=left
        elif base is None and (not left or not right):
            merged[key]=left or right
        else:
            merged[key]=left
            conflicts.append(key)
    return merged,conflicts


def booking_values(booking):
    snapshot=booking.source_quote_snapshot or {}
    raw=snapshot.get('historical_import',{}).get('raw',{})
    services=raw.get('F') or ' + '.join(e.supplier_visible_name+' x '+str(e.quantity) for e in booking.extras.all())
    values=dict(firm=booking.supplier.working_file_code or booking.supplier.supplier_code,
        name=booking.customer_name_snapshot or str(booking.customer),
        group=str(booking.vehicle_group) if booking.vehicle_group else raw.get('D',''),
        gross=format(booking.total_price_gross,'.2f'), services=services,
        phone=' // '.join(filter(None,[booking.customer_phone_1_snapshot,booking.customer_phone_2_snapshot,booking.customer_phone_3_snapshot])),
        email=booking.customer_email_snapshot, number=identifier(booking.supplier_booking_number),
        status='Отменён' if booking.status=='CANCELLED' else 'Учтён' if booking.status in ('COMPLETED','SETTLED') else 'Обычный',
        period=snapshot.get('working_file_period',''))
    # Historical imports often split a full driver label and clean punctuation
    # in phones. Preserve the original label when it still contains the saved
    # primary name, and phone spelling only when the digits are identical.
    original_name=normalize(raw.get('A',''))
    primary=normalize(values['name'])
    if original_name and primary and primary.casefold() in original_name.casefold():
        values['name']=original_name
    original_phone=normalize(raw.get('G',''))
    if original_phone and re.sub(r'\D','',original_phone)==re.sub(r'\D','',values['phone']):
        values['phone']=original_phone
    for side,col in [('pickup','B'),('return','C')]:
        dt=getattr(booking,side+'_datetime')
        location=getattr(booking,side+'_location_text') or getattr(booking,side+'_address')
        # Keep the complete original address/flight text when it represents the saved date.
        original=raw.get(col,'')
        parsed=trip_date(original)
        values[side]=original if original and (dt is None or parsed==dt) else (
            timezone.localtime(dt).strftime('%d/%m/%Y, %H:%M')+', '+location if dt else original)
    return {k:normalize(v) for k,v in values.items()}


def database_state(lock=False):
    query=Booking.objects.select_related('supplier','customer','vehicle_group').prefetch_related('extras')
    if lock:
        query=query.select_for_update(of=('self',))
    bookings={str(b.pk):b for b in query}
    state={pk:booking_values(b) for pk,b in bookings.items()}
    reports=defaultdict(set)
    latest={}
    for row in Row.objects.select_related('reconciliation').order_by('reconciliation__month','pk'):
        key=(row.reconciliation.supplier_id,identifier(row.number))
        latest[key]=row.decision
        if row.supplier_lines and row.decision not in ('CANCEL','CARRY','EXCLUDE','PREVIOUS'):
            reports[key].add(row.reconciliation.month.strftime('%m.%Y'))
    for pk,booking in bookings.items():
        key=(booking.supplier_id,identifier(booking.supplier_booking_number))
        if reports[key] and latest.get(key)!='CARRY' and state[pk]['status']!='Отменён':
            state[pk]['status']='Учтён'
            state[pk]['period']='; '.join(sorted(reports[key]))
    fingerprint={pk:{'values':value,'updated':bookings[pk].updated_at.isoformat(),
                     'status':bookings[pk].status} for pk,value in state.items()}
    digest=hashlib.sha256(json.dumps(fingerprint,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return bookings,state,digest


def read_file(content):
    if len(content)>15*1024*1024:
        raise ValidationError('Файл больше 15 MB.')
    try:
        with ZipFile(BytesIO(content)) as archive:
            if sum(i.file_size for i in archive.infolist())>120*1024*1024:
                raise ValidationError('Слишком большой распакованный файл.')
        book=load_workbook(BytesIO(content),data_only=False)
    except (BadZipFile,ValueError,KeyError) as exc:
        raise ValidationError('Не удалось прочитать Excel.') from exc
    if 'Заказы' not in book.sheetnames:
        raise ValidationError('Нужен общий файл с листом «Заказы».')
    rows=[]
    for sheet in [s for s in book if s.title in ('Заказы','Архив до 2026')]:
        if sheet.max_row>30000 or sheet.max_column>40:
            raise ValidationError('Превышен размер листа.')
        if any(normalize(sheet.cell(1,i+1).value)!=HEADINGS[i] for i in range(10) if i!=5):
            raise ValidationError('Заголовки общего файла изменены. Используйте файл, скачанный из программы.')
        for line,cells in enumerate(sheet.iter_rows(min_row=2),2):
            values=[c.value for c in cells]
            if not any(v is not None for v in values):
                continue
            if any(c.data_type=='f' for c in cells):
                raise ValidationError(f'{sheet.title}, строка {line}: формулы в заказах не поддерживаются.')
            values=(values+[None]*25)[:25]
            values=[v.isoformat() if isinstance(v,datetime) else v for v in values]
            item={key:normalize(values[col]) for key,col in COLUMNS.items()}
            item['number']=identifier(item['number'])
            if item['gross']:
                try:
                    value=Decimal(item['gross'].replace(',','.').replace(' ',''))
                    if not value.is_finite() or value<0 or value>Decimal('9999999999.99'):
                        raise InvalidOperation
                    item['gross']=format(value.quantize(Decimal('.01')),'.2f')
                except InvalidOperation as exc:
                    raise ValidationError(f'Строка {line}: неверная сумма.') from exc
            rows.append({'values':item,'raw':values,'booking':normalize(values[23]),
                'currency':normalize(values[24]) or 'PLN',
                'key':normalize(values[22]) or 'excel:'+str(uuid4()),'source':f'{sheet.title}:{line}'})
    baseline={}
    if '_Синхронизация' in book and book['_Синхронизация']['A1'].value:
        run_id=book['_Синхронизация']['A1'].value
        try:
            previous=OrderFileSync.objects.filter(pk=run_id,applied=True).first()
        except (ValidationError,ValueError):
            previous=None
        if previous is None:
            raise ValidationError('Не найдена история этого файла в этой базе. Обратитесь к владельцу программы.')
        baseline=previous.baseline
    book.close()
    return rows,baseline


def make_plan(rows,baseline,bookings,state):
    number_index=defaultdict(list)
    for pk,item in state.items():
        if item['number']:
            number_index[(item['firm'],item['number'])].append(pk)
    aliases={s.working_file_code or s.supplier_code:s for s in Supplier.objects.all()}
    duplicate=defaultdict(int)
    for row in rows:
        if row['values']['number']:
            duplicate[(row['values']['firm'],row['values']['number'])]+=1
    plan=[]
    seen=set()
    for row in rows:
        excel=row['values']
        key=(excel['firm'],excel['number'])
        matches=number_index.get(key,[]) if key[1] else []
        pk=row['booking'] or (matches[0] if len(matches)==1 else '')
        errors=[]
        if row['booking'] and pk not in state:
            errors.append('Карточка удалена или скрыта; автоматическое восстановление запрещено')
        if len(matches)>1 or duplicate[key]>1 and key[1] or pk and pk in seen:
            errors.append('Повтор номера или карточки')
        if pk:
            seen.add(pk)
        if excel['firm'] not in aliases:
            errors.append('Неизвестная фирма: настройте её код в справочнике')
        merged,fields=merge_fields(baseline.get(pk),excel,state[pk]) if pk in state else (excel.copy(),[])
        if fields:
            errors.append('Различаются поля: '+', '.join(fields))
        if pk in state and excel['firm']!=state[pk]['firm']:
            errors.append('Смену фирмы выполняйте через «Изменить заказ»')
        if row['currency'] != (bookings[pk].currency if pk in bookings else aliases[excel['firm']].default_currency if excel['firm'] in aliases else row['currency']):
            errors.append('Валюта не совпадает с карточкой или фирмой')
        if not pk:
            if not excel['number'] or not excel['name']:
                errors.append('Для нового заказа нужны номер фирмы и имя')
            possible_unnumbered = excel['firm'] in aliases and any(
                b.supplier_id==aliases[excel['firm']].pk and not b.supplier_booking_number
                and normalize(b.customer_email_snapshot)==excel['email'] and excel['email']
                and b.pickup_datetime and b.pickup_datetime==trip_date(excel['pickup']) for b in bookings.values())
            if not matches and possible_unnumbered:
                errors.append('Есть карточка без номера с тем же email и датой; сначала проверьте дубль')
        if not merged.get('gross'):
            errors.append('Не указана сумма')
        if len(merged.get('name',''))>200 or len(merged.get('email',''))>254:
            errors.append('Слишком длинное имя или email')
        if merged.get('status') not in ('Обычный','Учтён','Отменён'):
            errors.append('Неизвестный статус')
        phones=[p.strip() for p in re.split(r'//|\|',merged.get('phone','')) if p.strip()]
        if len(phones)>3 or any(len(p)>30 for p in phones):
            errors.append('Разделите телефоны знаком //; не более трёх телефонов по 30 символов')
        if merged.get('email'):
            from django.core.validators import validate_email
            try:
                validate_email(merged['email'])
            except ValidationError:
                errors.append('Некорректный email')
        for side in ('pickup','return'):
            if merged.get(side) and not trip_date(merged[side]):
                # Preserve old malformed text if unchanged; do not pretend it is a date.
                if not pk or merged[side]!=state.get(pk,{}).get(side):
                    errors.append('Не распознана дата: '+side)
        start,end=trip_date(merged.get('pickup')),trip_date(merged.get('return'))
        if start and end and end<start:
            if not pk or any(merged.get(k)!=state.get(pk,{}).get(k) for k in ('pickup','return')):
                errors.append('Возврат раньше получения')
        if pk in state:
            if any(merged.get(k)!=state[pk][k] for k in ('group','services')):
                errors.append('Класс или дополнительные услуги: измените их в карточке программы, затем повторите сверку')
        action='conflict' if errors else 'update' if pk else 'create'
        if action=='update' and merged==state[pk]:
            action='same'
        plan.append({**row,'booking':pk,'merged':merged,'errors':errors,'action':action,
                     'database':state.get(pk,{})})
    return plan


def workbook_bytes(rows,run_id=None):
    book=Workbook()
    sheet=book.active
    sheet.title='Заказы'
    sheet.append(HEADINGS)
    def sortkey(row):
        day=trip_date(row['values'].get('pickup'))
        return (day is None,day.isoformat() if day else '',row['values'].get('firm',''),row['key'])
    for item in sorted(rows,key=sortkey):
        raw=(item.get('raw',[])+[None]*25)[:25]
        for field,col in COLUMNS.items():
            raw[col]=item['values'].get(field,'')
        if raw[5]:
            raw[5]=float(Decimal(raw[5]))
        raw[18]=timezone.localtime(trip_date(raw[2])).replace(tzinfo=None) if trip_date(raw[2]) else None
        raw[22]=item['key']
        raw[23]=item.get('booking','')
        raw[24]=item.get('currency','PLN')
        raw[17]=item.get('note',raw[17])
        sheet.append(raw)
        # Excel must not interpret customer text as a formula.
        for column in range(1,len(HEADINGS)+1):
            cell=sheet.cell(sheet._current_row,column)
            if isinstance(cell.value,str):
                cell.data_type='s'
    sheet.freeze_panes='C2'
    sheet.auto_filter.ref=sheet.dimensions
    widths=[8,32,48,48,27,18,65,34,34,22]+[16]*5+[15,20,65,22,30,18,15,28,20,12]
    for i,width in enumerate(widths,1):
        from openpyxl.utils import get_column_letter
        sheet.column_dimensions[get_column_letter(i)].width=width
    for col in ['K','L','M','N','O','S','T','U','V','W','X']:
        sheet.column_dimensions[col].hidden=True
    for cell in sheet[1]:
        cell.font=Font(bold=True,color='FFFFFF')
        cell.fill=PatternFill('solid',fgColor='17365D')
    sheet.row_dimensions[1].height=34
    for i,row in enumerate(sheet.iter_rows(min_row=2),2):
        sheet.row_dimensions[i].height=55
        for cell in row:
            cell.alignment=Alignment(vertical='top',wrap_text=True)
        row[5].number_format='#,##0.00'
        row[18].number_format='dd-mm-yyyy hh:mm'
    for label,color in [('Учтён','FFF2CC'),('Отменён','FFC7CE')]:
        sheet.conditional_formatting.add(f'A2:Y{max(2,sheet.max_row+1000)}',FormulaRule(
            formula=[f'$P2="{label}"'],fill=PatternFill('solid',fgColor=color)))
    valid=DataValidation(type='list',formula1='"Обычный,Отменён,Учтён"')
    sheet.add_data_validation(valid)
    valid.add(f'P2:P{sheet.max_row+1000}')
    guide=book.create_sheet('Инструкция')
    for text in ['Синхронизация выполняется только по команде владельца. Файл — копия, а не замена полной резервной копии базы.',
        'После ручных изменений загрузите Excel в программу, проверьте расхождения и подтвердите применение.',
        'Красный — отменён; жёлтый — учтён (реализованная завершённая аренда), не подтверждение банковской оплаты.',
        'Не редактируйте скрытый ID заказа программы. Смена фирмы, класса и состава услуг требует проверки в карточке.',
        'Программа не удаляет заказы по отсутствию строки в файле и не отправляет письма при синхронизации.',
        'Предыдущие копии хранятся в программе. На сервере загрузите файл с компьютера, после проверки скачайте обновлённый.',
        'Коды фирм настраиваются в справочнике поставщиков. Валюта указана в отдельном столбце.',
        'Примечание «Не синхронизировано» означает, что строка сохранена в Excel, но её изменения не применены к базе.']:
        guide.append([text])
    guide.column_dimensions['A'].width=115
    for row in guide:
        row[0].alignment=Alignment(wrap_text=True,vertical='top')
        guide.row_dimensions[row[0].row].height=40
    meta=book.create_sheet('_Синхронизация')
    meta['A1']=str(run_id) if run_id else ''
    meta.sheet_state='veryHidden'
    output=BytesIO()
    book.save(output)
    return output.getvalue()


def output_rows(plan,bookings,state):
    result=[]
    represented=set()
    for item in plan:
        pk=item['booking']
        row={**item,'values':item['values'].copy()}
        if item['action']=='conflict':
            row['note']='Не синхронизировано: '+'; '.join(item['errors'])
        elif pk in state:
            row['values']=state[pk]
        if pk:
            represented.add(pk)
        result.append(row)
    for pk,values in state.items():
        if pk not in represented:
            result.append({'key':'booking:'+pk,'booking':pk,'values':values,'currency':bookings[pk].currency})
    return result


def create_snapshot(destination):
    bookings,state,_=database_state()
    previous=OrderFileSync.objects.filter(applied=True).exclude(result='').first()
    retained=[]
    if previous:
        with previous.result.open('rb') as handle:
            retained,_=read_file(handle.read())
    plan=[{**r,'action':'same' if r['booking'] in state else 'conflict',
           'errors':['Строка сохранена из последнего Excel; не связана с действующей карточкой']} for r in retained]
    Path(destination).write_bytes(workbook_bytes(output_rows(plan,bookings,state)))


def database_backup():
    directory=Path(settings.MEDIA_ROOT)/'order-sync'/'database-backups'
    directory.mkdir(parents=True,exist_ok=True)
    target=directory/str(uuid4())
    database=settings.DATABASES['default']
    if database['ENGINE']=='django.db.backends.sqlite3':
        target=target.with_suffix('.sqlite3')
        with sqlite3.connect(database['NAME']) as source,sqlite3.connect(target) as dest:
            source.backup(dest)
            if dest.execute('PRAGMA integrity_check').fetchone()[0]!='ok':
                raise ValidationError('Не прошла проверка резервной копии базы.')
    elif database['ENGINE']=='django.db.backends.postgresql':
        from scripts.render_backup import database_environment
        target=target.with_suffix('.dump')
        result=subprocess.run(['pg_dump','--format=custom','--no-owner','--no-acl','--file',str(target)],
            env=database_environment(database),capture_output=True,timeout=120)
        if result.returncode:
            raise ValidationError('Не удалось сохранить резервную копию базы; синхронизация остановлена.')
        result=subprocess.run(['pg_restore','--list',str(target)],capture_output=True,timeout=30)
        if result.returncode:
            raise ValidationError('Не прошла проверка резервной копии базы.')
    else:
        raise ValidationError('Резервное копирование этой базы не настроено.')
    target.chmod(0o600)
    return str(target)


def prepare_sync(actor,content=None):
    bookings,state,digest=database_state()
    rows,baseline=read_file(content) if content else ([],{})
    plan=make_plan(rows,baseline,bookings,state)
    run=OrderFileSync.objects.create(created_by=actor,plan={'rows':plan},database_digest=digest)
    if content:
        run.source.save(str(run.pk)+'.xlsx',ContentFile(content))
    return run


def export_sync(actor,seed_content=None):
    """Export never applies spreadsheet values to the database."""
    backup=database_backup()
    bookings,state,digest=database_state()
    previous=OrderFileSync.objects.filter(applied=True).exclude(result='').first()
    rows=[]
    if seed_content:
        rows,_=read_file(seed_content)
    elif previous:
        with previous.result.open('rb') as handle:
            rows,_=read_file(handle.read())
    plan=make_plan(rows,{},bookings,state) if seed_content else [
        {**r,'action':'same' if r['booking'] in state else 'conflict',
         'errors':['Строка не связана с карточкой программы']} for r in rows]
    if not seed_content and previous:
        conflicts={r['key'] for r in previous.plan.get('rows',[]) if r['action']=='conflict'}
        for row in plan:
            if row['key'] in conflicts:
                row.update(action='conflict',errors=['Не применённые ранее изменения Excel: загрузите файл для проверки'])
    run=OrderFileSync.objects.create(created_by=actor,database_digest=digest,applied=True,
        database_backup=backup,plan={'rows':plan})
    if seed_content:
        run.source.save(str(run.pk)+'.xlsx',ContentFile(seed_content),save=False)
    excluded={r['booking'] for r in plan if r['action']=='conflict'}
    run.baseline={pk:value for pk,value in state.items() if pk not in excluded}
    run.result.save(str(run.pk)+'.xlsx',ContentFile(workbook_bytes(output_rows(plan,bookings,state),run.pk)),save=False)
    run.save()
    return run


def apply_sync(run,actor):
    # Full backup is completed before acquiring database write locks.
    backup=database_backup()
    with transaction.atomic():
        run=OrderFileSync.objects.select_for_update().get(pk=run.pk)
        if run.applied:
            raise ValidationError('Эта синхронизация уже применена.')
        bookings,state,digest=database_state(lock=True)
        if digest!=run.database_digest:
            raise ValidationError('Данные программы изменились. Повторите предварительную проверку файла.')
        aliases={s.working_file_code or s.supplier_code:s for s in Supplier.objects.all()}
        rows=run.plan['rows']
        for item in rows:
            if item['action'] in ('conflict','same'):
                continue
            values=item['merged']
            old=state.get(item['booking'],{})
            if item['action']=='create':
                customer=Customer.objects.create(first_name=values['name'][:100],
                    last_name=values['name'][100:],email=values['email'])
                supplier=aliases[values['firm']]
                booking=Booking.objects.create(customer=customer,supplier=supplier,
                    created_by_user=actor,source_quote_snapshot={'historical_import':{
                        'batch_id':'order-file-sync','row':item['source'],'raw':dict(zip('ABCDEFGHI',
                        [values[k] for k in ('name','pickup','return','group','gross','services','phone','email','number')]))}},
                    currency=item['currency'])
                item['booking']=str(booking.pk)
                old={}
            else:
                booking=bookings[item['booking']]
            patch={}
            for field,attribute in [('name','customer_name_snapshot'),('email','customer_email_snapshot'),('number','supplier_booking_number')]:
                if values[field]!=old.get(field):
                    patch[attribute]=values[field]
            if values['phone']!=old.get('phone'):
                phones=[p.strip() for p in re.split(r'//|\|',values['phone']) if p.strip()]
                if len(phones)>3 or any(len(p)>30 for p in phones):
                    raise ValidationError('Телефон слишком длинный; проверьте строку '+item['source'])
                for i in range(1,4):
                    patch[f'customer_phone_{i}_snapshot']=phones[i-1] if i<=len(phones) else ''
            snapshot=dict(booking.source_quote_snapshot)
            snapshot['working_file_period']=values['period']
            snapshot['working_file_exchange']={'run':str(run.pk),'values':values}
            for side,col in [('pickup','B'),('return','C')]:
                if values[side]!=old.get(side):
                    dt=trip_date(values[side])
                    patch[side+'_datetime']=dt
                    patch[side+'_location_text']=values[side][:300]
                    if 'historical_import' in snapshot:
                        snapshot['historical_import']=dict(snapshot['historical_import'])
                        snapshot['historical_import']['raw']={**snapshot['historical_import'].get('raw',{}),col:values[side]}
            if values['gross']!=old.get('gross'):
                amount=Decimal(values['gross'])
                if item['action']=='create':
                    patch['vehicle_price_gross']=amount
                else:
                    patch['manual_adjustment_amount']=booking.manual_adjustment_amount+amount-booking.total_price_gross
                    patch['manual_adjustment_label']='Изменение суммы через Excel'
                patch['total_price_gross']=amount
            if values['status']!=old.get('status'):
                patch['status']={'Учтён':'COMPLETED','Отменён':'CANCELLED','Обычный':'CONFIRMED'}[values['status']]
            start=patch.get('pickup_datetime',booking.pickup_datetime)
            end=patch.get('return_datetime',booking.return_datetime)
            if start and end and end>=start:
                from math import ceil
                patch['rental_days']=max(1,ceil((end-start).total_seconds()/86400))
            patch.update(source_quote_snapshot=snapshot,updated_at=timezone.now())
            Booking.objects.filter(pk=booking.pk).update(**patch)
            booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
                'Подтверждённая синхронизация Excel; письма не отправлялись',
                changes={'run':str(run.pk),'before':old,'after':values,'operator_user_id':actor.pk})
        bookings,state,_=database_state()
        result=output_rows(rows,bookings,state)
        excluded={r['booking'] for r in rows if r['action']=='conflict'}
        run.baseline={pk:value for pk,value in state.items() if pk not in excluded}
        run.applied=True
        run.database_backup=backup
        run.plan={'rows':rows}
        run.result.save(str(run.pk)+'.xlsx',ContentFile(workbook_bytes(result,run.pk)),save=False)
        run.save()
    return run
