"""Working partner actions. Uses the operator's quote and booking formats."""
from decimal import Decimal
from uuid import uuid4
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.validators import validate_email
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import strip_tags
from config.email_addresses import parse_email_addresses
from .models import PortalConfiguration


def owner_copy():
    config=PortalConfiguration.objects.first()
    address=config.workspace_copy_email if config else ''
    try:validate_email(address)
    except ValidationError:raise ValidationError('כתובת העותק לעידן אינה מוגדרת. יש לפנות לעידן.')
    return address


def subject(record,kind):
    return f'[PARTNER · {record.partner.display_name}] {kind} · {record.number}'


def copy_recipients(primary,*addresses):
    seen={address.strip().casefold() for address in primary}
    result=[]
    for address in addresses:
        address=address.strip()
        validate_email(address)
        if address.casefold() not in seen:
            seen.add(address.casefold());result.append(address)
    return result


def send_offer(record,user,send_customer,customer_email):
    from quotes.models import Quote, QuoteEmailDelivery
    from quotes.email_tools import seat_guides
    copy=owner_copy()
    recipients=[record.partner.email]
    if send_customer:
        validate_email(customer_email);recipients.append(customer_email)
    recipients=list(dict.fromkeys(address.strip().casefold() for address in recipients))
    for address in recipients:validate_email(address)
    details=dict(record.details)
    # Freeze recipients for retries; only unsent deliveries are attempted.
    if details.get('send_recipients') and details['send_recipients']!=recipients:
        raise ValidationError('נמעני ההצעה כבר נקבעו. יש ליצור הצעה חדשה לשינוי הנמענים.')
    details.update(send_recipients=recipients,send_customer=send_customer,customer_email=customer_email)
    delivered=set(details.get('sent_recipients',[]))
    html=details['preview_html'];title=subject(record,'Offer')
    for address in recipients:
        if address in delivered:continue
        message=EmailMultiAlternatives(subject=title,body=strip_tags(html),to=[address],bcc=[] if address==copy.casefold() else [copy],reply_to=[copy])
        message.attach_alternative(html,'text/html')
        for guide in seat_guides(record.draft.quote):
            message.attach(guide['filename'],guide['path'].read_bytes(),'application/pdf')
        if message.send(fail_silently=False)!=1:raise OSError('Mail not accepted')
        delivered.add(address)
        details['sent_recipients']=list(delivered)
        record.details=details;record.save(update_fields=['details','updated_at'])
        QuoteEmailDelivery.objects.create(quote=record.draft.quote,sent_by_user=user,recipient=address,
            subject=title,html=html)
    details['mail_sent']=True;record.details=details;record.status='SENT'
    record.save(update_fields=['details','status','updated_at'])
    Quote.objects.filter(pk=record.draft.quote_id).update(status=Quote.Status.SENT,sent_at=timezone.now(),
        sent_by_user=user,sent_html_snapshot=html,sent_to_email=record.partner.email,sent_subject=title)


def notify_owner(record):
    copy=owner_copy()
    kind={'change':'Change request','cancel':'Cancellation request'}.get(record.details.get('action'),'Manual calculation request')
    lines=[f'Partner: {record.partner.display_name} <{record.partner.email}>',kind]
    if record.parent_id:
        lines.extend([f'Reservation: {record.parent.number}',f'Driver: {record.parent.customer_name}'])
        if record.parent.booking_id:lines.append('Supplier reservation: '+record.parent.booking.supplier_booking_number)
    lines.extend(['',record.details.get('message',''),''])
    for side in ('pickup','return'):
        lines.append(side.title()+': '+' · '.join(str(record.trip.get(side+'_'+key,'')) for key in ('city','date','time','address')))
    if EmailMultiAlternatives(subject=subject(record,kind),body='\n'.join(lines),to=[copy],reply_to=[record.partner.email]).send()!=1:
        raise OSError('Mail not accepted')
    record.details={**record.details,'mail_sent':True}
    record.save(update_fields=['details','updated_at'])


def create_booking(record,option_data,details,user):
    """Convert the immutable saved offer, including its exact protected prices."""
    from suppliers.models import SupplierExtraRate, VehicleRate, SupplierLocation
    from bookings.quote_conversion import create_draft
    from quotes.airport_pickup import airport_code_for_city
    option=record.draft.quote.options.select_related('quote__customer','vehicle_group','supplier').get(vehicle_group_id=int(option_data['id']))
    saved=option.calculation_snapshot
    if not saved.get('vehicle_rate_id'):raise ValidationError('ההצעה ישנה מדי להמרה אוטומטית. יש ליצור הצעה חדשה.')
    trip=record.trip
    quote=option.quote
    count=int(trip.get('drivers',1))
    if details.get('additional_driver'):count=max(2,count)
    if count>int(trip.get('drivers',1)) and count>option.supplier.included_driver_count:
        raise ValidationError('נוסף נהג שלא נכלל בחישוב. חזרו להצעה ועדכנו את מספר הנהגים.')
    names=[details['driver_name'],details.get('additional_driver','')]
    names.extend(details.get(f'driver_{i}_name','') for i in range(3,count+1))
    if any(not name.strip() for name in names[:count]):raise ValidationError('נא להשלים את שמות כל הנהגים.')
    data=dict(first_name=details['driver_name'],last_name='',email=details['email'],phone_1=details['phone'],
        phone_2='',phone_3='',country='',address='',wants_invoice=details.get('invoice',False),
        invoice_name=details.get('invoice_name',''),invoice_tax_id=details.get('invoice_tax',''),
        invoice_address=details.get('invoice_address',''),invoice_email=details['email'] if details.get('invoice') else '',
        flight_number=details.get('flight',''),child_seat_details=details.get('child_seat_details',[]),
        sub_agent=record.partner.pricing_sub_agent,driver_count=count,rental_country=saved.get('rental_country','PL'),
        cross_border_requested=saved.get('cross_border_requested',False),vehicle_group=option.vehicle_group,
        pickup_datetime=quote.pickup_datetime,return_datetime=quote.return_datetime)
    for side in ('pickup','return'):
        for key in ('city','service','address'):data[side+'_'+key]=trip.get(side+'_'+key,'')
    for index,name in enumerate(names[:count],1):data[f'driver_{index}_name']=name
    lines=[]
    for line in saved.get('lines',[]):
        if not line.get('extra_id') or not line.get('rate_id'):raise ValidationError('חסר פירוט מחיר. יש לפנות לעידן.')
        rate=SupplierExtraRate.objects.select_related('extra').get(pk=line['rate_id'],extra_id=line['extra_id'])
        if rate.extra.supplier_id!=option.supplier_id:raise ValidationError('נתוני החברה אינם תואמים להצעה.')
        lines.append(dict(extra=rate.extra,rate=rate,quantity=Decimal(line['quantity']),price=Decimal(line['price']),name=line['name']))
    locations={}
    for side in ('pickup','return'):
        locations[side]=None
        if data[side+'_service']=='AIRPORT':
            code=airport_code_for_city(data[side+'_city'])
            if code:locations[side]=SupplierLocation.objects.filter(supplier=option.supplier,is_active=True,
                location_type='AIRPORT',airport_code=code,**{'supports_'+side:True}).first()
    rate=VehicleRate.objects.select_related('season__price_list').get(pk=saved['vehicle_rate_id'])
    result=dict(supplier=option.supplier,group=option.vehicle_group,vehicle_rate=rate,currency=option.currency,
        daily_rate=Decimal(saved['daily_rate']),base=Decimal(saved['base']),extras_total=Decimal(saved['extras_total']),
        total=option.total_price_gross,deposit_amount=option.deposit_amount,deposit_currency=option.deposit_currency,
        season=saved.get('season',''),day_range=saved.get('day_range',''),locations=locations,extra_lines=lines,
        subagent_adjustment=Decimal(saved.get('subagent_adjustment','0')))
    snapshot=dict(total=str(option.total_price_gross),currency=option.currency,deposit=str(option.deposit_amount),
        deposit_currency=option.deposit_currency,request={key:trip.get(key,'') for key in
            ('pickup_city','pickup_service','pickup_address','return_city','return_service','return_address')},
        partner_id=record.partner_id,partner_offer=record.number,prepayment_notice=saved.get('prepayment_notice',{}))
    snapshot['request']['cross_border_requested']=saved.get('cross_border_requested',False)
    snapshot['request']['partner_remarks']=details.get('remarks','')
    booking=create_draft(option,data,result,snapshot,user)
    for entry,line in zip(booking.extras.order_by('pk'),saved.get('lines',[])):
        frozen=line.get('rate_snapshot',{})
        if frozen:
            for source,target in [('amount_gross','unit_price_gross_snapshot'),('minimum_amount_gross','minimum_amount_gross_snapshot'),('maximum_amount_gross','maximum_amount_gross_snapshot')]:
                value=frozen.get(source)
                setattr(entry,target,Decimal(value) if value is not None else None)
            entry.calculation_type_snapshot=frozen['calculation_type'];entry.formula_snapshot=frozen['formula_config']
            entry.currency_snapshot=frozen.get('currency',option.currency)
            entry.is_mandatory_snapshot=frozen.get('is_mandatory',entry.is_mandatory_snapshot)
            type(entry).objects.filter(pk=entry.pk).update(**{key:getattr(entry,key) for key in ['unit_price_gross_snapshot','minimum_amount_gross_snapshot','maximum_amount_gross_snapshot','calculation_type_snapshot','formula_snapshot','currency_snapshot','is_mandatory_snapshot']})
    return booking


def send_booking(record,user):
    from bookings.models import Booking, SupplierEmailDelivery, BookingHistoryEvent
    from bookings.supplier_format import render_supplier_booking,new_booking_html
    from bookings.message_content import booking_price_error
    booking=record.booking;copy=owner_copy()
    recipients=parse_email_addresses(booking.supplier.booking_email)
    if not recipients:raise ValidationError('כתובת חברת ההשכרה חסרה. יש לפנות לעידן.')
    copies=copy_recipients(recipients,copy,record.partner.email)
    body=render_supplier_booking(booking)
    if record.details.get('remarks'):body+='\nRemarks: '+record.details['remarks']
    error=booking_price_error(booking,body=body)
    if error:raise ValidationError(error)
    title=subject(record,'New booking')
    delivery=SupplierEmailDelivery.objects.create(token=uuid4(),booking=booking,recipient=';'.join(recipients),
        subject=title,body=body,created_by=user)
    message=EmailMultiAlternatives(subject=title,body=body,to=recipients,bcc=copies,reply_to=[copy])
    html=new_booking_html(booking,'NEW',body)
    if html:message.attach_alternative(html,'text/html')
    try:
        if message.send(fail_silently=False)!=1:raise OSError('Mail not accepted')
    except Exception:
        delivery.status='FAILED';delivery.save(update_fields=['status']);raise
    delivery.status='SENT';delivery.sent_at=timezone.now();delivery.save(update_fields=['status','sent_at'])
    Booking.objects.filter(pk=booking.pk).update(status=Booking.Status.WAITING_CONFIRMATION)
    booking.status=Booking.Status.WAITING_CONFIRMATION
    booking.log_history(BookingHistoryEvent.EventType.STATUS_CHANGED,'Partner request sent; waiting for Idan confirmation',
        old_status=Booking.Status.DRAFT,new_status=Booking.Status.WAITING_CONFIRMATION,
        changes={'partner_id':record.partner_id,'operator_user_id':user.pk})
    record.status='WAITING';record.details={**record.details,'mail_sent':True,'sent_copies':copies}
    record.save(update_fields=['status','details','updated_at'])
