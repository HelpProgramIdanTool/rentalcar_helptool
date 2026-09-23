from uuid import uuid4
from decimal import Decimal, InvalidOperation
import base64
import hashlib
from smtplib import SMTPException

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Q, Max
from django.urls import reverse
from django.template.loader import render_to_string
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST
from django.utils import timezone

from customers.models import Customer

from .forms import FirstInquiryForm, QuoteListFilterForm, QUOTE_STATUS_LABELS
from .models import Quote, QuoteOption, QuoteEmailDelivery
from .email_tools import load_email_template, seat_guides, child_seat_text
from .email_forms import EmailSubjectForm, BlockFormSet, OptionFormSet
from .email_content import REQUIRED_BLOCKS
from .airport_pickup import airport_pickup_messages
from .services import find_or_create_customer
from .services import (
    calculate_quote_options,
    ensure_quote_document_blocks,
    ensure_quote_option_presentation,
)


@login_required
def quote_list(request):
    filters = QuoteListFilterForm(request.GET)
    quotes = Quote.objects.select_related("customer", "created_by_user", "sent_by_user")
    if filters.is_valid():
        data = filters.cleaned_data
        for term in data["q"].split():
            quotes = quotes.filter(
                Q(quote_number__icontains=term) | Q(customer__first_name__icontains=term)
                | Q(customer__last_name__icontains=term) | Q(customer__email__icontains=term)
                | Q(customer__phone_1__icontains=term) | Q(customer__phone_2__icontains=term)
                | Q(customer__phone_3__icontains=term)
            )
        if data["status"]:
            quotes = quotes.filter(status=data["status"])
        if data["pickup_from"]:
            quotes = quotes.filter(pickup_datetime__date__gte=data["pickup_from"])
        if data["pickup_to"]:
            quotes = quotes.filter(pickup_datetime__date__lte=data["pickup_to"])
    else:
        quotes = quotes.none()
    sort = request.GET.get("sort", "-created_at")
    allowed_sorts = {"created_at", "-created_at", "pickup_datetime", "-pickup_datetime"}
    if sort not in allowed_sorts:
        sort = "-created_at"
    page = Paginator(quotes.order_by(sort, "-pk"), 25).get_page(request.GET.get("page"))
    for quote in page:
        quote.status_label = QUOTE_STATUS_LABELS.get(quote.status, quote.status)
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "quotes/quote_list.html", {
        "page_obj": page, "filters": filters, "sort": sort,
        "filter_query": query.urlencode(), "active_menu": "quotes",
    })


def _quote_form_initial(quote):
    customer = quote.customer
    pickup = timezone.localtime(quote.pickup_datetime)
    returned = timezone.localtime(quote.return_datetime)
    vehicle_group_ids = list(
        quote.requested_vehicle_groups.values_list("id", flat=True)
    )
    if not vehicle_group_ids:
        groups = quote.requested_vehicle_classes.values_list(
            "vehicle_groups__id", flat=True
        )
        vehicle_group_ids = list(
            group_id for group_id in groups if group_id is not None
        )
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
        "vehicle_groups": vehicle_group_ids,
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
    quote.requested_vehicle_groups.set(data["vehicle_groups"])
    comparison_ids = data["vehicle_groups"].values_list(
        "comparison_classes__id", flat=True
    ).exclude(comparison_classes__id__isnull=True).distinct()
    quote.requested_vehicle_classes.set(comparison_ids)
    quote.requested_suppliers.set(data["suppliers"])
    quote.options.all().delete()
    # Email wording is a separate draft and survives changes to rental dates.


@login_required
def new_inquiry(request, customer_id=None):
    selected_customer = get_object_or_404(Customer, pk=customer_id) if customer_id is not None else None
    initial = {}
    if selected_customer:
        initial = {field: getattr(selected_customer, field) for field in (
            "first_name", "last_name", "email", "phone_1", "phone_2", "phone_3",
            "country", "preferred_language", "address", "wants_invoice", "invoice_name",
            "invoice_tax_id", "invoice_address", "invoice_email",
        )}
    form = FirstInquiryForm(request.POST or None, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            customer, customer_created = find_or_create_customer(
                form.cleaned_data, selected_customer=selected_customer,
            )
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
            quote.requested_vehicle_groups.set(form.cleaned_data["vehicle_groups"])
            comparison_ids = form.cleaned_data["vehicle_groups"].values_list(
                "comparison_classes__id", flat=True
            ).exclude(comparison_classes__id__isnull=True).distinct()
            quote.requested_vehicle_classes.set(comparison_ids)
            quote.requested_suppliers.set(form.cleaned_data["suppliers"])
        if form.cleaned_data.get("skipped_suppliers"):
            messages.warning(request, "Фирмы без машин выбранных классов не добавлены в расчёт: " + ", ".join(form.cleaned_data["skipped_suppliers"]) + ".")
        return redirect("quotes:calculate_quote" if request.POST.get("imported_inquiry") else "quotes:inquiry_saved", quote_number=quote.quote_number)
    return render(request, "quotes/new_inquiry.html", {
        "form": form, "selected_customer": selected_customer,
    })


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
        if form.cleaned_data.get("skipped_suppliers"):
            messages.warning(request, "Фирмы без машин выбранных классов не добавлены в расчёт: " + ", ".join(form.cleaned_data["skipped_suppliers"]) + ".")
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
    duplicate.requested_vehicle_groups.set(source.requested_vehicle_groups.all())
    duplicate.requested_suppliers.set(source.requested_suppliers.all())
    return redirect("quotes:edit_quote", quote_number=duplicate.quote_number)


@login_required
def calculate_quote(request, quote_number):
    quote = Quote.objects.select_related("customer").get(quote_number=quote_number)
    options = calculate_quote_options(quote)
    display_options = [option for option in options if option["available"]]
    missing_options = [option for option in options if not option["available"]]
    if request.method == "POST":
        selected_ids = {int(value) for value in request.POST.getlist("selected_options") if value.isdigit()}
        available = {option["group"].id: option for option in options if option["available"]}
        selected = [available[group_id] for group_id in selected_ids if group_id in available]
        adjustment_error = ""
        for option in selected:
            group_id = option["group"].id
            label = request.POST.get(f"manual_label_{group_id}", "").strip()
            raw_amount = request.POST.get(f"manual_amount_{group_id}", "").strip()
            try:
                amount = Decimal(raw_amount) if raw_amount else Decimal("0")
            except InvalidOperation:
                amount = Decimal("-1")
            option["manual_label"], option["manual_amount"] = label, raw_amount
            if amount < 0 or bool(label) != bool(amount):
                adjustment_error = "Для ручной доплаты заполните описание и положительную сумму."
            else:
                option["adjustment_amount"] = amount
        if not selected:
            return render(request, "quotes/calculate_quote.html", {
                "quote": quote, "options": display_options, "missing_options": missing_options,
                "selection_error": "Отметь хотя бы один рассчитанный вариант.",
            })
        if adjustment_error:
            return render(request, "quotes/calculate_quote.html", {
                "quote": quote, "options": display_options, "missing_options": missing_options,
                "selection_error": adjustment_error,
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
                        "total_price_gross": option["total"] + option["adjustment_amount"],
                        "manual_adjustment_label": option["manual_label"],
                        "manual_adjustment_amount": option["adjustment_amount"],
                        "currency": option["currency"],
                        "deposit_amount": option["deposit_amount"],
                        "deposit_currency": option["deposit_currency"],
                        "calculation_snapshot": {
                            "daily_rate": str(option["daily_rate"]), "days": option["days"],
                            "base": str(option["base"]), "extras_total": str(option["extras_total"]),
                            "season": option["season"], "day_range": option["day_range"], "lines": lines,
                            "manual_adjustment_label": option["manual_label"],
                            "manual_adjustment_amount": str(option["adjustment_amount"]),
                            "hebrew_vehicle_class": option["hebrew_vehicle_class"],
                            "body_type_label": option["body_type_label"],
                            "fuel_type_label": option["fuel_type_label"],
                            "transmission_label": option["transmission_label"],
                            "luggage_info": option["luggage_info"],
                            "included_items": option["included_items"],
                            "excluded_items": option["excluded_items"],
                        },
                        "display_order": order, "is_included": True,
                    },
                )
        return redirect("quotes:email_editor", quote_number=quote.quote_number)
    return render(
        request,
        "quotes/calculate_quote.html",
        {"quote": quote, "options": display_options, "missing_options": missing_options},
    )


@login_required
@never_cache
def quote_preview(request, quote_number):
    quote = get_object_or_404(
        Quote.objects.select_related("customer"), quote_number=quote_number
    )
    return render(request, "quotes/quote_preview.html", _quote_preview_context(quote))


@login_required
@never_cache
def copy_quote(request, quote_number):
    quote = get_object_or_404(Quote, quote_number=quote_number)
    if not quote.options.filter(is_included=True).exists():
        return JsonResponse({"error": "Сначала сохраните варианты оферты."}, status=400)
    context = _quote_preview_context(quote, is_email=True)
    return JsonResponse({
        "html": render_to_string("quotes/quote_preview.html", context),
        "text": render_to_string("quotes/quote_email.txt", context),
        "subject": quote.email_subject or f"Car rental offer {quote.quote_number}",
    })


@login_required
@never_cache
def email_editor(request, quote_number):
    quote = get_object_or_404(Quote.objects.select_related("customer"), quote_number=quote_number)
    ensure_quote_document_blocks(quote)
    if request.method == "POST" and request.POST.get("action") == "reset":
        with transaction.atomic():
            load_email_template(quote, replace=True)
        messages.success(request, "Загружен действующий шаблон. Отправленные письма сохранены в истории.")
        return redirect("quotes:email_editor", quote_number=quote.quote_number)
    data = request.POST if request.method == "POST" else None
    subject_form = EmailSubjectForm(data, instance=quote)
    blocks = BlockFormSet(data, queryset=quote.document_blocks.all(), prefix="blocks")
    options = OptionFormSet(data, queryset=quote.options.filter(is_included=True), prefix="options")
    if request.method == "POST":
        valid = [subject_form.is_valid(), blocks.is_valid(), options.is_valid()]
        if all(valid):
            with transaction.atomic():
                subject_form.save()
                blocks.save()
                options.save()
                if request.POST.get("action") == "add_block":
                    last_order = quote.document_blocks.aggregate(value=Max("display_order"))["value"] or 0
                    new_block = quote.document_blocks.create(
                        block_key=f"CUSTOM_{uuid4().hex}", title="Новый блок",
                        content="", display_order=last_order + 10, is_enabled=True,
                    )
                    messages.success(request, "Правки сохранены. Добавлен блок — заполните его заголовок и текст.")
                    return redirect(reverse("quotes:email_editor", args=[quote.quote_number]) + f"?block={new_block.pk}#block-{new_block.pk}")
            if request.POST.get("action") == "preview":
                return redirect("quotes:quote_preview", quote_number=quote.quote_number)
            messages.success(request, "Черновик письма сохранён.")
            return redirect("quotes:email_editor", quote_number=quote.quote_number)
    guides = seat_guides(quote)
    return render(request, "quotes/email_editor.html", {
        "quote": quote, "subject_form": subject_form, "blocks": blocks, "options": options,
        "guides": guides, "child_seat_text": child_seat_text(quote, guides),
        "deliveries": quote.email_deliveries.defer("html", "attachments"), "active_menu": "quotes",
    })


@login_required
def quote_guide(request, quote_number, code):
    quote = get_object_or_404(Quote, quote_number=quote_number)
    for guide in seat_guides(quote):
        if guide["code"] == code and guide["path"].is_file():
            return FileResponse(guide["path"].open("rb"), as_attachment=True, filename=guide["filename"])
    from django.http import Http404
    raise Http404


@login_required
def email_delivery(request, quote_number, delivery_id):
    delivery = get_object_or_404(QuoteEmailDelivery, pk=delivery_id, quote__quote_number=quote_number)
    response = HttpResponse(delivery.html)
    response["Content-Security-Policy"] = "sandbox; default-src 'none'; style-src 'unsafe-inline'; img-src data:"
    return response


def _quote_preview_context(quote, *, is_email=False):
    ensure_quote_document_blocks(quote)
    ensure_quote_option_presentation(quote)
    options = list(quote.options.filter(is_included=True).select_related("comparison_class"))
    is_english = quote.language == "English"
    pickup_messages = airport_pickup_messages(
        quote, {option.supplier_id for option in options}, quote.language
    )
    english_items = {
        "מחיר השכרת הרכב": "Vehicle rental price",
        "מע״מ (VAT)": "VAT",
        "ביטוח מלא עם ביטול השתתפות עצמית": "Full insurance with zero excess",
        "קילומטראז׳ ללא הגבלה": "Unlimited mileage",
        "נהג שני ללא תשלום": "Second driver free of charge",
        "נהג נוסף": "Additional driver",
        "תוספת שירות בשדה התעופה": "Airport service fee",
        "כיסא תינוק / בוסטר": "Child seat / booster",
        "מסירה או החזרה בכתובת בעיר": "Delivery or return at a city address",
        "מסירה והחזרה בעיר או בשדה התעופה": "Delivery and return in the city or at the airport",
        "אישור והרחבת כיסוי ליציאה מפולין": "Approval and extended coverage for travel outside Poland",
        "GPS / מערכת ניווט": "GPS / navigation",
        "שרשראות שלג": "Snow chains",
        "נתב Wi-Fi": "Wi-Fi router",
    }
    def translate_item(value):
        if value in english_items:
            return english_items[value]
        for source, translated in english_items.items():
            if value.startswith(source + " — "):
                details = value[len(source) + 3:]
                details = (details.replace(" ליום", " per day")
                                  .replace(" להשכרה", " per rental")
                                  .replace(" ליחידה", " per unit")
                                  .replace("מקסימום", "maximum"))
                return f"{translated} — {details}"
        return value
    for option in options:
        option.airport_pickup_message = pickup_messages.get(option.supplier_id, "")
        option.display_vehicle_class = (
            option.vehicle_group_name_snapshot
            if is_english else option.calculation_snapshot.get("hebrew_vehicle_class", option.vehicle_group_name_snapshot)
        )
        option.display_included_items = [
            translate_item(item) if is_english else item
            for item in option.calculation_snapshot.get("included_items", [])
        ]
        option.display_excluded_items = [
            translate_item(item) if is_english else item
            for item in option.calculation_snapshot.get("excluded_items", [])
        ]
    blocks = quote.document_blocks.filter(Q(is_enabled=True) | Q(block_key__in=REQUIRED_BLOCKS)).exclude(content="")
    introduction_keys = {"GREETING", "IMPORTANT", "CROSS_BORDER"}
    introduction_blocks = [block for block in blocks if block.block_key in introduction_keys]
    blocks = [block for block in blocks if block.block_key not in introduction_keys]
    guides = seat_guides(quote)
    service_labels = ({
        "AIRPORT": "Airport", "ADDRESS": "Delivery to a city address", "CITY_BRANCH": "City branch",
    } if is_english else {
        "AIRPORT": "שדה התעופה",
        "ADDRESS": "מסירה לכתובת בעיר",
        "CITY_BRANCH": "סניף בעיר",
    })
    pickup_location = f"{quote.pickup_city} — {service_labels.get(quote.pickup_service, quote.pickup_service)}"
    return_location = f"{quote.return_city} — {service_labels.get(quote.return_service, quote.return_service)}"
    if quote.pickup_address:
        pickup_location += f": {quote.pickup_address}"
    if quote.return_address:
        return_location += f": {quote.return_address}"
    return {
        "quote": quote, "options": options, "blocks": blocks,
        "pickup_location": pickup_location, "return_location": return_location,
        "is_email": is_email,
        "is_english": is_english,
        "introduction_blocks": introduction_blocks,
        "guides": guides, "child_seat_text": child_seat_text(quote, guides),
    }


@login_required
@require_POST
def send_quote(request, quote_number):
    quote = get_object_or_404(
        Quote.objects.select_related("customer"), quote_number=quote_number
    )
    email = quote.customer.email.strip()
    try:
        validate_email(email)
    except ValidationError:
        messages.error(
            request, "Нельзя отправить оферту: у клиента нет правильного email."
        )
        return redirect("quotes:quote_preview", quote_number=quote.quote_number)

    if not quote.options.filter(is_included=True).exists():
        messages.error(
            request, "Нельзя отправить оферту: сначала выберите хотя бы один вариант."
        )
        return redirect("quotes:quote_preview", quote_number=quote.quote_number)

    # Separate deliveries into new conversations so Gmail does not trim the
    # repeated offer sections as quoted text from a previous delivery.
    delivery_version = uuid4().hex[:12]
    subject = f"{quote.email_subject or ('Car rental offer ' + quote.quote_number)} | Version {delivery_version}"
    context = _quote_preview_context(quote, is_email=True)
    html = render_to_string("quotes/quote_preview.html", context)
    plain_text = render_to_string("quotes/quote_email.txt", context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=plain_text,
        to=[email],
        alternatives=[(html, "text/html")],
    )
    attachments = []
    try:
        for guide in seat_guides(quote):
            content = guide["path"].read_bytes()
            message.attach(guide["filename"], content, "application/pdf")
            attachments.append({"filename": guide["filename"], "sha256": hashlib.sha256(content).hexdigest(), "data": base64.b64encode(content).decode("ascii")})
    except OSError:
        messages.error(request, "Письмо не отправлено: не найден файл с пояснениями о креслах.")
        return redirect("quotes:email_editor", quote_number=quote.quote_number)
    try:
        if message.send(fail_silently=False) != 1:
            raise SMTPException("No message accepted")
    except (SMTPException, OSError):
        messages.error(request, "Не удалось отправить письмо. Черновик сохранён. Проверьте подключение к почте.")
        return redirect("quotes:email_editor", quote_number=quote.quote_number)
    QuoteEmailDelivery.objects.create(
        quote=quote, sent_by_user=request.user, recipient=email,
        subject=subject, html=html, attachments=attachments,
    )

    quote.status = Quote.Status.SENT
    quote.sent_by_user = request.user
    quote.sent_at = timezone.now()
    quote.sent_to_email = email
    quote.sent_subject = subject
    quote.sent_html_snapshot = html
    quote.save(update_fields=(
        "status", "sent_by_user", "sent_at", "sent_to_email", "sent_subject",
        "sent_html_snapshot", "updated_at",
    ))
    messages.success(request, f"Оферта отправлена клиенту на {email}.")
    return redirect("quotes:quote_preview", quote_number=quote.quote_number)


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
    if request.GET.get("customer_id", "").isdigit():
        customer = get_object_or_404(Customer, pk=request.GET["customer_id"])
    else:
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
