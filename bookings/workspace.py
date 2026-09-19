from django import forms
from uuid import uuid4
from smtplib import SMTPException
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string

from employees.models import Employee
from .models import Booking, BookingHistoryEvent, SupplierEmailDelivery
from .message_content import price_breakdown, supplier_location


class ReservationForm(forms.Form):
    supplier_booking_number = forms.CharField(label="Номер резервации поставщика", max_length=100, required=False)
    status = forms.ChoiceField(label="Статус заказа", choices=Booking.Status.choices)

    def __init__(self, *args, booking, **kwargs):
        self.booking = booking
        super().__init__(*args, **kwargs)

    def clean(self):
        data = super().clean()
        number = data.get("supplier_booking_number", "")
        if data.get("status") == Booking.Status.CONFIRMED and not number:
            self.add_error("supplier_booking_number", "Для подтверждённого заказа укажите номер резервации.")
        if number and Booking.objects.filter(supplier=self.booking.supplier,
                supplier_booking_number__iexact=number).exclude(pk=self.booking.pk).exists():
            self.add_error("supplier_booking_number", "У этой фирмы уже есть заказ с таким номером. Проверьте дубликат.")
        return data


@login_required
def booking_list(request):
    bookings = Booking.objects.select_related("supplier", "vehicle_group", "salesperson_employee", "sub_agent")
    query = request.GET.get("q", "").strip()
    if query:
        bookings = bookings.filter(Q(booking_number__icontains=query) |
            Q(supplier_booking_number__icontains=query) | Q(customer_name_snapshot__icontains=query) |
            Q(customer_email_snapshot__icontains=query) | Q(customer_phone_1_snapshot__icontains=query) |
            Q(sub_agent__name__icontains=query) | Q(salesperson_employee__first_name__icontains=query) |
            Q(salesperson_employee__last_name__icontains=query))
    status = request.GET.get("status", "")
    if status:
        bookings = bookings.filter(status=status)
    supplier = request.GET.get("supplier", "")
    if supplier.isdigit():
        bookings = bookings.filter(supplier_id=supplier)
    from suppliers.models import Supplier
    return render(request, "bookings/list.html", {
        "page_obj": Paginator(bookings.order_by("-created_at", "-pk"), 30).get_page(request.GET.get("page")),
        "q": query, "status": status, "supplier_id": supplier, "suppliers": Supplier.objects.all(),
        "statuses": Booking.Status.choices, "active_menu": "orders",
    })


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def booking_detail(request, pk):
    booking = get_object_or_404(Booking.objects.select_for_update().select_related("supplier", "vehicle_group", "source_quote"), pk=pk)
    form = ReservationForm(request.POST or None, booking=booking, initial={
        "supplier_booking_number": booking.supplier_booking_number, "status": booking.status,
    })
    if request.method == "POST" and form.is_valid():
        changes = {field: {"old": getattr(booking, field), "new": value}
                   for field, value in form.cleaned_data.items() if getattr(booking, field) != value}
        if changes:
            # Recording confirmation must never trigger a fresh price calculation.
            Booking.objects.filter(pk=booking.pk).update(**form.cleaned_data, updated_at=timezone.now())
            booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
                "Reservation number/status updated", changes={**changes, "operator_user_id": request.user.pk},
                created_by=Employee.objects.filter(login_user=request.user).first())
        return redirect("quotes:booking_detail", pk=booking.pk)
    return render(request, "bookings/detail.html", {"booking": booking, "reservation_form": form, "active_menu": "orders"})


class SupplierMessageForm(forms.Form):
    recipient = forms.EmailField(required=False)
    subject = forms.CharField(max_length=250)
    body = forms.CharField()


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def supplier_message(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("supplier", "vehicle_group"), pk=pk)
    extras = list(booking.extras.all())
    names = " // ".join(f"{driver.first_name} {driver.last_name}".strip() for driver in booking.drivers.all())
    draft = booking.history_events.filter(description="Supplier message draft saved").order_by("-pk").first()
    initial = draft.changes["message"] if draft else {
        "recipient": booking.supplier.booking_email,
        "subject": f"Car rental booking request {booking.booking_number}",
        "body": render_to_string("bookings/supplier_message.txt", {
            "booking": booking, "driver_names": names or booking.customer_name_snapshot or "[driver names]",
            "price_breakdown": price_breakdown(booking, extras),
            "pickup_location": supplier_location(booking, "pickup"),
            "return_location": supplier_location(booking, "return"),
            "extras": [item for item in extras if item.included_in_total],
        }).strip(),
    }
    form = SupplierMessageForm(request.POST or None, initial=initial)
    send_token = signing.dumps({"booking": booking.pk, "user": request.user.pk, "token": str(uuid4())}, salt="supplier-send")
    if request.method == "POST" and request.POST.get("action") == "send":
        form.fields["recipient"].required = True
        if form.is_valid():
            try:
                send_data = signing.loads(request.POST.get("send_token", ""), salt="supplier-send", max_age=3600)
                if send_data["booking"] != booking.pk or send_data["user"] != request.user.pk:
                    raise signing.BadSignature()
            except (signing.BadSignature, KeyError):
                form.add_error(None, "Страница устарела. Откройте письмо заново перед отправкой.")
            else:
                delivery, created = SupplierEmailDelivery.objects.get_or_create(token=send_data["token"], defaults={
                    "booking": booking, "created_by": request.user, **form.cleaned_data})
                if not created:
                    form.add_error(None, "Этот запрос уже обработан. Проверьте историю отправки ниже; повторное письмо не отправлено.")
                else:
                    booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
                        "Supplier message draft saved", changes={"message": form.cleaned_data, "operator_user_id": request.user.pk},
                        created_by=Employee.objects.filter(login_user=request.user).first())
                    try:
                        count = EmailMultiAlternatives(subject=delivery.subject, body=delivery.body, to=[delivery.recipient]).send()
                        if count != 1:
                            raise SMTPException("Message not accepted")
                    except (SMTPException, OSError, ValueError):
                        delivery.status = "FAILED"
                        delivery.save(update_fields=["status"])
                        form.add_error(None, "Отправка не подтверждена. Текст сохранён в истории. Проверьте почту перед повторной отправкой.")
                    else:
                        with transaction.atomic():
                            delivery.status = "SENT"
                            delivery.sent_at = timezone.now()
                            delivery.save(update_fields=["status", "sent_at"])
                            Booking.objects.filter(pk=booking.pk, status="DRAFT").update(status="WAITING_CONFIRMATION", updated_at=timezone.now())
                            booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED, "Supplier email sent",
                                changes={"delivery_id": delivery.pk, "recipient": delivery.recipient, "operator_user_id": request.user.pk},
                                created_by=Employee.objects.filter(login_user=request.user).first())
                        messages.success(request, "Письмо передано почтовому серверу для отправки поставщику.")
                        return redirect("quotes:supplier_message", pk=booking.pk)
    if request.method == "POST" and request.POST.get("action") != "send" and form.is_valid():
        booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
            "Supplier message draft saved", changes={"message": form.cleaned_data, "operator_user_id": request.user.pk},
            created_by=Employee.objects.filter(login_user=request.user).first())
        return redirect("quotes:supplier_message", pk=booking.pk)
    return render(request, "bookings/supplier_message.html", {
        "booking": booking, "active_menu": "orders",
        "form": form,
        "recipient": form["recipient"].value(), "subject": form["subject"].value(), "body": form["body"].value(),
        "draft_saved": bool(draft),
        "send_token": send_token, "deliveries": booking.supplier_deliveries.order_by("-created_at")[:10],
    })
