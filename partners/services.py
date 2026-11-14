from datetime import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from customers.models import Customer
from quotes.models import Quote, QuoteOption
from quotes.services import calculate_quote_options
from config.rental_duration import calculate_rental_days
from suppliers.models import FormVehicleCategory, VehicleGroup, Supplier


def automatic_allowed(data):
    return all(data.get(key) for key in ('driver_ok', 'credit_ok', 'border_ok')) and not data.get('foreign_route')


def complete_option(option, cross_border=False):
    if not option or not option.get('available') or option.get('unavailable_requests'):
        return False
    if any(line.get('warning') for line in option.get('extra_lines', [])):
        return False
    return not cross_border or any(line.get('extra') and line['extra'].extra_code == 'CROSS_BORDER' for line in option.get('extra_lines', []))


def available_groups():
    return VehicleGroup.objects.filter(is_active=True, show_in_offers=True,
        supplier__status=Supplier.Status.ACTIVE, form_categories__is_active=True).distinct().select_related('supplier').prefetch_related('comparison_classes')


def trip_quote(data):
    quote = Quote(pickup_datetime=datetime.fromisoformat(data['pickup_datetime']),
        return_datetime=datetime.fromisoformat(data['return_datetime']),
        pickup_city=data['pickup_city'], return_city=data['return_city'],
        pickup_service=data['pickup_service'], return_service=data['return_service'],
        pickup_address=data.get('pickup_address', ''), return_address=data.get('return_address', ''),
        cross_border_requested=data['cross_border'], driver_count=data['drivers'])
    quote.pickup_location_text = ' · '.join(filter(None, [quote.pickup_city, quote.pickup_service, quote.pickup_address]))
    quote.return_location_text = ' · '.join(filter(None, [quote.return_city, quote.return_service, quote.return_address]))
    quote.rental_days = calculate_rental_days(quote.pickup_datetime, quote.return_datetime)
    quote.extra_requests = {key:qty for key, qty in [('CHILD_SEAT',data['seats']),('NAVIGATION',int(data['gps'])),('SNOW_CHAINS',int(data['chains']))] if qty}
    # Reuse the operator's configured pricing context; never accept it from POST.
    quote.sub_agent_id = data.get('pricing_sub_agent_id')
    return quote


def calculate_options(data, groups=None):
    quote = trip_quote(data)
    if quote.pickup_datetime <= timezone.now():
        raise ValidationError('מועד הקבלה כבר עבר. נא לעדכן את התאריכים.')
    results = {}
    for group in groups if groups is not None else available_groups():
        rows = calculate_quote_options(quote, vehicle_group=group)
        row = rows[0] if rows else None
        results[group.pk] = row if complete_option(row, quote.cross_border_requested) else None
    return results


def categories_with_options(results):
    rows = []
    for category in FormVehicleCategory.objects.filter(is_active=True).prefetch_related('vehicle_groups__supplier'):
        choices = []
        for group in category.vehicle_groups.all():
            if group.pk in results:
                choices.append({'group':group, 'option':results[group.pk]})
        if choices:
            rows.append({'name':category.name, 'choices':choices})
    return rows


@transaction.atomic
def prepare_quote(draft, recipient, config, user):
    ids = set(draft.selected_groups)
    groups = list(available_groups().filter(pk__in=ids))
    if not ids or {g.pk for g in groups} != ids:
        raise ValidationError('נא לבחור מחדש את האפשרויות הזמינות.')
    results = calculate_options(draft.trip, groups)
    if any(not results.get(pk) for pk in ids):
        raise ValidationError('אחת האפשרויות דורשת בדיקה של עידן. נא לבחור מחדש.')
    quote = trip_quote(draft.trip)
    # Do not merge tenants' customers by a shared email or by a name.
    customer = Customer.objects.create(first_name=recipient['customer_name'], last_name='',
        full_name_latin=recipient['customer_name'], email=recipient.get('customer_email',''), phone_1='')
    quote.customer = customer
    quote.created_by_user = user
    quote.language = 'Hebrew'
    quote.customer_notes = draft.trip.get('countries','')
    quote.internal_notes = f'Partner portal · {draft.partner.display_name} · {draft.pk}'
    quote.save()
    for order, option in enumerate(results.values(), 1):
        snapshot = {key:str(option.get(key,'')) for key in ('daily_rate','base','extras_total','subagent_adjustment')}
        snapshot.update({key:option.get(key,'') for key in ('days','season','day_range','subagent_pricing_method','price_audience','hebrew_vehicle_class','body_type_label','fuel_type_label','transmission_label','luggage_info','included_items','excluded_items')})
        snapshot.update(manual_adjustment_amount='0', manual_adjustment_label='',
            lines=[{'extra_id':line['extra'].pk if line.get('extra') else None,
                'rate_id':line['rate'].pk if line.get('rate') else None,
                'name':line['name'], 'price':str(line.get('price','')), 'quantity':str(line.get('quantity',1)), 'warning':line.get('warning','')}
                for line in option['extra_lines']])
        QuoteOption.objects.create(quote=quote, supplier=option['supplier'], vehicle_group=option['group'],
            comparison_class=option['comparison'], supplier_name_snapshot=option['supplier'].supplier_name,
            vehicle_group_name_snapshot=option['group'].group_name, vehicle_models_snapshot=option['models'],
            total_price_gross=option['total'], currency=option['currency'], deposit_amount=option['deposit_amount'],
            deposit_currency=option['deposit_currency'], calculation_snapshot=snapshot, display_order=order)
    draft.quote = quote
    draft.trip = {**draft.trip, 'recipient':{**recipient, 'owner_email':config.owner_email}}
    draft.save(update_fields=['quote','trip','updated_at'])
    return quote


def stale_quote(draft):
    saved = list(draft.quote.options.filter(is_included=True).select_related('vehicle_group'))
    groups = list(available_groups().filter(pk__in=[o.vehicle_group_id for o in saved]))
    current = calculate_options(draft.trip, groups)
    return any(not current.get(row.vehicle_group_id) or
        current[row.vehicle_group_id]['total'] != row.total_price_gross or
        current[row.vehicle_group_id]['currency'] != row.currency or
        current[row.vehicle_group_id]['deposit_amount'] != row.deposit_amount for row in saved)
