"""Operator review of current prices before converting an offer into a draft."""
import copy
import hashlib
import json
from uuid import uuid4

from django import forms
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from config.rental_duration import calculate_rental_days
from employees.models import Employee
from suppliers.models import SupplierLocation, VehicleGroup
from quotes.forms import FirstInquiryForm
from quotes.airport_pickup import airport_code_for_city
from quotes.models import Quote, QuoteOption
from quotes.services import calculate_quote_options, _active_extra_rate, _quoted_extra_price
from decimal import Decimal
from quotes.views import _quote_form_initial
from .models import Booking, BookingDriver, BookingExtra, BookingHistoryEvent
from .missing_data import MissingDepositForm, new_deposit_form, apply_deposit


class BookingFromOfferForm(FirstInquiryForm):
    vehicle_note = forms.CharField(label="Примечание к автомобилю (например, SEDAN)", max_length=200, required=False)
    flight_number = forms.CharField(label="Номер рейса", max_length=50, required=False)
    manual_adjustment_label = forms.CharField(label="Описание ручной доплаты", max_length=200, required=False)
    manual_adjustment_amount = forms.DecimalField(label="Ручная доплата", min_value=0, max_digits=10, decimal_places=2, required=False)
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        field_order = list(self.fields)
        field_order.remove("flight_number")
        field_order.insert(field_order.index("pickup_address") + 1, "flight_number")
        self.order_fields(field_order)
        self.fields["driver_count"].max_value = 20
        count_value = self.data.get("driver_count") if self.is_bound else self.initial.get("driver_count", 2)
        try:
            minimum = 1 if "entry_token" in self.fields else 2
            driver_count = min(max(int(count_value), minimum), 20)
        except (TypeError, ValueError):
            driver_count = 1
        for index in range(1, driver_count + 1):
            self.fields[f"driver_{index}_name"] = forms.CharField(
                label=f"Водитель {index} — имя и фамилия латиницей",
                max_length=201,
                required=False,
            )
            self.fields[f"driver_{index}_young"] = forms.BooleanField(
                label="Молодой водитель",
                required=False,
            )
        self.driver_name_fields = [self[f"driver_{index}_name"] for index in range(1, driver_count + 1)]
        self.driver_fields = [
            (self[f"driver_{index}_name"], self[f"driver_{index}_young"])
            for index in range(1, driver_count + 1)
        ]
        selected_extras = (
            self.data.getlist("extra_choices")
            if self.is_bound else self.initial.get("extra_choices", [])
        )
        seat_count_value = (
            self.data.get("child_seat_quantity")
            if self.is_bound else self.initial.get("child_seat_quantity", 0)
        )
        try:
            seat_count = min(max(int(seat_count_value), 0), 10)
        except (TypeError, ValueError):
            seat_count = 0
        if "CHILD_SEAT" not in selected_extras:
            seat_count = 0
        self.child_seat_fields = []
        for index in range(1, seat_count + 1):
            fields = []
            for suffix, label, max_length in (
                ("age", "Возраст ребёнка", 30),
                ("height", "Рост ребёнка (см)", 30),
                ("type_number", "Тип или номер кресла", 100),
            ):
                name = f"child_seat_{index}_{suffix}"
                self.fields[name] = forms.CharField(
                    label=label, max_length=max_length, required=False,
                )
                fields.append(self[name])
            self.child_seat_fields.append(fields)
        groups = self.fields.pop("vehicle_groups").queryset
        if "entry_token" not in self.fields:
            selected_group = self.data.get("vehicle_group") if self.is_bound else self.initial.get("vehicle_group")
            if selected_group:
                groups = VehicleGroup.objects.filter(Q(pk__in=groups.values("pk")) | Q(pk=selected_group)).distinct()
        self.fields.pop("vehicle_classes")
        self.fields.pop("suppliers")
        self.fields["vehicle_group"] = forms.ModelChoiceField(
            label="Автомобиль и фирма", queryset=groups,
        )
        for name in ("pickup_date", "return_date"):
            self.fields[name].input_formats = ["%Y-%m-%d", "%d-%m-%Y"]
            self.fields[name].widget = forms.DateInput(format="%d-%m-%Y", attrs={"placeholder": "ДД-ММ-ГГГГ", "autocomplete": "off"})

    def clean(self):
        data = super().clean()
        label, amount = data.get("manual_adjustment_label", "").strip(), data.get("manual_adjustment_amount")
        if bool(label) != (amount is not None and amount != 0):
            self.add_error("manual_adjustment_label" if not label else "manual_adjustment_amount", "Заполните описание и сумму ручной доплаты.")
        data["child_seat_details"] = [
            {
                "age": data.get(f"child_seat_{index}_age", "").strip(),
                "height": data.get(f"child_seat_{index}_height", "").strip(),
                "type_number": data.get(f"child_seat_{index}_type_number", "").strip(),
            }
            for index in range(1, len(self.child_seat_fields) + 1)
        ]
        return data

def calculate(option, data):
    inquiry = copy.copy(option.quote)
    inquiry.sub_agent = data.get("sub_agent")
    inquiry.sub_agent_id = inquiry.sub_agent.pk if inquiry.sub_agent else None
    for field in ("pickup_datetime", "return_datetime", "pickup_city", "return_city",
                  "pickup_service", "return_service", "pickup_address", "return_address",
                  "driver_count", "cross_border_requested"):
        setattr(inquiry, field, data[field])
    inquiry.rental_days = calculate_rental_days(inquiry.pickup_datetime, inquiry.return_datetime)
    inquiry.extra_requests = {
        code: data["child_seat_quantity"] if code == "CHILD_SEAT" else 1
        for code in data["extra_choices"]
    }
    young_count = sum(bool(data.get(f"driver_{index}_young")) for index in range(1, data["driver_count"] + 1))
    if young_count:
        young_extra = data["vehicle_group"].supplier.extras.filter(
            is_active=True, extra_code__in=("YOUNG_DRIVER", "YOUNG_DRIVER_21_24")
        ).order_by("pk").first()
        if young_extra:
            inquiry.extra_requests[young_extra.extra_code] = young_count
    results = calculate_quote_options(inquiry, vehicle_group=data["vehicle_group"])
    if not results or not results[0]["available"]:
        raise forms.ValidationError("Нет действующего тарифа для выбранной машины и дат. Заказ не создан.")
    result = results[0]
    manual_amount = data.get("manual_adjustment_amount") or Decimal("0.00")
    if manual_amount:
        result["manual_adjustment_label"] = data["manual_adjustment_label"]
        result["manual_adjustment_amount"] = manual_amount
        result["total"] += manual_amount
    # Apply the booking register's existing after-hours rules in the review too.
    probe = Booking(supplier=result["supplier"], pickup_datetime=inquiry.pickup_datetime,
                    return_datetime=inquiry.return_datetime)
    locations = {}
    for side in ("pickup", "return"):
        locations[side] = None
        if data[f"{side}_service"] == "AIRPORT":
            airport_code = airport_code_for_city(data[f"{side}_city"])
            locations[side] = SupplierLocation.objects.filter(
                supplier=result["supplier"], is_active=True,
                location_type="AIRPORT", **{f"supports_{side}": True},
            ).filter(Q(airport_code=airport_code) if airport_code else Q(city__iexact=data[f"{side}_city"])).first()
    result["locations"] = locations
    night_count = sum(probe._needs_after_hours_charge(data[f"{side}_datetime"], locations[side])
                      for side in ("pickup", "return"))
    if night_count:
        for extra in result["supplier"].extras.filter(is_active=True, extra_code__in=("NIGHT_SERVICE", "OUT_OF_HOURS")):
            if any(line.get("extra") == extra for line in result["extra_lines"]):
                continue
            rate = _active_extra_rate(extra, timezone.localtime(inquiry.pickup_datetime).date(), inquiry.rental_days)
            if rate is None:
                raise forms.ValidationError("Нет тарифа на обслуживание вне рабочих часов.")
            price = _quoted_extra_price(extra, rate, Decimal(inquiry.rental_days), Decimal(night_count))
            result["extra_lines"].append(dict(extra=extra, rate=rate, quantity=Decimal(night_count), price=price, name=extra.name))
            result["extras_total"] += price
            result["total"] += price
    if result["unavailable_requests"] or any(line.get("warning") for line in result["extra_lines"]):
        raise forms.ValidationError("Не удалось рассчитать все выбранные добавки. Проверьте тарифы или измените выбор.")
    codes = {line["extra"].extra_code for line in result["extra_lines"]}
    if inquiry.cross_border_requested and "CROSS_BORDER" not in codes:
        raise forms.ValidationError("Нет тарифа на выезд за границу. Уточните условия перед созданием заказа.")
    if inquiry.driver_count > 2 and "ADDITIONAL_DRIVER" not in codes:
        raise forms.ValidationError("Нет тарифа для дополнительных водителей.")
    if any(line["rate"].currency != result["currency"] for line in result["extra_lines"]):
        raise forms.ValidationError("Валюта добавок отличается от валюты аренды. Проверьте тарифы.")
    for line in result["extra_lines"]:
        if any(key in (line["rate"].formula_config or {}) for key in ("per_km_gross", "per_missing_liter_gross", "plus")):
            raise forms.ValidationError("Добавка требует дополнительных данных для расчёта. Уточните её тариф.")
    return result


def review_snapshot(option, data, result):
    values = {key: (value.pk if hasattr(value, "_meta") else value) for key, value in data.items() if key != "vehicle_group"}
    values["vehicle_group"] = data["vehicle_group"].pk
    payload = {
        "option_id": option.pk, "quote_number": option.quote.quote_number,
        "original_total": str(option.total_price_gross), "original_currency": option.currency,
        "request": values, "total": str(result["total"]), "currency": result["currency"],
        "rate_id": result["vehicle_rate"].pk, "base": str(result["base"]),
        "deposit": str(result["deposit_amount"]), "deposit_currency": result["deposit_currency"],
        "locations": {side: location.pk if location else None for side, location in result["locations"].items()},
        "extras": [{"extra_id": line["extra"].pk, "rate_id": line["rate"].pk,
                    "quantity": str(line["quantity"]), "price": str(line["price"]),
                    "name": line["name"]} for line in result["extra_lines"]],
    }
    return json.loads(json.dumps(payload, cls=DjangoJSONEncoder))


def fingerprint(snapshot):
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def create_draft(option, data, result, snapshot, user):
    """Called only inside the locked review transaction, after signed confirmation."""
    booking = Booking(customer=option.quote.customer, source_quote=option.quote if option.quote.pk else None,
                      source_quote_snapshot=snapshot, supplier=result["supplier"],
                      vehicle_group=result["group"], currency=result["currency"],
                      pickup_datetime=data["pickup_datetime"], return_datetime=data["return_datetime"],
                      sub_agent=data.get("sub_agent"),
                      order_source="SUBAGENT" if data.get("sub_agent") else "SELF")
    labels = dict(FirstInquiryForm.SERVICE_CHOICES)
    for side in ("pickup", "return"):
        setattr(booking, f"{side}_location", result["locations"][side])
        setattr(booking, f"{side}_location_text", f"{data[side + '_city']} — {labels[data[side + '_service']]}")
        setattr(booking, f"{side}_address", data[f"{side}_address"])
    actor = Employee.objects.filter(login_user=user).first()
    booking.created_by_employee = actor
    booking.created_by_user = user
    booking._history_actor = actor
    booking.save()
    # The reviewed calculation is authoritative. Native save creates mandatory
    # extras; replace those with the exact current rates and quantities reviewed.
    booking.extras.all().delete()
    entries = []
    for line in result["extra_lines"]:
        rate, extra = line["rate"], line["extra"]
        entries.append(BookingExtra(
            booking=booking, extra=extra, rate=rate, quantity=line["quantity"],
            customer_visible_name=extra.name, supplier_visible_name=extra.name,
            calculation_type_snapshot=rate.calculation_type,
            unit_price_gross_snapshot=rate.amount_gross,
            minimum_amount_gross_snapshot=rate.minimum_amount_gross,
            maximum_amount_gross_snapshot=rate.maximum_amount_gross,
            calculated_price_gross=line["price"], currency_snapshot=rate.currency,
            formula_snapshot=rate.formula_config, is_mandatory_snapshot=extra.is_mandatory,
        ))
    BookingExtra.objects.bulk_create(entries)
    rate = result["vehicle_rate"]
    updates = {
        "vehicle_rate": rate, "vehicle_daily_rate_gross_snapshot": result["daily_rate"],
        "calculated_vehicle_price_gross": result["base"], "vehicle_price_gross": result["base"],
        "price_list_version_snapshot": rate.season.price_list.version,
        "price_season_snapshot": result["season"], "price_day_range_snapshot": result["day_range"],
        "price_calculation_status": Booking.PriceCalculationStatus.CALCULATED,
        "customer_name_snapshot": " ".join(filter(None, [data["first_name"], data["last_name"]])),
        "wants_invoice_snapshot": data["wants_invoice"],
        "flight_number": data.get("flight_number", ""),
        "child_seat_details": data.get("child_seat_details", []),
        "subagent_price_adjustment_amount": result.get("subagent_adjustment", Decimal("0.00")),
    }
    for field in ("email", "phone_1", "phone_2", "phone_3", "country", "address"):
        updates[f"customer_{field}_snapshot"] = data[field]
    for field in ("invoice_name", "invoice_tax_id", "invoice_address", "invoice_email"):
        updates[f"{field}_snapshot"] = data[field]
    Booking.objects.filter(pk=booking.pk).update(**updates)
    Booking.objects.filter(pk=booking.pk).update(
        manual_adjustment_label=data.get("manual_adjustment_label", ""),
        manual_adjustment_amount=data.get("manual_adjustment_amount") or Decimal("0.00"),
    )
    booking.refresh_from_db()
    booking.recalculate_totals()
    if "driver_1_name" in data:
        drivers = []
        for index in range(1, data["driver_count"] + 1):
            full_name = data.get(f"driver_{index}_name", "").strip()
            if full_name:
                parts = full_name.split(maxsplit=1)
                drivers.append(BookingDriver(
                    booking=booking, first_name=parts[0],
                    last_name=parts[1] if len(parts) > 1 else "",
                    role="MAIN" if index == 1 else "ADDITIONAL", display_order=index,
                    young_driver_status=bool(data.get(f"driver_{index}_young")),
                ))
        BookingDriver.objects.bulk_create(drivers)
    booking.log_history(BookingHistoryEvent.EventType.DETAILS_CHANGED,
                        f"Created from {option.quote.quote_number}; current price confirmed",
                        changes={**snapshot, "operator_user_id": user.pk}, created_by=actor)
    return booking


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def from_offer(request, quote_number, option_id):
    # Serialize conversion and protect each confirmed form from a double submit.
    quote = get_object_or_404(Quote.objects.select_for_update(), quote_number=quote_number)
    option = get_object_or_404(QuoteOption.objects.select_related("quote__customer"),
                             pk=option_id, quote=quote, is_included=True)
    initial = _quote_form_initial(quote)
    initial.update(vehicle_group=option.vehicle_group_id,
                   pickup_date=timezone.localtime(quote.pickup_datetime).date(),
                   return_date=timezone.localtime(quote.return_datetime).date(),
                   manual_adjustment_label=option.manual_adjustment_label,
                   manual_adjustment_amount=option.manual_adjustment_amount or None)
    form = BookingFromOfferForm(request.POST or None, initial=initial)
    result = snapshot = token = None
    deposit_form = None
    deposit_pending = False
    deposit_once = False
    if request.method == "POST" and form.is_valid():
        try:
            result = calculate(option, form.cleaned_data)
            if result["deposit_amount"] is None:
                if request.POST.get("deposit-context") and request.POST.get("action") != "reset_deposit":
                    deposit_form = MissingDepositForm(request.POST, user=request.user, prefix="deposit")
                    resolved = apply_deposit(deposit_form, result, option, request.user,
                                            save_permanently=request.POST.get("action") == "resolve_deposit")
                    deposit_pending = not resolved
                    deposit_once = resolved and deposit_form.cleaned_data["usage"] == "once"
                    if resolved and not deposit_once:
                        deposit_form = None
                else:
                    deposit_form = new_deposit_form(result["group"], option, request.user)
                    deposit_pending = True
            elif request.POST.get("action") == "resolve_deposit":
                form.add_error(None, "Депозит уже заполнен в базе. Проверьте актуальное значение в расчёте.")
            if deposit_pending:
                raise forms.ValidationError("Укажите отсутствующий депозит перед созданием заказа.")
            snapshot = review_snapshot(option, form.cleaned_data, result)
            if deposit_once:
                snapshot["deposit_usage"] = "once"
            stamp = {"fingerprint": fingerprint(snapshot), "user": request.user.pk}
            if request.POST.get("action") == "create":
                try:
                    previous = signing.loads(request.POST.get("review_token", ""), salt="booking-review", max_age=3600)
                except signing.BadSignature:
                    previous = None
                valid_review = bool(
                    previous
                    and previous.get("fingerprint") == stamp["fingerprint"]
                    and previous.get("user") == stamp["user"]
                    and previous.get("nonce")
                )
                if valid_review and request.POST.get("confirm_price") == "yes":
                    existing = Booking.objects.filter(
                        source_quote=quote,
                        source_quote_snapshot__conversion_nonce=previous["nonce"],
                    ).first()
                    if existing:
                        return redirect("quotes:booking_detail", pk=existing.pk)
                    snapshot["conversion_nonce"] = previous["nonce"]
                    booking = create_draft(option, form.cleaned_data, result, snapshot, request.user)
                    quote.status = Quote.Status.ACCEPTED
                    quote.save(update_fields=["status", "updated_at"])
                    return redirect("quotes:booking_detail", pk=booking.pk)
                form.add_error(None, "Проверьте актуальный расчёт и подтвердите его. Данные или тариф могли измениться.")
            stamp["nonce"] = uuid4().hex
            token = signing.dumps(stamp, salt="booking-review")
        except forms.ValidationError as error:
            form.add_error(None, error)
    changed = result and (result["total"] != option.total_price_gross or result["currency"] != option.currency)
    delta = result["total"] - option.total_price_gross if result and result["currency"] == option.currency else None
    return render(request, "bookings/from_offer.html", {
        "form": form, "option": option, "quote": quote, "result": result,
        "review_token": token, "changed": changed, "delta": delta, "active_menu": "orders",
        "deposit_form": deposit_form, "deposit_pending": deposit_pending, "deposit_once": deposit_once,
    })
