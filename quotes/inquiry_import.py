"""Read the labelled Hebrew website form without contacting the website."""
import html
import re
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .forms import FirstInquiryForm


def parse_inquiry(raw):
    text = html.unescape(raw).replace("\\", "").replace("\u00a0", " ")
    lines = [line.strip().strip("*").strip() for line in text.splitlines()]
    fields, sections, section = {}, {}, ""
    for line in lines:
        if line.rstrip(":") in ("קבלת הרכב", "החזרת הרכב"):
            section = "pickup" if line.startswith("קבלת") else "return"
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
            if section and key.strip() in ("עיר", "מקום", "תאריך", "שעה"):
                sections[(section, key.strip())] = value.strip()
    warnings = []
    data = {"customer_notes": raw, "preferred_language": "Hebrew", "driver_count": 1,
            "first_name": fields.get("שם", ""), "last_name": "",
            "email": fields.get("דוא״ל", fields.get('דוא"ל', "")),
            "phone_1": fields.get("טלפון / וואטסאפ", ""), "extra_choices": []}
    cities = {"קרקוב": "Kraków", "קראקוב": "Kraków", "ורשה": "Warszawa", "וורשה": "Warszawa",
              "קטוביץ": "Katowice", "גדנסק": "Gdańsk", "ורוצלב": "Wrocław",
              "פוזנן": "Poznań", "לובלין": "Lublin", "ז'שוב": "Rzeszów"}
    for side in ("pickup", "return"):
        city = sections.get((side, "עיר"), "")
        data[f"{side}_city"] = cities.get(city, city)
        place = sections.get((side, "מקום"), "")
        if "שדה תעופה" in place:
            data[f"{side}_service"] = "AIRPORT"
        elif "מלון" in place or "כתובת" in place:
            data[f"{side}_service"] = "ADDRESS"
        else:
            data[f"{side}_service"] = {"סניף": "CITY_BRANCH"}.get(place, "")
        data[f"{side}_address"] = (
            place if data[f"{side}_service"] == "ADDRESS" and place not in {"מלון", "כתובת"} else ""
        )
        if "מלון" in place:
            warnings.append("Уточните название и точный адрес отеля перед отправкой предложения.")
        date = sections.get((side, "תאריך"), "")
        try:
            date = datetime.strptime(date, "%Y-%m-%d").strftime("%d-%m-%Y")
        except ValueError:
            warnings.append("Проверьте даты получения и возврата: ожидается дата ГГГГ-ММ-ДД в заявке.")
            date = ""
        data[f"{side}_date"] = date
        data[f"{side}_time"] = sections.get((side, "שעה"), "")
    def answer(label):
        match = re.search(r"^" + re.escape(label) + r"\s*:\s*(כן|לא)\s*$", text, re.M)
        return match.group(1) if match else ""
    data["cross_border_requested"] = answer("יציאה מחוץ לפולין") == "כן"
    if not answer("יציאה מחוץ לפולין"):
        warnings.append("Уточните, планируется ли выезд за границу.")
    for label, code in (("כיסאות / בוסטרים", "CHILD_SEAT"), ("GPS", "NAVIGATION"), ("שרשראות שלג", "SNOW_CHAINS")):
        if answer(label) == "כן":
            data["extra_choices"].append(code)
    if "צריך המלצה" in fields.get("שרשראות שלג", ""):
        warnings.append("Клиент просит рекомендацию по цепям для снега. Уточните у поставщика перед ответом; цепи не добавлены автоматически.")
    quantity = fields.get("מספר כיסאות / בוסטרים", "")
    data["child_seat_quantity"] = quantity if quantity.isdigit() else ""
    if "ילדים" in text or "כיסא תינוק" in text or "CHILD_SEAT" in data["extra_choices"]:
        warnings.append("Проверьте кресла и бустеры для всех детей, включая собственные. Платные кресла отмечены только при ответе «да».")
    if fields.get("כל נהג מעל גיל 24 ועם לפחות שנה רישיון") != "כן":
        warnings.append("Уточните возраст и стаж каждого водителя; условия зависят от фирмы.")
    passengers = fields.get("מספר נוסעים כולל הנהג", "")
    bags = fields.get("מספר מזוודות משוער", "")
    requirements = {"passengers": int(passengers) if passengers.isdigit() else None,
                    "bags": int(bags) if bags.isdigit() else None,
                    "automatic": "אוטומטית" in fields.get("תיבת הילוכים", ""),
                    "manual": "ידנית" in fields.get("תיבת הילוכים", ""),
                    "categories": [item.strip() for item in re.findall(r"^\s*-\s*(.+)$", text, re.M)]}
    if any("היברידי" in category for category in requirements["categories"]):
        warnings.append("Тип двигателя (гибрид) не указан в данных поставщиков. Проверьте его вручную перед отправкой предложения.")
    drivers = re.search(r"\b(\d+)\s+נהגים", text)
    if drivers:
        data["driver_count"] = int(drivers.group(1))
    else:
        warnings.append("Количество водителей принято равным 1 — измените при необходимости.")
    warnings.append("Вместимость багажа нужно подтвердить у поставщика. Выбранные категории не подтверждают наличие машины.")
    if not requirements["passengers"]:
        warnings.append("Число пассажиров не распознано: выберите категории вручную.")
    data["internal_notes"] = "Заявка: " + fields.get("מספר פנייה", "без номера") + "\n" + "\n".join(warnings)
    return data, requirements, warnings


def suitable_group(group, requirements):
    seats = requirements["passengers"]
    if not seats or (group.seats is not None and group.seats < seats):
        return False
    if requirements["automatic"] and group.transmission != "AUTOMATIC":
        return False
    if requirements.get("manual") and group.transmission != "MANUAL":
        return False
    categories = requirements.get("categories", [])
    codes = {c.code for c in group.comparison_classes.all()} if hasattr(group, 'comparison_classes') else set()
    if categories:
        matches = []
        for category in categories:
            if "8/9" in category:
                matches.append(group.seats in (8, 9) or 'PASSENGER_VAN_AUTO' in codes)
            elif "7" in category:
                matches.append(group.seats == 7 or 'SUV_7_AUTO' in codes)
            elif "סטיישן" in category:
                matches.append(group.body_type == "ESTATE")
            elif "סדאן" in category:
                name = getattr(group, "group_name", "").upper()
                premium = (
                    "PREMIUM" in name
                    or "PREMIUM" in getattr(group, "category", "").upper()
                    or any("PREMIUM" in code for code in codes)
                )
                standard_class = (
                    any(code.startswith(("C_", "D_")) for code in codes)
                    or re.match(r"^[CD](?:\b|[_ -])", name)
                )
                matches.append(
                    group.body_type == "SEDAN"
                    and not ("סטנדרטי" in category and (premium or not standard_class))
                )
            elif "SUV" in category.upper():
                is_suv = group.body_type == "SUV" or any('SUV' in code for code in codes)
                name = getattr(group, 'group_name', '').upper()
                premium = (
                    'PREMIUM' in name or 'LUX' in name
                    or 'PREMIUM' in getattr(group, 'category', '').upper()
                    or any('PREMIUM' in code for code in codes)
                )
                requested_premium = any(word in category for word in ('פרימיום', 'פרמיום')) or 'PREMIUM' in category.upper()
                size = None
                if 'SUV_SMALL_AUTO' in codes or 'SMALL' in name:
                    size = 'SMALL'
                elif 'SUV_MEDIUM_AUTO' in codes or 'MEDIUM' in name:
                    size = 'MEDIUM'
                elif 'SUV_BIG_AUTO' in codes or any(word in name for word in ('BIG', 'LARGE')):
                    size = 'BIG'
                requested_size = (
                    'SMALL' if 'קטן' in category else
                    'MEDIUM' if 'בינוני' in category else
                    'BIG' if 'גדול' in category else None
                )
                matches.append(
                    is_suv and premium == requested_premium
                    and (requested_size is None or size == requested_size)
                )
        if matches and not any(matches):
            return False
    return True


@login_required
@require_POST
def import_inquiry(request):
    raw = request.POST.get("text", "").strip()
    if not raw or len(raw) > 30000:
        return JsonResponse({"error": "Вставьте заявку (до 30 000 символов)."}, status=400)
    data, requirements, warnings = parse_inquiry(raw)
    if "מספר נוסעים כולל הנהג" not in raw or "קבלת הרכב" not in raw:
        return JsonResponse({"error": "Не распознан формат заявки сайта. Существующие поля сохранены."}, status=400)
    form = FirstInquiryForm()
    groups = [g for g in form.fields["vehicle_groups"].queryset if suitable_group(g, requirements)]
    data["vehicle_groups"] = [g.pk for g in groups]
    data["suppliers"] = list(form.fields["suppliers"].queryset.values_list('pk', flat=True))
    if any(g.seats is None for g in groups):
        warnings.append("У некоторых подходящих категорий не заполнено количество мест. Они показаны как кандидаты: проверьте вместимость перед отправкой.")
    if not groups:
        warnings.append("Подходящие категории не найдены. Проверьте число мест и коробку передач в справочнике.")
    return JsonResponse({"fields": data, "warnings": warnings, "requirements": requirements})
