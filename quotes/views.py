from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import redirect, render
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.utils import timezone

from customers.models import Customer

from .forms import FirstInquiryForm
from .models import Quote, QuoteOption
from .services import find_or_create_customer
from .services import (
    calculate_quote_options,
    ensure_quote_document_blocks,
    ensure_quote_option_presentation,
)


def _quote_form_initial(quote):
    customer = quote.customer
    pickup = timezone.localtime(quote.pickup_datetime)
    returned = timezone.localtime(quote.return_datetime)
    return {
        "first_name": customer.first_name, "last_name": customer.last_name,
        "email": customer.email, "phone_1": customer.phone_1,
        "phone_2": customer.phone_2, "phone_3": customer.phone_3,
        "country": customer.country, "preferred_language": quote.language,
        "address": customer.address, "wants_invoice": customer.wants_invoice,
        "invoice_name": customer.invoice_name, "invoice_tax_id": customer.invoice_tax_id,
        "invoice_address": customer.invoice_address, "invoice_email": customer.invoice_email,
        "pickup_date": pickup.strftime("%d-%m-%Y"), "pickup_time": pickup.strftime("%H:%M"),
        "return_date": returned.strftime("%d-%m-%Y"), "return_time": returned.strftime("%H:%M"),
        "pickup_city": quote.pickup_city, "pickup_service": quote.pickup_service,
        "pickup_address": quote.pickup_address, "return_city": quote.return_city,
        "return_service": quote.return_service, "return_address": quote.return_address,
        "vehicle_classes": list(quote.requested_vehicle_classes.values_list("id", flat=True)),
        "suppliers": list(quote.requested_suppliers.values_list("id", flat=True)),
        "driver_count": quote.driver_count,
        "cross_border_requested": quote.cross_border_requested,
        "extra_choices": list(quote.extra_requests),
        "child_seat_quantity": quote.extra_requests.get("CHILD_SEAT", 1),
        "customer_notes": quote.customer_notes, "internal_notes": quote.internal_notes,
    }


def _update_quote_from_form(quote, data):
    customer = quote.customer
    for field in (
        "first_name", "last_name", "email", "phone_1", "phone_2", "phone_3",
        "country", "address", "invoice_name", "invoice_tax_id", "invoice_address", "invoice_email",
    ):
        setattr(customer, field, data.get(field, ""))
    customer.wants_invoice = data.get("wants_invoice", False)
    customer.preferred_language = data["preferred_language"]
    customer.save()
    service_labels = dict(FirstInquiryForm.SERVICE_CHOICES)
    for prefix in ("pickup", "return"):
        location = f"{data[f'{prefix}_city']} — {service_labels[data[f'{prefix}_service']]}"
        if data[f"{prefix}_address"]:
            location += f": {data[f'{prefix}_address']}"
        setattr(quote, f"{prefix}_location_text", location)
        setattr(quote, f"{prefix}_city", data[f"{prefix}_city"])
        setattr(quote, f"{prefix}_service", data[f"{prefix}_service"])
        setattr(quote, f"{prefix}_address", data[f"{prefix}_address"])
    quote.language = data["preferred_language"]
    quote.pickup_datetime = data["pickup_datetime"]
    quote.return_datetime = data["return_datetime"]
    quote.driver_count = data["driver_count"]
    quote.cross_border_requested = data["cross_border_requested"]
    quote.extra_requests = {
        code: data["child_seat_quantity"] if code == "CHILD_SEAT" else 1
        for code in data["extra_choices"]
    }
    quote.customer_notes = data["customer_notes"]
    quote.internal_notes = data["internal_notes"]
    quote.save()
    quote.requested_vehicle_classes.set(data["vehicle_classes"])
    quote.requested_suppliers.set(data["suppliers"])
    quote.options.all().delete()
    quote.document_blocks.all().delete()


@login_required
def new_inquiry(request):
    form = FirstInquiryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            customer, customer_created = find_or_create_customer(form.cleaned_data)
            service_labels = dict(FirstInquiryForm.SERVICE_CHOICES)
            pickup_location = (
                f"{form.cleaned_data['pickup_city']} — "
                f"{service_labels[form.cleaned_data['pickup_service']]}"
            )
            return_location = (
                f"{form.cleaned_data['return_city']} — "
                f"{service_labels[form.cleaned_data['return_service']]}"
            )
            if form.cleaned_data["pickup_address"]:
                pickup_location += f": {form.cleaned_data['pickup_address']}"
            if form.cleaned_data["return_address"]:
                return_location += f": {form.cleaned_data['return_address']}"
            quote = Quote.objects.create(
                customer=customer,
                created_by_user=request.user,
                language=form.cleaned_data["preferred_language"],
                pickup_datetime=form.cleaned_data["pickup_datetime"],
                return_datetime=form.cleaned_data["return_datetime"],
                pickup_location_text=pickup_location,
                return_location_text=return_location,
                pickup_city=form.cleaned_data["pickup_city"],
                pickup_service=form.cleaned_data["pickup_service"],
                pickup_address=form.cleaned_data["pickup_address"],
                return_city=form.cleaned_data["return_city"],
                return_service=form.cleaned_data["return_service"],
                return_address=form.cleaned_data["return_address"],
                vehicle_request="",
                driver_count=form.cleaned_data["driver_count"],
                cross_border_requested=form.cleaned_data["cross_border_requested"],
                extra_requests={
                    code: (
                        form.cleaned_data["child_seat_quantity"]
                        if code == "CHILD_SEAT"
                        else 1
                    )
                    for code in form.cleaned_data["extra_choices"]
                },
                customer_notes=form.cleaned_data["customer_notes"],
                internal_notes=form.cleaned_data["internal_notes"],
            )
            quote.requested_vehicle_classes.set(form.cleaned_data["vehicle_classes"])
            quote.requested_suppliers.set(form.cleaned_data["suppliers"])
        return redirect("quotes:inquiry_saved", quote_number=quote.quote_number)
    return render(request, "quotes/new_inquiry.html", {"form": form})


@login_required
def inquiry_saved(request, quote_number):
    quote = Quote.objects.select_related("customer").get(quote_number=quote_number)
    return render(request, "quotes/inquiry_saved.html", {"quote": quote})


@login_required
def edit_quote(request, quote_number):
    quote = Quote.objects.select_related("customer").get(quote_number=quote_number)
    form = FirstInquiryForm(
        request.POST or None,
        initial=None if request.method == "POST" else _quote_form_initial(quote),
    )
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            _update_quote_from_form(quote, form.cleaned_data)
        return redirect("quotes:calculate_quote", quote_number=quote.quote_number)
    return render(request, "quotes/new_inquiry.html", {
        "form": form, "quote": quote, "is_editing": True,
    })


@login_required
@require_POST
def duplicate_quote(request, quote_number):
    source = Quote.objects.select_related("customer").get(quote_number=quote_number)
    duplicate = Quote.objects.create(
        customer=source.customer, created_by_user=request.user, status=Quote.Status.DRAFT,
        language=source.language, pickup_datetime=source.pickup_datetime,
        return_datetime=source.return_datetime, pickup_location_text=source.pickup_location_text,
        return_location_text=source.return_location_text, pickup_city=source.pickup_city,
        pickup_service=source.pickup_service, pickup_address=source.pickup_address,
        return_city=source.return_city, return_service=source.return_service,
        return_address=source.return_address, cross_border_requested=source.cross_border_requested,
        extra_requests=source.extra_requests, driver_count=source.driver_count,
        vehicle_request=source.vehicle_request, customer_notes=source.customer_notes,
        internal_notes=source.internal_notes,
    )
    duplicate.requested_vehicle_classes.set(source.requested_vehicle_classes.all())
    duplicate.requested_suppliers.set(source.requested_suppliers.all())
    return redirect("quotes:edit_quote", quote_number=duplicate.quote_number)


@login_required
def calculate_quote(request, quote_number):
    quote = Quote.objects.select_related("customer").get(quote_number=quote_number)
    options = calculate_quote_options(quote)
    if request.method == "POST":
        selected_ids = {int(value) for value in request.POST.getlist("selected_options") if value.isdigit()}
        available = {option["group"].id: option for option in options if option["available"]}
        selected = [available[group_id] for group_id in selected_ids if group_id in available]
        if not selected:
            return render(request, "quotes/calculate_quote.html", {
                "quote": quote, "options": options,
                "selection_error": "Отметь хотя бы один рассчитанный вариант.",
            })
        with transaction.atomic():
            quote.options.update(is_included=False)
            for order, option in enumerate(selected, start=1):
                lines = [{
                    "name": line["name"],
                    "price": str(line.get("price", "")),
                    "warning": line.get("warning", ""),
                } for line in option["extra_lines"]]
                QuoteOption.objects.update_or_create(
                    quote=quote, vehicle_group=option["group"],
                    defaults={
                        "supplier": option["supplier"],
                        "comparison_class": option["comparison"],
                        "supplier_name_snapshot": option["supplier"].supplier_name,
                        "vehicle_group_name_snapshot": option["group"].group_name,
                        "vehicle_models_snapshot": option["models"],
                        "total_price_gross": option["total"],
                        "currency": option["currency"],
                        "deposit_amount": option["deposit_amount"],
                        "deposit_currency": option["deposit_currency"],
                        "calculation_snapshot": {
                            "daily_rate": str(option["daily_rate"]), "days": option["days"],
                            "base": str(option["base"]), "extras_total": str(option["extras_total"]),
                            "season": option["season"], "day_range": option["day_range"], "lines": lines,
                            "hebrew_vehicle_class": option["hebrew_vehicle_class"],
                            "included_items": option["included_items"],
                            "excluded_items": option["excluded_items"],
                        },
                        "display_order": order, "is_included": True,
                    },
                )
        return redirect("quotes:quote_preview", quote_number=quote.quote_number)
    return render(
        request,
        "quotes/calculate_quote.html",
        {"quote": quote, "options": options},
    )


@login_required
@never_cache
def quote_preview(request, quote_number):
    quote = Quote.objects.select_related("customer").get(quote_number=quote_number)
    ensure_quote_document_blocks(quote)
    ensure_quote_option_presentation(quote)
    options = quote.options.filter(is_included=True).select_related("comparison_class")
    blocks = quote.document_blocks.filter(is_enabled=True)
    service_labels = {
        "AIRPORT": "שדה התעופה",
        "ADDRESS": "מסירה לכתובת בעיר",
        "CITY_BRANCH": "סניף בעיר",
    }
    pickup_location = f"{quote.pickup_city} — {service_labels.get(quote.pickup_service, quote.pickup_service)}"
    return_location = f"{quote.return_city} — {service_labels.get(quote.return_service, quote.return_service)}"
    if quote.pickup_address:
        pickup_location += f": {quote.pickup_address}"
    if quote.return_address:
        return_location += f": {quote.return_address}"
    return render(request, "quotes/quote_preview.html", {
        "quote": quote, "options": options, "blocks": blocks,
        "pickup_location": pickup_location, "return_location": return_location,
    })


@login_required
def customer_lookup(request):
    email = request.GET.get("email", "").strip()
    phone = request.GET.get("phone", "").strip()
    if not email and not phone:
        return JsonResponse({"found": False})
    query = Q()
    if email:
        query |= Q(email__iexact=email)
    if phone:
        query |= Q(phone_1=phone) | Q(phone_2=phone) | Q(phone_3=phone)
    customer = Customer.objects.filter(query).first()
    if not customer:
        return JsonResponse({"found": False})
    events = [
        {
            "date": event.event_date.strftime("%d-%m-%Y"),
            "title": event.title,
            "type": event.get_event_type_display(),
            "severity": event.get_severity_display(),
        }
        for event in customer.events.all()[:5]
    ]
    return JsonResponse({
        "found": True,
        "id": customer.id,
        "name": str(customer),
        "email": customer.email,
        "phones": [phone for phone in (customer.phone_1, customer.phone_2, customer.phone_3) if phone],
        "quote_count": customer.quotes.count(),
        "booking_count": customer.bookings.count(),
        "warning_level": customer.get_warning_level_display(),
        "warning_code": customer.warning_level,
        "warning_text": customer.warning_text,
        "events": events,
        "admin_url": f"/admin/customers/customer/{customer.id}/change/",
    })
