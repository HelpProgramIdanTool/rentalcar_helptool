from django import forms
from django.utils import timezone
from suppliers.models import Supplier, VehicleComparisonClass, VehicleGroup

class FirstInquiryForm(forms.Form):
    LANGUAGE_CHOICES = [
        ("Hebrew", "עברית — иврит"),
        ("Russian", "Русский"),
        ("English", "English"),
        ("Polish", "Polski"),
    ]
    CITY_CHOICES = [
        (city, city) for city in (
            "Warszawa", "Kraków", "Katowice", "Gdańsk", "Lublin", "Łódź",
            "Modlin", "Olsztyn", "Poznań", "Rzeszów", "Szczecin", "Wrocław",
            "Radom", "Bydgoszcz", "Prague", "Pardubice",
        )
    ]
    SERVICE_CHOICES = [
        ("AIRPORT", "Аэропорт"),
        ("ADDRESS", "Доставка по адресу клиента"),
        ("CITY_BRANCH", "Отдел в городе"),
    ]
    EXTRA_CHOICES = [
        ("CHILD_SEAT", "Детское кресло / бустер"),
        ("SNOW_CHAINS", "Цепи для снега"),
        ("NAVIGATION", "GPS / навигация"),
        ("WIFI_ROUTER", "Wi-Fi роутер"),
    ]
    TIME_CHOICES = [
        (f"{hour:02d}:{minute:02d}", f"{hour:02d}:{minute:02d}")
        for hour in range(24) for minute in range(0, 60, 5)
    ]
    first_name = forms.CharField(label="Имя", max_length=100)
    last_name = forms.CharField(label="Фамилия", max_length=100)
    email = forms.EmailField(label="E-mail", required=False)
    phone_1 = forms.CharField(label="Телефон 1", max_length=30, required=False)
    phone_2 = forms.CharField(label="Телефон 2", max_length=30, required=False)
    phone_3 = forms.CharField(label="Телефон 3", max_length=30, required=False)
    country = forms.CharField(label="Страна", max_length=100, required=False)
    preferred_language = forms.ChoiceField(
        label="Язык клиента", choices=LANGUAGE_CHOICES, initial="Hebrew"
    )
    address = forms.CharField(label="Адрес проживания", max_length=255, required=False)
    wants_invoice = forms.BooleanField(label="Клиент хочет инвойс", required=False)
    invoice_name = forms.CharField(label="Название / имя для инвойса", max_length=200, required=False)
    invoice_tax_id = forms.CharField(label="NIP / налоговый номер", max_length=50, required=False)
    invoice_address = forms.CharField(label="Адрес для инвойса", max_length=255, required=False)
    invoice_email = forms.EmailField(label="E-mail для инвойса", required=False)

    pickup_date = forms.DateField(
        label="Дата получения",
        input_formats=["%d-%m-%Y"],
        widget=forms.TextInput(attrs={"placeholder": "ДД-ММ-ГГГГ", "autocomplete": "off"}),
    )
    pickup_time = forms.ChoiceField(label="Время получения", choices=TIME_CHOICES, initial="10:00")
    return_date = forms.DateField(
        label="Дата возврата",
        input_formats=["%d-%m-%Y"],
        widget=forms.TextInput(attrs={"placeholder": "ДД-ММ-ГГГГ", "autocomplete": "off"}),
    )
    return_time = forms.ChoiceField(label="Время возврата", choices=TIME_CHOICES, initial="10:00")
    pickup_city = forms.ChoiceField(label="Город получения", choices=CITY_CHOICES)
    pickup_service = forms.ChoiceField(label="Способ получения", choices=SERVICE_CHOICES)
    pickup_address = forms.CharField(label="Адрес получения", max_length=300, required=False)
    return_city = forms.ChoiceField(label="Город возврата", choices=CITY_CHOICES)
    return_service = forms.ChoiceField(label="Способ возврата", choices=SERVICE_CHOICES)
    return_address = forms.CharField(label="Адрес возврата", max_length=300, required=False)
    vehicle_classes = forms.ModelMultipleChoiceField(
        label="Классы автомобилей",
        queryset=VehicleComparisonClass.objects.none(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )
    vehicle_groups = forms.ModelMultipleChoiceField(
        label="Категории автомобилей поставщиков",
        queryset=VehicleGroup.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    suppliers = forms.ModelMultipleChoiceField(
        label="Рассчитать предложения фирм",
        queryset=Supplier.objects.none(),
        widget=forms.CheckboxSelectMultiple,
    )
    driver_count = forms.IntegerField(label="Количество водителей", min_value=1, initial=1)
    cross_border_requested = forms.BooleanField(label="Выезд за границу", required=False)
    extra_choices = forms.MultipleChoiceField(
        label="Дополнительные услуги",
        choices=EXTRA_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    child_seat_quantity = forms.IntegerField(
        label="Количество детских кресел",
        min_value=1,
        max_value=9,
        initial=1,
        required=False,
    )
    customer_notes = forms.CharField(
        label="Что написал клиент", required=False, widget=forms.Textarea(attrs={"rows": 4})
    )
    internal_notes = forms.CharField(
        label="Моя заметка", required=False, widget=forms.Textarea(attrs={"rows": 3})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vehicle_classes"].queryset = VehicleComparisonClass.objects.filter(
            is_active=True
        ).order_by("display_order", "name")
        self.fields["vehicle_groups"].queryset = VehicleGroup.objects.filter(
            is_active=True, supplier__status=Supplier.Status.ACTIVE
        ).select_related("supplier").order_by(
            "supplier__supplier_name", "display_order", "group_name"
        )
        supplier_queryset = Supplier.objects.filter(status=Supplier.Status.ACTIVE).order_by(
            "supplier_name"
        )
        self.fields["suppliers"].queryset = supplier_queryset
        if not self.is_bound:
            self.fields["suppliers"].initial = list(
                supplier_queryset.values_list("id", flat=True)
            )
        for field_name in ("email", "phone_1", "phone_2", "phone_3"):
            self.fields[field_name].widget.attrs["autocomplete"] = (
                "email" if field_name == "email" else "tel"
            )

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("email") and not cleaned.get("phone_1"):
            raise forms.ValidationError("Укажите хотя бы e-mail или первый телефон.")
        pickup_date = cleaned.get("pickup_date")
        pickup_time = cleaned.get("pickup_time")
        return_date = cleaned.get("return_date")
        return_time = cleaned.get("return_time")
        if pickup_date and pickup_time:
            pickup_time = __import__("datetime").time.fromisoformat(pickup_time)
            cleaned["pickup_datetime"] = timezone.make_aware(
                __import__("datetime").datetime.combine(pickup_date, pickup_time)
            )
        if return_date and return_time:
            return_time = __import__("datetime").time.fromisoformat(return_time)
            cleaned["return_datetime"] = timezone.make_aware(
                __import__("datetime").datetime.combine(return_date, return_time)
            )
        if cleaned.get("pickup_datetime") and cleaned.get("return_datetime"):
            if cleaned["return_datetime"] <= cleaned["pickup_datetime"]:
                self.add_error("return_date", "Возврат должен быть позже получения.")
        if cleaned.get("wants_invoice"):
            if not cleaned.get("invoice_name"):
                self.add_error("invoice_name", "Укажите имя или название для инвойса.")
            if not cleaned.get("invoice_address"):
                self.add_error("invoice_address", "Укажите адрес для инвойса.")
        if "CHILD_SEAT" in cleaned.get("extra_choices", []):
            if not cleaned.get("child_seat_quantity"):
                self.add_error("child_seat_quantity", "Укажите количество детских кресел.")
        return cleaned
