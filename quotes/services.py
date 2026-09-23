from decimal import Decimal

from django.db.models import Q
from django.utils import timezone

from customers.models import Customer
from suppliers.models import (
    PriceList,
    SupplierExtraRate,
    VehicleComparisonClass,
    VehicleRate,
)
from .models import QuoteDocumentBlock, QuoteTemplate


HEBREW_VEHICLE_CLASS_NAMES = {
    "B_MANUAL": "קבוצה B — האצ׳בק, ידני",
    "B_AUTO": "קבוצה B — האצ׳בק, אוטומטי",
    "C_MANUAL_HATCH": "קבוצה C — האצ׳בק, ידני",
    "C_MANUAL_SEDAN": "קבוצה C — סדאן, ידני",
    "C_AUTO_HATCH": "קבוצה C — האצ׳בק, אוטומטי",
    "C_AUTO_SEDAN": "קבוצה C — סדאן, אוטומטי",
    "C_WAGON_AUTO": "קבוצה C — סטיישן, אוטומטי",
    "D_SEDAN_AUTO": "קבוצה D — סדאן, אוטומטי",
    "D_WAGON_AUTO": "קבוצה D — סטיישן, אוטומטי",
    "SUV_SMALL_AUTO": "SUV קטן — אוטומטי",
    "SUV_MEDIUM_AUTO": "SUV בינוני — אוטומטי",
    "SUV_BIG_AUTO": "SUV גדול — אוטומטי",
    "SUV_7_AUTO": "SUV עם 7 מקומות — אוטומטי",
    "PREMIUM_SEDAN_AUTO": "סדאן פרימיום — אוטומטי",
    "PREMIUM_SUV_AUTO": "SUV פרימיום — אוטומטי",
    "PASSENGER_VAN_AUTO": "רכב נוסעים 8–9 מקומות — אוטומטי",
}


def vehicle_class_presentation(comparison, group):
    """Avoid promising one body type when a supplier group covers several."""
    title = HEBREW_VEHICLE_CLASS_NAMES.get(comparison.code, comparison.name)
    comparison_codes = {item.code for item in group.comparison_classes.all()}
    mixed_bodies = (
        any("HATCH" in code for code in comparison_codes)
        and any("SEDAN" in code for code in comparison_codes)
    )
    if mixed_bodies:
        return title.split(" — ", 1)[0], ""
    return title, group.get_body_type_display() if group.body_type else ""

STANDARD_INCLUDED_ITEMS = [
    "ביטוח מלא עם ביטול השתתפות עצמית",
    "קילומטראז׳ ללא הגבלה",
    "נהג שני ללא תשלום",
]


def normalize_included_items(items):
    """Use the same standard benefits, retaining other selected extras."""
    legacy_standard_items = {
        "עד שני נהגים", "חבילת With Comfort Package",
        "ביטוח מלא עם ביטול השתתפות - SCDW", "ללא הגבלת ק״מ",
    }
    return list(dict.fromkeys([
        "מחיר השכרת הרכב", "מע״מ (VAT)", *STANDARD_INCLUDED_ITEMS,
        *(item for item in items if item not in legacy_standard_items),
    ]))


HEBREW_EXTRA_NAMES = {
    "ADDITIONAL_DRIVER": "נהג נוסף",
    "AIRPORT_FEE": "תוספת שירות בשדה התעופה",
    "BABY_SEAT_BOOSTER": "כיסא תינוק / בוסטר",
    "CHILD_SEAT": "כיסא תינוק / בוסטר",
    "CITY_ADDRESS_DELIVERY": "מסירה או החזרה בכתובת בעיר",
    "CITY_AIRPORT_DELIVERY": "מסירה והחזרה בעיר או בשדה התעופה",
    "CROSS_BORDER": "אישור והרחבת כיסוי ליציאה מפולין",
    "DELIVERY_RETURN": "מסירה והחזרה בעיר או בשדה התעופה",
    "GPS": "GPS / מערכת ניווט",
    "NAVIGATION": "GPS / מערכת ניווט",
    "SNOW_CHAINS": "שרשראות שלג",
    "WIFI_ROUTER": "נתב Wi-Fi",
}


def find_or_create_customer(data, *, selected_customer=None):
    match = Q()
    if data.get("email"):
        match |= Q(email__iexact=data["email"].strip())
    for field in ("phone_1", "phone_2", "phone_3"):
        if data.get(field):
            phone = data[field].strip()
            match |= Q(phone_1=phone) | Q(phone_2=phone) | Q(phone_3=phone)

    customer = selected_customer or Customer.objects.filter(match).first()
    values = {
        field: data.get(field, "")
        for field in (
            "first_name", "last_name", "email", "phone_1", "phone_2", "phone_3",
            "country", "preferred_language", "address", "invoice_name", "invoice_tax_id",
            "invoice_address", "invoice_email",
        )
    }
    values["wants_invoice"] = data.get("wants_invoice", False)

    if customer:
        for field, value in values.items():
            if value:
                setattr(customer, field, value)
        customer.save()
        return customer, False
    return Customer.objects.create(**values), True


def _extra_price(rate, days, quantity=Decimal("1")):
    formula = rate.formula_config or {}
    if rate.calculation_type == "FORMULA":
        if "total_per_rental_gross" in formula:
            unit_price = Decimal(str(formula["total_per_rental_gross"]))
        else:
            base = Decimal(str(formula.get("per_rental_gross", rate.amount_gross)))
            per_day = Decimal(str(formula.get("per_rental_day_gross", 0)))
            unit_price = base + per_day * days
    elif rate.calculation_type in ("PER_DAY", "PER_DRIVER_DAY"):
        unit_price = rate.amount_gross * days
    else:
        unit_price = rate.amount_gross

    minimum = getattr(rate, "minimum_amount_gross", None)
    maximum = getattr(rate, "maximum_amount_gross", None)
    if minimum is not None:
        unit_price = max(unit_price, minimum)
    if maximum is not None:
        unit_price = min(unit_price, maximum)
    return unit_price * quantity


def _quoted_extra_price(extra, rate, days, quantity=Decimal("1")):
    return _extra_price(rate, days, quantity)


def _extra_line_name(extra, quantity):
    name = HEBREW_EXTRA_NAMES.get(extra.extra_code, extra.name)
    if extra.extra_code in {"BABY_SEAT_BOOSTER", "CHILD_SEAT"}:
        return f"{name} × {int(quantity)}"
    if quantity > 1:
        return f"{name} × {int(quantity)}"
    return name


def _luggage_info(group):
    if group.luggage_volume_liters:
        return f"נפח תא מטען משוער: לפחות {group.luggage_volume_liters} ליטר"
    pieces = []
    if group.luggage_large is not None:
        pieces.append(f"{group.luggage_large} מזוודות גדולות")
    if group.luggage_small is not None:
        pieces.append(f"{group.luggage_small} מזוודות קטנות")
    if pieces:
        return "קיבולת תא מטען משוערת: " + " + ".join(pieces)
    if group.cargo_note:
        return group.cargo_note
    return ""


def _rate_description(rate):
    formula = rate.formula_config or {}
    if "per_rental_gross" in formula or "per_rental_day_gross" in formula:
        base = Decimal(str(formula.get("per_rental_gross", rate.amount_gross)))
        per_day = Decimal(str(formula.get("per_rental_day_gross", 0)))
        return f"{base} PLN + {per_day} PLN ליום"
    suffix = {
        "PER_DAY": " ליום",
        "PER_DRIVER_DAY": " ליום",
        "PER_RENTAL": " להשכרה",
        "PER_UNIT": " ליחידה",
        "FIXED": "",
    }.get(rate.calculation_type, "")
    maximum = (
        f", מקסימום {rate.maximum_amount_gross} PLN"
        if rate.maximum_amount_gross is not None else ""
    )
    return f"{rate.amount_gross} PLN{suffix}{maximum}"


def _active_extra_rate(extra, pickup_date, days):
    return extra.rates.filter(
        is_active=True,
        valid_from__lte=pickup_date,
    ).filter(
        Q(valid_to__isnull=True) | Q(valid_to__gte=pickup_date),
        Q(days_from__isnull=True) | Q(days_from__lte=days),
        Q(days_to__isnull=True) | Q(days_to__gte=days),
        location__isnull=True,
    ).order_by("-priority", "-valid_from").first()


def _service_extra_requests(quote, supplier_code):
    requests = {}
    address_sides = sum(
        service == "ADDRESS"
        for service in (quote.pickup_service, quote.return_service)
    )
    if supplier_code in {"01", "03"} and address_sides:
        requests["CITY_ADDRESS_DELIVERY"] = Decimal(address_sides)
    if supplier_code == "02" and quote.pickup_service == "AIRPORT":
        requests["AIRPORT_FEE"] = Decimal("1")
    return requests


def _missing_rate_reason(group, pickup_date, days):
    rates = VehicleRate.objects.filter(
        is_active=True, vehicle_group=group.effective_rate_group,
        season__is_active=True, season__price_list__status="ACTIVE",
        day_range__is_active=True, day_range__days_from__lte=days,
    ).filter(Q(day_range__days_to__isnull=True) | Q(day_range__days_to__gte=days)).select_related(
        "season__price_list"
    )
    coverage_ends = []
    for rate in rates:
        ends = [end for end in (
            rate.season.price_list.effective_to, rate.season.rental_date_to
        ) if end is not None]
        if not ends:
            return "Для выбранной даты пока нет подтверждённой цены. Проверьте ценник поставщика."
        coverage_ends.append(min(ends))
    if coverage_ends and max(coverage_ends) < pickup_date:
        return f"Последний загруженный тариф действует до {max(coverage_ends):%d.%m.%Y}. Для выбранной даты нужна новая цена поставщика."
    return "Для выбранной даты пока нет подтверждённой цены. Проверьте ценник поставщика."


def calculate_quote_options(quote, *, vehicle_group=None):
    pickup_date = timezone.localtime(quote.pickup_datetime).date()
    requested_group_ids = {vehicle_group.pk} if vehicle_group else set(
        quote.requested_vehicle_groups.values_list("id", flat=True)
    )
    comparisons = (vehicle_group.comparison_classes if vehicle_group else quote.requested_vehicle_classes).prefetch_related(
        "vehicle_groups__supplier", "vehicle_groups__models", "vehicle_groups__comparison_classes"
    ).all()
    if not comparisons and quote.vehicle_request:
        comparisons = VehicleComparisonClass.objects.prefetch_related(
            "vehicle_groups__supplier", "vehicle_groups__models", "vehicle_groups__comparison_classes"
        ).filter(code=quote.vehicle_request)
    requested_supplier_ids = {vehicle_group.supplier_id} if vehicle_group else set(quote.requested_suppliers.values_list("id", flat=True))
    selected_supplier_ids = {vehicle_group.supplier_id} if vehicle_group else set(
        quote.requested_vehicle_groups.values_list("supplier_id", flat=True)
    )
    suppliers_missing_groups = requested_supplier_ids - selected_supplier_ids if requested_group_ids else set()
    results = []
    for comparison in comparisons:
      groups = comparison.vehicle_groups.filter(is_active=True)
      if requested_group_ids:
        groups = groups.filter(Q(id__in=requested_group_ids) | Q(supplier_id__in=suppliers_missing_groups))
      for group in groups:
        if requested_supplier_ids and group.supplier_id not in requested_supplier_ids:
            continue
        vehicle_title, body_type_label = vehicle_class_presentation(comparison, group)
        use_subagent_prices = bool(
            getattr(quote, "sub_agent_id", None)
            and group.supplier.subagent_pricing_method
            == group.supplier.SubagentPricingMethod.DEDICATED
        )
        price_audience = (
            PriceList.Audience.SUBAGENT if use_subagent_prices
            else PriceList.Audience.STANDARD
        )
        rate = VehicleRate.objects.filter(
            is_active=True,
            vehicle_group=group.effective_rate_group,
            season__is_active=True,
            season__price_list__status="ACTIVE",
            season__price_list__audience=price_audience,
            season__price_list__effective_from__lte=pickup_date,
            season__rental_date_from__lte=pickup_date,
            day_range__is_active=True,
            day_range__days_from__lte=quote.rental_days,
        ).filter(
            Q(season__price_list__effective_to__isnull=True) | Q(season__price_list__effective_to__gte=pickup_date),
            Q(season__rental_date_to__isnull=True) | Q(season__rental_date_to__gte=pickup_date),
            Q(day_range__days_to__isnull=True) | Q(day_range__days_to__gte=quote.rental_days),
        ).select_related("season__price_list", "day_range").order_by(
            "-season__price_list__effective_from", "-season__priority"
        ).first()
        if not rate:
            results.append({
                "comparison": comparison,
                "supplier": group.supplier,
                "group": group,
                "models": ", ".join(str(model) for model in group.models.filter(is_active=True)[:4]),
                "body_type_label": body_type_label,
                "fuel_type_label": group.fuel_type_note,
                "transmission_label": (
                    group.get_transmission_display()
                    if group.transmission != group.Transmission.UNKNOWN else ""
                ),
                "available": False,
                "reason": _missing_rate_reason(group, pickup_date, quote.rental_days),
                "total": None,
            })
            continue
        base = rate.daily_rate_gross * quote.rental_days
        lines = []
        extras_total = Decimal("0.00")
        requested_code_map = {
            "CHILD_SEAT": {"01": "CHILD_SEAT", "02": "CHILD_SEAT", "03": "BABY_SEAT_BOOSTER"},
            "SNOW_CHAINS": {"01": "SNOW_CHAINS", "02": "SNOW_CHAINS", "03": "SNOW_CHAINS"},
            "NAVIGATION": {"01": "NAVIGATION", "02": "GPS"},
            "WIFI_ROUTER": {"01": "WIFI_ROUTER"},
        }
        supplier_code = group.supplier.supplier_code
        requested_supplier_codes = {
            mapping[supplier_code]: Decimal(str(quote.extra_requests[canonical_code]))
            for canonical_code, mapping in requested_code_map.items()
            if canonical_code in quote.extra_requests and supplier_code in mapping
        }
        # Some booking-only requests already use the supplier's own configured
        # code (for example a young-driver fee), so they need no translation.
        direct_codes = set(group.supplier.extras.filter(
            is_active=True, extra_code__in=quote.extra_requests,
        ).values_list("extra_code", flat=True))
        requested_supplier_codes.update({
            code: Decimal(str(quote.extra_requests[code])) for code in direct_codes
        })
        requested_supplier_codes.update(
            _service_extra_requests(quote, supplier_code)
        )
        extras = group.supplier.extras.filter(is_active=True).filter(
            Q(is_mandatory=True)
            | Q(extra_code="ADDITIONAL_DRIVER")
            | Q(extra_code="CROSS_BORDER")
            | Q(extra_code__in=requested_supplier_codes)
        )
        for extra in extras:
            quantity = Decimal("1")
            if extra.extra_code == "ADDITIONAL_DRIVER":
                quantity = Decimal(max(quote.driver_count - 2, 0))
                if not quantity:
                    continue
            elif extra.extra_code == "CROSS_BORDER" and not quote.cross_border_requested:
                continue
            elif extra.extra_code in requested_supplier_codes:
                quantity = requested_supplier_codes[extra.extra_code]
            elif not extra.is_mandatory and extra.extra_code not in {"ADDITIONAL_DRIVER", "CROSS_BORDER"}:
                continue
            extra_rate = _active_extra_rate(extra, pickup_date, quote.rental_days)
            if not extra_rate:
                lines.append({
                    "name": _extra_line_name(extra, quantity),
                    "warning": "Нет подходящего тарифа",
                })
                continue
            price = _quoted_extra_price(
                extra, extra_rate, Decimal(quote.rental_days), quantity
            )
            extras_total += price
            lines.append({
                "name": _extra_line_name(extra, quantity),
                "price": price,
                "extra": extra,
                "rate": extra_rate,
                "quantity": quantity,
            })
        unavailable_requests = []
        for canonical_code, quantity in quote.extra_requests.items():
            supplier_extra_code = (canonical_code if canonical_code in direct_codes else
                                   requested_code_map.get(canonical_code, {}).get(supplier_code))
            if not supplier_extra_code:
                unavailable_requests.append(canonical_code)
            elif not extras.filter(extra_code=supplier_extra_code).exists():
                unavailable_requests.append(canonical_code)
        included_items = normalize_included_items(
            line["name"] for line in lines if line.get("price") is not None
        )

        optional_labels = {
            "CHILD_SEAT": "כיסא תינוק / בוסטר",
            "SNOW_CHAINS": "שרשראות שלג",
            "NAVIGATION": "GPS / מערכת ניווט",
            "WIFI_ROUTER": "נתב Wi-Fi",
            "CROSS_BORDER": "אישור והרחבת כיסוי ליציאה מפולין",
        }
        not_requested = set(optional_labels) - set(quote.extra_requests)
        if quote.cross_border_requested:
            not_requested.discard("CROSS_BORDER")
        excluded_items = []
        for canonical_code in optional_labels:
            if canonical_code not in not_requested:
                continue
            supplier_extra_code = (
                "CROSS_BORDER" if canonical_code == "CROSS_BORDER"
                else requested_code_map.get(canonical_code, {}).get(supplier_code)
            )
            if not supplier_extra_code:
                continue
            optional_extra = group.supplier.extras.filter(
                is_active=True, extra_code=supplier_extra_code
            ).first()
            if not optional_extra:
                continue
            optional_rate = _active_extra_rate(optional_extra, pickup_date, quote.rental_days)
            if optional_rate:
                excluded_items.append(
                    f"{optional_labels[canonical_code]} — {_rate_description(optional_rate)}"
                )
        subtotal = base + extras_total
        subagent_adjustment = Decimal("0.00")
        if (
            getattr(quote, "sub_agent_id", None)
            and group.supplier.subagent_pricing_method
            == group.supplier.SubagentPricingMethod.PERCENT_TOTAL
        ):
            subagent_adjustment = (
                subtotal * group.supplier.subagent_markup_percent / Decimal("100")
            ).quantize(Decimal("0.01"))
        results.append({
            "comparison": comparison,
            "supplier": group.supplier,
            "group": group,
            "models": ", ".join(str(model) for model in group.models.filter(is_active=True)[:4]),
            "daily_rate": rate.daily_rate_gross,
            "vehicle_rate": rate,
            "days": quote.rental_days,
            "base": base,
            "extra_lines": lines,
            "unavailable_requests": unavailable_requests,
            "extras_total": extras_total,
            "total": subtotal + subagent_adjustment,
            "subagent_adjustment": subagent_adjustment,
            "subagent_pricing_method": (
                group.supplier.subagent_pricing_method
                if getattr(quote, "sub_agent_id", None) else ""
            ),
            "price_audience": price_audience,
            "season": rate.season.season_name,
            "day_range": rate.day_range.label,
            "currency": rate.currency,
            "deposit_amount": group.effective_deposit_amount,
            "deposit_currency": group.effective_rate_group.deposit_currency,
            "hebrew_vehicle_class": vehicle_title,
            "body_type_label": body_type_label,
            "fuel_type_label": group.fuel_type_note,
            "transmission_label": (
                group.get_transmission_display()
                if group.transmission != group.Transmission.UNKNOWN else ""
            ),
            "luggage_info": _luggage_info(group),
            "included_items": included_items,
            "excluded_items": excluded_items,
            "available": True,
        })
    return sorted(results, key=lambda item: (
        item["comparison"].display_order,
        not item["available"],
        item["total"] if item["total"] is not None else Decimal("999999999"),
    ))


def ensure_quote_option_presentation(quote):
    """Add client-facing fields to options saved before those fields existed."""
    calculated_by_group = {
        option["group"].id: option
        for option in calculate_quote_options(quote)
        if option["available"]
    }
    for saved_option in quote.options.filter(is_included=True):
        snapshot = dict(saved_option.calculation_snapshot or {})
        calculated = calculated_by_group.get(saved_option.vehicle_group_id)
        group = saved_option.vehicle_group
        fallback_title, fallback_body = vehicle_class_presentation(saved_option.comparison_class, group)
        snapshot["body_type_label"] = (
            calculated["body_type_label"] if calculated else
            fallback_body
        )
        snapshot["transmission_label"] = (
            calculated["transmission_label"] if calculated else
            group.get_transmission_display()
            if group.transmission != group.Transmission.UNKNOWN else ""
        )
        snapshot["fuel_type_label"] = (
            calculated["fuel_type_label"] if calculated else group.fuel_type_note
        )
        if not calculated:
            if group.body_type and not fallback_body:
                snapshot["hebrew_vehicle_class"] = fallback_title
            snapshot["included_items"] = normalize_included_items(snapshot.get("included_items", []))
            saved_option.calculation_snapshot = snapshot
            saved_option.save(update_fields=["calculation_snapshot"])
            continue
        snapshot["hebrew_vehicle_class"] = calculated["hebrew_vehicle_class"]
        snapshot["luggage_info"] = calculated["luggage_info"]
        snapshot["included_items"] = calculated["included_items"]
        snapshot["excluded_items"] = calculated["excluded_items"]
        saved_option.calculation_snapshot = snapshot
        if saved_option.deposit_amount is None and calculated["deposit_amount"] is not None:
            saved_option.deposit_amount = calculated["deposit_amount"]
            saved_option.deposit_currency = calculated["deposit_currency"]
            saved_option.save(update_fields=[
                "calculation_snapshot", "deposit_amount", "deposit_currency"
            ])
            continue
        saved_option.calculation_snapshot = snapshot
        saved_option.save(update_fields=["calculation_snapshot"])


def ensure_quote_document_blocks(quote):
    from .email_tools import load_email_template, ensure_required_blocks
    if quote.document_blocks.exists():
        ensure_required_blocks(quote)
        return
    load_email_template(quote)
