"""Operator review of booking amendments and independently tracked supplier mail."""
from copy import deepcopy
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.html import escape
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from config.email_addresses import parse_email_addresses
from .attention import visible_bookings
from .manual import ManualBookingForm, clone_initial
from .message_content import price_breakdown, supplier_location
from .models import Booking, BookingAmendment, BookingHistoryEvent, SupplierEmailDelivery
from .quote_conversion import calculate, create_draft, fingerprint, review_snapshot


class AmendmentForm(ManualBookingForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop('entry_token')
        self.fields.pop('existing_customer')


def current_snapshot(booking):
    """Keep the full original booking and related evidence before replacing inputs."""
    from django.core.serializers.json import DjangoJSONEncoder
    import json
    return json.loads(json.dumps({
        'fields': {f.attname: getattr(booking, f.attname) for f in booking._meta.concrete_fields},
        'drivers': list(booking.drivers.values()),
        'extras': list(booking.extras.values()),
    }, cls=DjangoJSONEncoder))


def initial_data(booking):
    initial = clone_initial(booking)
    initial['customer_name'] = booking.customer_name_snapshot
    for index, driver in enumerate(booking.drivers.all(), 1):
        initial[f'driver_{index}_name'] = f'{driver.first_name} {driver.last_name}'.strip()
        initial[f'driver_{index}_young'] = driver.young_driver_status
    if not booking.drivers.exists():
        initial['driver_1_name'] = booking.customer_name_snapshot
    return initial


def order_body(booking):
    extras = list(booking.extras.all())
    from quotes.localization import presentation_for, translate_text
    english = presentation_for('English')
    for extra in extras:
        extra.supplier_visible_name = translate_text(extra.supplier_visible_name, english)
    return render_to_string('bookings/supplier_message.txt', {
        'booking': booking,
        'driver_names': ' // '.join(f'{d.first_name} {d.last_name}'.strip() for d in booking.drivers.all()) or booking.customer_name_snapshot,
        'price_breakdown': price_breakdown(booking, extras),
        'pickup_location': supplier_location(booking, 'pickup'),
        'return_location': supplier_location(booking, 'return'),
        'extras': [e for e in extras if e.included_in_total],
    }).strip()


def message(kind, recipient, subject, body, previous=''):
    import difflib
    old_lines = previous.splitlines()
    new_lines = body.splitlines()
    same = set()
    for block in difflib.SequenceMatcher(None, old_lines, new_lines).get_matching_blocks():
        same.update(range(block.b, block.b + block.size))
    html = '<div style="font-family:Arial;white-space:pre-wrap">'
    for index, line in enumerate(new_lines):
        text = escape(line)
        if kind == 'UPDATE' and index not in same:
            text = f'<strong style="color:#155eef"><u>{text}</u></strong>'
        html += str(text) + '<br>'
    html += '</div>'
    return dict(kind=kind, recipient=recipient, subject=subject[:250], body=body,
                html=html, status='DRAFT', token=str(uuid4()))


def prepare_amendment(booking, data, result, snapshot, user, pending=None):
    from suppliers.models import Supplier
    before = pending.before if pending else current_snapshot(booking)
    old_supplier = Supplier.objects.get(pk=before['fields']['supplier_id'])
    old_number = before['fields']['supplier_booking_number']
    old_body = before.get('supplier_body') or order_body(booking)
    before = {**before, 'supplier_body': old_body}
    switched = old_supplier.pk != result['supplier'].pk
    if switched and not old_number:
        raise forms.ValidationError('Перед сменой фирмы укажите номер старого заказа поставщика для письма отмены.')
    if not switched and not old_number:
        raise forms.ValidationError('Для UPDATE укажите номер заказа поставщика в карточке заказа.')
    snapshot = {**booking.source_quote_snapshot, **snapshot}
    option = SimpleNamespace(quote=SimpleNamespace(customer=booking.customer, pk=None, quote_number=booking.booking_number))
    create_draft(option, data, result, snapshot, user, existing=booking)
    updates = {name: data.get(name, '') for name in ('hotel_name', 'return_hotel_name')}
    if switched:
        updates.update(supplier_booking_number='', status=Booking.Status.DRAFT)
    else:
        updates.update(supplier_booking_number=old_number, status=before['fields']['status'])
    Booking.objects.filter(pk=booking.pk).update(**updates)
    booking.refresh_from_db()
    new_body = order_body(booking)
    if switched:
        mails = [message('CANCEL', old_supplier.changes_email or old_supplier.booking_email,
                    f'CANCEL ORDER {old_number}',
                    f'Please cancel reservation {old_number} and confirm cancellation.\n\n{old_body}'),
                 message('NEW', booking.supplier.booking_email,
                    f'NEW ORDER - {booking.customer_name_snapshot}', new_body)]
    else:
        body = f'Please update reservation {old_number} and send an updated voucher.\n\n{new_body}'
        mails = [message('UPDATE', booking.supplier.changes_email or booking.supplier.booking_email,
                         f'UPDATE ORDER {old_number}', body, old_body)]
    if pending:
        pending.after = current_snapshot(booking)
        pending.messages = mails
        pending.save(update_fields=['after', 'messages'])
        amendment = pending
    else:
        amendment = BookingAmendment.objects.create(booking=booking, before=before,
            after=current_snapshot(booking), messages=mails, created_by=user)
    booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
        'Booking amendment prepared; supplier messages not sent',
        changes={'amendment_id': amendment.pk, 'supplier_changed': switched, 'operator_user_id': user.pk})
    return amendment


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def edit_booking(request, pk):
    booking = get_object_or_404(visible_bookings(request.user).select_for_update(), pk=pk)
    pending = next((a for a in booking.amendments.order_by('-pk') if any(m['status'] != 'SENT' for m in a.messages)), None)
    if pending and any(m['status'] != 'DRAFT' for m in pending.messages):
        return redirect('quotes:booking_amendment', pk=pk, amendment_id=pending.pk)
    form = AmendmentForm(request.POST or None, initial=initial_data(booking))
    # Ownership is not reassigned while amending a customer's rental.
    for name in ('order_source', 'responsible', 'sub_agent'):
        form.fields[name].disabled = True
    baseline = fingerprint(current_snapshot(booking))
    result = token = None
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        from quotes.models import Quote
        option = SimpleNamespace(pk=None, quote=Quote(quote_number=booking.booking_number,
            sub_agent=booking.sub_agent), total_price_gross=booking.total_price_gross, currency=booking.currency)
        try:
            result = calculate(option, data)
            if result['deposit_amount'] is None:
                raise forms.ValidationError('Не указан депозит выбранной группы. Заполните его в справочнике перед изменением заказа.')
            snapshot = review_snapshot(option, data, result)
            stamp = {'user': request.user.pk, 'booking': pk, 'baseline': baseline, 'result': fingerprint(snapshot)}
            if request.POST.get('action') == 'create':
                try:
                    previous = signing.loads(request.POST.get('review_token', ''), salt='booking-amendment', max_age=3600)
                except signing.BadSignature:
                    previous = None
                if previous != stamp or request.POST.get('confirm_price') != 'yes':
                    raise forms.ValidationError('Данные, заказ или тариф изменились. Пересчитайте и подтвердите актуальный расчёт.')
                amendment = prepare_amendment(booking, data, result, snapshot, request.user, pending=pending)
                return redirect('quotes:booking_amendment', pk=pk, amendment_id=amendment.pk)
            token = signing.dumps(stamp, salt='booking-amendment')
        except forms.ValidationError as error:
            form.add_error(None, error)
    return render(request, 'bookings/from_offer.html', dict(
        form=form, booking=booking, edit_mode=True, manual_entry=True, clone_source=booking,
        result=result, review_token=token, active_menu='orders',
        group_suppliers={str(g.pk): str(g.supplier_id) for g in form.fields['vehicle_group'].queryset},
        delta=result['total']-booking.total_price_gross if result and result['currency']==booking.currency else None))


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def cancel_booking(request, pk):
    booking = get_object_or_404(visible_bookings(request.user), pk=pk)
    if request.method == 'POST':
        with transaction.atomic():
            booking = visible_bookings(request.user).select_for_update().get(pk=pk)
            if booking.status == Booking.Status.CANCELLED:
                messages.info(request, 'Заказ уже отменён.')
                return redirect('quotes:booking_detail', pk=pk)
            pending = next((a for a in booking.amendments.order_by('-pk')
                            if any(m['kind']=='CANCEL_BOOKING' and m['status'] in ('DRAFT','FAILED','SENDING') for m in a.messages)), None)
            if pending:
                return redirect('quotes:booking_amendment', pk=pk, amendment_id=pending.pk)
            number = booking.supplier_booking_number or booking.booking_number
            item = message('CANCEL_BOOKING', booking.supplier.changes_email or booking.supplier.booking_email,
                           f'CANCEL ORDER {number}',
                           f'Please cancel reservation {number}. The customer has requested cancellation.\n\n{order_body(booking)}')
            amendment = BookingAmendment.objects.create(booking=booking, before=current_snapshot(booking),
                after=current_snapshot(booking), messages=[item], created_by=request.user)
        return redirect('quotes:booking_amendment', pk=pk, amendment_id=amendment.pk)
    return render(request, 'bookings/cancel.html', {'booking':booking, 'active_menu':'orders'})


@login_required
@never_cache
@require_http_methods(['GET', 'POST'])
def amendment_messages(request, pk, amendment_id):
    booking = get_object_or_404(visible_bookings(request.user), pk=pk)
    amendment = get_object_or_404(BookingAmendment, pk=amendment_id, booking=booking)
    if request.method == 'POST':
        try:
            index = int(request.POST.get('message_index', '-1'))
        except ValueError:
            raise Http404
        if not 0 <= index < len(amendment.messages):
            raise Http404
        with transaction.atomic():
            amendment = BookingAmendment.objects.select_for_update().get(pk=amendment.pk)
            item = deepcopy(amendment.messages[index])
            retry = item['status'] == 'FAILED' and request.POST.get('confirm_retry') == 'yes'
            if item['status'] != 'DRAFT' and not retry:
                messages.error(request, 'Это письмо уже обработано. Проверьте его состояние; повторная отправка заблокирована.')
                return redirect('quotes:booking_amendment', pk=pk, amendment_id=amendment_id)
            try:
                recipients = parse_email_addresses(request.POST.get('recipient', item['recipient']))
                if not recipients:
                    raise ValueError('Укажите адрес получателя.')
            except (ValueError, forms.ValidationError):
                messages.error(request, 'Укажите корректный адрес получателя.')
                return redirect('quotes:booking_amendment', pk=pk, amendment_id=amendment_id)
            manual = request.POST.get('action') == 'manual' and item['kind'] == 'CANCEL_BOOKING'
            item.update(recipient='; '.join(recipients), status='SENDING')
            if retry:
                item['token'] = str(uuid4())
            amendment.messages[index] = item
            amendment.save(update_fields=['messages'])
            delivery = SupplierEmailDelivery.objects.create(token=item['token'], booking=booking,
                recipient=item['recipient'], subject=item['subject'], body=item['body'], created_by=request.user)
        error = ''
        try:
            if not manual:
                email = EmailMultiAlternatives(subject=item['subject'], body=item['body'], to=recipients)
                email.attach_alternative(item['html'], 'text/html')
                if email.send() != 1:
                    raise OSError('Mail was not accepted')
        except (OSError, ValueError):
            error = 'Отправка не подтверждена. Проверьте почту перед повторной отправкой.'
        with transaction.atomic():
            amendment = BookingAmendment.objects.select_for_update().get(pk=amendment.pk)
            amendment.messages[index]['status'] = 'FAILED' if error else 'SENT'
            amendment.save(update_fields=['messages'])
            delivery.status = 'FAILED' if error else ('MANUAL' if manual else 'SENT')
            delivery.sent_at = None if error else timezone.now()
            delivery.save(update_fields=['status', 'sent_at'])
            if not error and item['kind'] == 'CANCEL_BOOKING':
                locked = Booking.objects.select_for_update().get(pk=pk)
                old_status = locked.status
                Booking.objects.filter(pk=pk).update(status=Booking.Status.CANCELLED, updated_at=timezone.now())
                locked.log_history(BookingHistoryEvent.EventType.CANCELLED,
                    'Cancellation message sent manually' if manual else 'Cancellation message accepted by mail server',
                    old_status=old_status, new_status=Booking.Status.CANCELLED,
                    changes={'amendment_id':amendment.pk,'delivery_id':delivery.pk,'operator_user_id':request.user.pk})
            if not error and item['kind'] in ('NEW', 'UPDATE'):
                new_status = Booking.Status.WAITING_CONFIRMATION if item['kind']=='NEW' else Booking.Status.UPDATE_PENDING
                old_status = booking.status
                Booking.objects.filter(pk=pk).update(status=new_status, updated_at=timezone.now())
                booking.log_history(BookingHistoryEvent.EventType.STATUS_CHANGED,
                    'Supplier amendment message sent; waiting for confirmation', old_status=old_status,
                    new_status=new_status, changes={'amendment_id': amendment.pk, 'delivery_id': delivery.pk})
            booking.log_history(BookingHistoryEvent.EventType.NOTE, 'Amendment supplier mail result',
                changes={'amendment_id': amendment.pk, 'kind': item['kind'], 'status': delivery.status})
        (messages.error if error else messages.success)(request, error or ('Ручная отправка отмечена. Заказ отменён.' if manual else 'Письмо передано почтовому серверу.'))
        return redirect('quotes:booking_amendment', pk=pk, amendment_id=amendment_id)
    return render(request, 'bookings/amendment_messages.html', {
        'booking': booking, 'amendment': amendment, 'active_menu': 'orders',
        'can_revise': all(m['status']=='DRAFT' and m['kind']!='CANCEL_BOOKING' for m in amendment.messages)})
