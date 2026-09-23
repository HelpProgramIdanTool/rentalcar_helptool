from django import forms
from uuid import uuid4
from smtplib import SMTPException
from django.core import signing
from django.core.mail import EmailMultiAlternatives
from django.http import FileResponse
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.template.loader import render_to_string

from employees.models import Employee
from .models import Booking, BookingHistoryEvent, BookingVoucher, SupplierEmailDelivery
from .message_content import price_breakdown, supplier_location


class ReservationForm(forms.Form):
    supplier_booking_number = forms.CharField(label="Номер резервации поставщика", max_length=100, required=False)
    status = forms.ChoiceField(label="Статус заказа", choices=Booking.Status.choices)
    flight_number = forms.CharField(label="Номер рейса", max_length=50, required=False)

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


class VoucherUploadForm(forms.Form):
    file = forms.FileField(label="Ваучер поставщика")

    def clean_file(self):
        uploaded = self.cleaned_data["file"]
        if uploaded.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Файл слишком большой. Максимум 10 МБ.")
        extension = uploaded.name.rsplit(".", 1)[-1].lower() if "." in uploaded.name else ""
        signatures = {"pdf": b"%PDF-", "jpg": b"\xff\xd8\xff", "jpeg": b"\xff\xd8\xff", "png": b"\x89PNG\r\n\x1a\n"}
        signature = signatures.get(extension)
        beginning = uploaded.read(8)
        uploaded.seek(0)
        if not signature or not beginning.startswith(signature):
            raise forms.ValidationError("Загрузите PDF, JPG или PNG файл.")
        return uploaded


@login_required
@require_http_methods(["POST"])
def upload_voucher(request, pk):
    booking = get_object_or_404(Booking, pk=pk)
    form = VoucherUploadForm(request.POST, request.FILES)
    if form.is_valid():
        uploaded = form.cleaned_data["file"]
        voucher = BookingVoucher.objects.create(
            booking=booking, file=uploaded, original_filename=uploaded.name[:255],
            uploaded_by_user=request.user,
        )
        booking.log_history(BookingHistoryEvent.EventType.NOTE, "Supplier voucher uploaded",
            changes={"voucher_id": voucher.pk, "operator_user_id": request.user.pk},
            created_by=Employee.objects.filter(login_user=request.user).first())
        messages.success(request, "Ваучер сохранён.")
    else:
        messages.error(request, " ".join(str(error) for errors in form.errors.values() for error in errors))
    return redirect("quotes:booking_detail", pk=pk)


@login_required
@require_http_methods(["GET"])
@never_cache
def download_voucher(request, pk, voucher_id):
    voucher = get_object_or_404(BookingVoucher, pk=voucher_id, booking_id=pk)
    response = FileResponse(voucher.file.open("rb"), as_attachment=True, filename=voucher.original_filename)
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def booking_list(request):
    bookings = Booking.objects.select_related(
        "supplier", "vehicle_group", "salesperson_employee", "sub_agent",
        "created_by_user", "confirmed_by_user",
    )
    query = request.GET.get("q", "").strip()
    if query:
        marked_number = Q()
        if len(query) > 2 and query[:2].isalpha():
            marked_number = Q(
                sub_agent__code_prefix__iexact=query[:2],
                supplier_booking_number__icontains=query[2:],
            )
        bookings = bookings.filter(marked_number | Q(booking_number__icontains=query) |
            Q(supplier_booking_number__icontains=query) | Q(customer_name_snapshot__icontains=query) |
            Q(customer_email_snapshot__icontains=query) | Q(customer_phone_1_snapshot__icontains=query) |
            Q(sub_agent__name__icontains=query) | Q(sub_agent__code_prefix__icontains=query) |
            Q(salesperson_employee__first_name__icontains=query) |
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
        "flight_number": booking.flight_number,
    })
    if request.method == "POST" and form.is_valid():
        changes = {field: {"old": getattr(booking, field), "new": value}
                   for field, value in form.cleaned_data.items() if getattr(booking, field) != value}
        if changes:
            # Recording confirmation must never trigger a fresh price calculation.
            updates = {**form.cleaned_data, "updated_at": timezone.now()}
            if booking.status != Booking.Status.CONFIRMED and form.cleaned_data["status"] == Booking.Status.CONFIRMED:
                updates["confirmed_by_user"] = request.user
            Booking.objects.filter(pk=booking.pk).update(**updates)
            booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
                "Reservation number/status updated", changes={**changes, "operator_user_id": request.user.pk},
                created_by=Employee.objects.filter(login_user=request.user).first())
            if "status" in changes:
                booking.log_history(
                    BookingHistoryEvent.EventType.STATUS_CHANGED,
                    "Status changed on booking page",
                    old_status=changes["status"]["old"], new_status=changes["status"]["new"],
                    changes={"operator_user_id": request.user.pk},
                    created_by=Employee.objects.filter(login_user=request.user).first(),
                )
        return redirect("quotes:booking_detail", pk=booking.pk)
    status_events = list(booking.history_events.filter(
        event_type=BookingHistoryEvent.EventType.STATUS_CHANGED,
    ).select_related("created_by"))
    user_ids = {event.changes.get("operator_user_id") for event in status_events if event.changes.get("operator_user_id")}
    users = get_user_model().objects.in_bulk(user_ids)
    status_names = {
        "DRAFT": "Черновик", "WAITING_CONFIRMATION": "Ожидает подтверждения",
        "CONFIRMED": "Подтверждён", "UPDATE_PENDING": "Ожидает изменения",
        "ACTIVE": "Аренда идёт", "COMPLETED": "Завершён",
        "CANCELLED": "Отменён", "NO_SHOW": "Неявка", "SETTLED": "Расчёты закрыты",
    }
    status_history = []
    for event in status_events:
        user = users.get(event.changes.get("operator_user_id"))
        status_history.append({
            "at": event.created_at,
            "old": status_names.get(event.old_status, event.old_status),
            "new": status_names.get(event.new_status, event.new_status),
            "actor": (
                str(event.created_by) if event.created_by else
                (user.get_full_name() or user.username) if user else "—"
            ),
        })
    return render(request, "bookings/detail.html", {
        "booking": booking, "reservation_form": form,
        "voucher_change_count": booking.history_events.filter(
            event_type=BookingHistoryEvent.EventType.STATUS_CHANGED,
            old_status=Booking.Status.UPDATE_PENDING,
            new_status=Booking.Status.CONFIRMED,
        ).count(),
        "status_history": status_history, "active_menu": "orders",
    })


class SupplierMessageForm(forms.Form):
    recipient = forms.EmailField(required=False)
    subject = forms.CharField(max_length=250)
    body = forms.CharField()


@login_required
@require_http_methods(["GET", "POST"])
@never_cache
def supplier_message(request, pk):
    booking = get_object_or_404(Booking.objects.select_related("supplier", "vehicle_group"), pk=pk)
    change_mode = (request.GET.get("change") == "1" or request.POST.get("change_mode") == "1")
    draft_description = "Supplier change draft saved" if change_mode else "Supplier message draft saved"
    extras = list(booking.extras.all())
    names = " // ".join(f"{driver.first_name} {driver.last_name}".strip() for driver in booking.drivers.all())
    draft = booking.history_events.filter(description=draft_description).order_by("-pk").first()
    initial = draft.changes["message"] if draft else {
        "recipient": booking.supplier.booking_email,
        "subject": (f"Change request {booking.supplier_booking_number} / {booking.booking_number}" if change_mode else f"Car rental booking request {booking.booking_number}"),
        "body": ((f"Please update existing reservation {booking.supplier_booking_number}.\nPlease confirm the changes and send an updated voucher.\n\n" if change_mode else "") + render_to_string("bookings/supplier_message.txt", {
            "booking": booking, "driver_names": names or booking.customer_name_snapshot or "[driver names]",
            "price_breakdown": price_breakdown(booking, extras),
            "pickup_location": supplier_location(booking, "pickup"),
            "return_location": supplier_location(booking, "return"),
            "extras": [item for item in extras if item.included_in_total],
        }).strip()),
    }
    form = SupplierMessageForm(request.POST or None, initial=initial)
    send_token = signing.dumps({"booking": booking.pk, "user": request.user.pk, "token": str(uuid4())}, salt="supplier-send")
    if request.method == "POST" and request.POST.get("action") in ("send", "mark_manual"):
        form.fields["recipient"].required = True
        if change_mode and (not booking.supplier_booking_number or booking.status not in (Booking.Status.CONFIRMED, Booking.Status.UPDATE_PENDING)):
            form.add_error(None, "Изменение можно отправить после подтверждения заказа и внесения номера поставщика.")
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
                        draft_description, changes={"message": form.cleaned_data, "operator_user_id": request.user.pk},
                        created_by=Employee.objects.filter(login_user=request.user).first())
                    try:
                        count = (1 if request.POST.get("action") == "mark_manual" else
                            EmailMultiAlternatives(subject=delivery.subject, body=delivery.body, to=[delivery.recipient]).send())
                        if count != 1:
                            raise SMTPException("Message not accepted")
                    except (SMTPException, OSError, ValueError):
                        delivery.status = "FAILED"
                        delivery.save(update_fields=["status"])
                        form.add_error(None, "Отправка не подтверждена. Текст сохранён в истории. Проверьте почту перед повторной отправкой.")
                    else:
                        with transaction.atomic():
                            delivery.status = "MANUAL" if request.POST.get("action") == "mark_manual" else "SENT"
                            delivery.sent_at = timezone.now()
                            delivery.save(update_fields=["status", "sent_at"])
                            old_status = Booking.Status.CONFIRMED if change_mode else Booking.Status.DRAFT
                            new_status = Booking.Status.UPDATE_PENDING if change_mode else Booking.Status.WAITING_CONFIRMATION
                            status_changed = Booking.objects.filter(pk=booking.pk, status=old_status).update(
                                status=new_status, updated_at=timezone.now())
                            if status_changed:
                                booking.log_history(
                                    BookingHistoryEvent.EventType.STATUS_CHANGED,
                                    "Supplier request sent; waiting for confirmation",
                                    old_status=old_status,
                                    new_status=new_status,
                                    changes={"operator_user_id": request.user.pk},
                                    created_by=Employee.objects.filter(login_user=request.user).first(),
                                )
                            booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED, "Supplier message recorded",
                                changes={"delivery_id": delivery.pk, "recipient": delivery.recipient, "operator_user_id": request.user.pk, "method": delivery.status},
                                created_by=Employee.objects.filter(login_user=request.user).first())
                        messages.success(request, "Письмо передано почтовому серверу для отправки поставщику.")
                        return redirect(("quotes:booking_detail" if change_mode else "quotes:supplier_message"), pk=booking.pk)
    if request.method == "POST" and request.POST.get("action") != "send" and form.is_valid():
        booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
            draft_description, changes={"message": form.cleaned_data, "operator_user_id": request.user.pk},
            created_by=Employee.objects.filter(login_user=request.user).first())
        return redirect(reverse("quotes:supplier_message", args=[booking.pk]) + ("?change=1" if change_mode else ""))
    return render(request, "bookings/supplier_message.html", {
        "booking": booking, "active_menu": "orders",
        "form": form,
        "recipient": form["recipient"].value(), "subject": form["subject"].value(), "body": form["body"].value(),
        "draft_saved": bool(draft),
        "change_mode": change_mode,
        "send_token": send_token, "deliveries": booking.supplier_deliveries.order_by("-created_at")[:10],
    })
