"""Supplier-configured NEW letters; UPDATE and other suppliers keep legacy text."""
from string import Template

from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils import timezone, translation
from django.utils.dateformat import format as format_date
from django.utils.html import escape

from config.driver_fees import YOUNG_DRIVER_CODES
from quotes.localization import presentation_for, translate_text
from suppliers.booking_email_format import validate_booking_email_format
from .message_content import price_breakdown, supplier_location, young_driver_names, amount_text


def has_new_booking_format(booking, kind):
    return kind == 'NEW' and bool(booking.supplier.new_booking_email_template.strip())


def _english_datetime(value):
    if value is None:
        return '[please specify]'
    with translation.override('en'):
        return format_date(timezone.localtime(value),'j F Y, H:i')


def _airport(booking, side):
    request = booking.source_quote_snapshot.get('request',{})
    location = getattr(booking,side+'_location',None)
    return request.get(side+'_service') == 'AIRPORT' or bool(location and location.location_type == 'AIRPORT')


def _location(booking, side, options):
    city = booking.source_quote_snapshot.get('request',{}).get(side+'_city','')
    translated = options.get('city_names',{}).get(city)
    if translated and _airport(booking,side):
        return translated+' Airport'
    return supplier_location(booking,side)


def _services(booking, extras, options):
    services = list(options.get('included_services',[]))
    labels = options.get('service_names',{})
    skip = set(options.get('skip_service_codes',[]))
    airport_label = options.get('airport_service_label','')
    if airport_label and (any(_airport(booking,side) for side in ('pickup','return'))
                         or any(e.extra.extra_code=='AIRPORT_FEE' and e.included_in_total for e in extras)):
        services.append(airport_label)
    for extra in extras:
        if not extra.included_in_total or (extra.quantity <= 0 and extra.calculated_price_gross == 0):
            continue
        code = extra.extra.extra_code
        if code in skip or code in YOUNG_DRIVER_CODES:
            continue
        name = labels.get(code,extra.supplier_visible_name)
        if code in ('CHILD_SEAT','BABY_SEAT_BOOSTER'):
            details = []
            for seat in booking.child_seat_details:
                parts = [str(seat.get('type_number') or '[please specify]')]
                if seat.get('age'):
                    parts.append('age '+str(seat['age']))
                if seat.get('height'):
                    parts.append('height '+str(seat['height'])+' cm')
                details.append(', '.join(parts))
            name += ' '+(' / '.join(details) if details else '[please specify]')
        if extra.quantity > 1:
            name += ' x '+amount_text(extra.quantity)
        services.append(name)
    if booking.source_quote_snapshot.get('request',{}).get('cross_border_requested') and labels.get('CROSS_BORDER'):
        services.append(labels['CROSS_BORDER'])
    young = young_driver_names(booking)
    if young:
        services.append(f'Young/new drivers ({len(young)}): '+' // '.join(young))
    if booking.manual_adjustment_amount:
        services.append(f'Manual surcharge: {booking.manual_adjustment_label}: {booking.manual_adjustment_amount} {booking.currency}')
    prepayment = booking.source_quote_snapshot.get('prepayment_notice',{}).get('English','')
    if prepayment:
        services.append(prepayment)
    return '\n'.join('- '+service for service in dict.fromkeys(services) if service)


def render_supplier_booking(booking, *, kind='NEW', extras=None,driver_fallback=''):
    extras = list(booking.extras.all()) if extras is None else extras
    english = presentation_for('English')
    for extra in extras:
        extra.supplier_visible_name = translate_text(extra.supplier_visible_name,english)
    drivers = [' '.join(filter(None,(d.first_name,d.last_name))).strip() for d in booking.drivers.all()]
    if not has_new_booking_format(booking,kind):
        return render_to_string('bookings/supplier_message.txt',dict(booking=booking,
            driver_names=' // '.join(drivers) or booking.customer_name_snapshot or driver_fallback,
            young_driver_names=young_driver_names(booking),price_breakdown=price_breakdown(booking,extras),
            pickup_location=supplier_location(booking,'pickup'),return_location=supplier_location(booking,'return'),
            extras=[extra for extra in extras if extra.included_in_total])).strip()
    options = booking.supplier.new_booking_email_options
    if options is None:
        options = {}
    try:
        validate_booking_email_format(booking.supplier.new_booking_email_template,options)
    except ValueError as error:
        raise ValidationError('Проверьте формат нового заказа поставщика: '+str(error))
    group = booking.vehicle_group
    raw = booking.source_quote_snapshot.get('historical_import',{}).get('raw',{})
    vehicle = f'{group.group_name.upper()} ({group.group_code})' if group else str(raw.get('D',''))
    deposit = booking.source_quote_snapshot.get('deposit')
    deposit = (str(deposit)+' '+booking.source_quote_snapshot.get('deposit_currency',booking.currency)
               if deposit is not None and str(deposit) not in ('','None') else '[please specify]')
    values = dict(customer=booking.customer_name_snapshot,
        driver_names=' / '.join(drivers) or '[please specify driver names]',
        address=', '.join(value for value in [booking.customer_address_snapshot,booking.customer_city_snapshot,
                    booking.customer_country_snapshot,booking.customer_postal_code_snapshot] if value),
        phone=' // '.join(value for value in [booking.customer_phone_1_snapshot,booking.customer_phone_2_snapshot,
                    booking.customer_phone_3_snapshot] if value), email=booking.customer_email_snapshot,
        pickup_date=_english_datetime(booking.pickup_datetime),pickup_location=_location(booking,'pickup',options),
        flight_number=booking.flight_number,return_date=_english_datetime(booking.return_datetime),
        return_location=_location(booking,'return',options),vehicle_class=vehicle,days=str(booking.rental_days or ''),
        services=_services(booking,extras,options),deposit=deposit,price_calculation=price_breakdown(booking,extras))
    return Template(booking.supplier.new_booking_email_template).substitute(values).strip()


def new_booking_html(booking, kind, body):
    if not has_new_booking_format(booking,kind):
        return None
    lines = []
    for line in body.splitlines():
        if line.startswith('- '):
            lines.append('&#8226; '+str(escape(line[2:])))
        elif ': ' in line:
            label,value = line.split(': ',1)
            lines.append('<strong>'+str(escape(label))+':</strong> '+str(escape(value)))
        elif line in ('Rental Details','Additional Services'):
            lines.append('<strong>'+str(escape(line))+'</strong>')
        else:
            lines.append(str(escape(line)))
    return '<div dir="ltr" style="font:14px/1.6 Arial,sans-serif;text-align:left">'+'<br>'.join(lines)+'</div>'
