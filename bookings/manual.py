from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

from django import forms
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from customers.models import Customer
from employees.models import Employee, SubAgent
from suppliers.models import Supplier
from quotes.models import Quote
from .models import Booking
from .quote_conversion import BookingFromOfferForm, calculate, create_draft, fingerprint, review_snapshot
from .missing_data import MissingDepositForm, new_deposit_form, apply_deposit


class ManualBookingForm(BookingFromOfferForm):
    entry_token = forms.CharField(widget=forms.HiddenInput)
    existing_customer = forms.ModelChoiceField(label="Карточка существующего клиента (или новый клиент)", queryset=Customer.objects.all(), required=False)
    supplier = forms.ModelChoiceField(label="Фирма, где заказываем", queryset=Supplier.objects.filter(status="ACTIVE"))
    order_source = forms.ChoiceField(label="Чей заказ", choices=Booking._meta.get_field("order_source").choices)
    responsible = forms.ModelChoiceField(label="Ответственный сотрудник", queryset=Employee.objects.filter(status="ACTIVE"), required=False)
    sub_agent = forms.ModelChoiceField(label="Субагент", queryset=SubAgent.objects.filter(is_active=True), required=False)
    customer_name = forms.CharField(label="Имя и фамилия", max_length=201)
    hotel_name = forms.CharField(label="Отель при получении", max_length=200, required=False)
    return_hotel_name = forms.CharField(label="Отель при возврате", max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("first_name", None)
        self.fields.pop("last_name", None)
        self.order_fields(["entry_token", "existing_customer", "customer_name", "email", "phone_1", "phone_2", "phone_3"])

    def clean(self):
        data = super().clean()
        parts = data.get("customer_name", "").strip().split(maxsplit=1)
        data["first_name"] = parts[0] if parts else ""
        data["last_name"] = parts[1] if len(parts) > 1 else ""
        group, supplier = data.get("vehicle_group"), data.get("supplier")
        if group and supplier and group.supplier_id != supplier.pk:
            self.add_error("vehicle_group", "Выберите группу указанной фирмы.")
        if data.get("order_source") == "EMPLOYEE" and not data.get("responsible"):
            self.add_error("responsible", "Укажите сотрудника, чей это заказ.")
        if data.get("order_source") == "SUBAGENT" and not data.get("sub_agent"):
            self.add_error("sub_agent", "Выберите субагента.")
        if data.get("order_source") != "SUBAGENT" and data.get("sub_agent"):
            self.add_error("sub_agent", "Субагент указывается для заказа субагента.")
        for index in range(1, (data.get("driver_count") or 0) + 1):
            if not data.get(f"driver_{index}_name", "").strip():
                self.add_error(f"driver_{index}_name", "Укажите имя и фамилию водителя.")
        return data


@login_required
@require_http_methods(["GET", "POST"])
@transaction.atomic
def new_booking(request):
    initial = {"entry_token": signing.dumps({"key": str(uuid4()), "user": request.user.pk}, salt="manual-entry"),
               "order_source": "SELF", "driver_count": 1}
    customer_id = request.GET.get("customer", "")
    selected = Customer.objects.filter(pk=customer_id).first() if customer_id.isdigit() else None
    if selected:
        for name in ("email", "phone_1", "phone_2", "phone_3", "country", "address", "preferred_language",
                     "wants_invoice", "invoice_name", "invoice_tax_id", "invoice_address", "invoice_email"):
            initial[name] = getattr(selected, name)
        initial["customer_name"] = " ".join(filter(None, [selected.first_name, selected.last_name]))
        initial["existing_customer"] = selected.pk
        initial["driver_1_name"] = selected.full_name_latin
    form = ManualBookingForm(request.POST or None, initial=initial)
    result = token = deposit_form = None
    deposit_pending = deposit_once = False
    if request.method == "POST":
        try:
            entry = signing.loads(request.POST.get("entry_token", ""), salt="manual-entry", max_age=86400)
            if entry["user"] != request.user.pk:
                raise signing.BadSignature()
            existing = Booking.objects.filter(manual_entry_key=entry["key"], created_by_user=request.user).first()
            if existing:
                return redirect("quotes:booking_detail", pk=existing.pk)
        except (signing.BadSignature, KeyError):
            form.is_valid()
            form.add_error(None, "Форма устарела. Откройте «Новый заказ» заново.")
            entry = None
        if entry and form.is_valid():
            data = form.cleaned_data
            option = SimpleNamespace(pk=None, quote=Quote(quote_number="Ручной заказ"), total_price_gross=Decimal("0"), currency="PLN")
            option.quote.sub_agent = data.get("sub_agent")
            option.quote.sub_agent_id = data["sub_agent"].pk if data.get("sub_agent") else None
            try:
                result = calculate(option, data)
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
                if deposit_pending:
                    raise forms.ValidationError("Укажите депозит в открывшемся окне.")
                snapshot = review_snapshot(option, data, result)
                snapshot.update(origin="manual", sub_agent_name=str(data["sub_agent"]) if data["sub_agent"] else "",
                    sub_agent_phone=data["sub_agent"].phone if data["sub_agent"] else "")
                if deposit_once:
                    snapshot["deposit_usage"] = "once"
                stamp = {"fingerprint": fingerprint(snapshot), "user": request.user.pk, "key": entry["key"]}
                if request.POST.get("action") == "create":
                    try:
                        previous = signing.loads(request.POST.get("review_token", ""), salt="manual-review", max_age=3600)
                    except signing.BadSignature:
                        previous = None
                    if previous == stamp and request.POST.get("confirm_price") == "yes":
                        customer = data["existing_customer"]
                        if customer is None:
                            fields = ("first_name", "last_name", "email", "phone_1", "phone_2", "phone_3", "country", "address", "preferred_language",
                                      "wants_invoice", "invoice_name", "invoice_tax_id", "invoice_address", "invoice_email")
                            customer = Customer.objects.create(**{name: data[name] for name in fields})
                        option.quote.customer = customer
                        booking = create_draft(option, data, result, snapshot, request.user)
                        actor = Employee.objects.filter(login_user=request.user).first()
                        Booking.objects.filter(pk=booking.pk).update(manual_entry_key=entry["key"], order_source=data["order_source"],
                            salesperson_employee=actor if data["order_source"] == "SELF" else data["responsible"],
                            sub_agent=data["sub_agent"], flight_number=data["flight_number"], hotel_name=data["hotel_name"],
                            return_hotel_name=data["return_hotel_name"],
                            supplier_booking_number="")
                        return redirect("quotes:booking_detail", pk=booking.pk)
                    form.add_error(None, "Проверьте расчёт заново и подтвердите сумму: данные или тариф изменились.")
                token = signing.dumps(stamp, salt="manual-review")
            except forms.ValidationError as error:
                form.add_error(None, error)
    return render(request, "bookings/from_offer.html", {
        "manual_entry": True, "form": form, "result": result, "review_token": token,
        "deposit_form": deposit_form, "deposit_pending": deposit_pending, "deposit_once": deposit_once,
        "active_menu": "orders", "customers": Customer.objects.all(), "delta": None,
        "group_suppliers": {str(group.pk): str(group.supplier_id) for group in form.fields["vehicle_group"].queryset},
    })
