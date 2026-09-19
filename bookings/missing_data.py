"""Validated operator input for a missing deposit; no guessed defaults."""
from django import forms
from django.contrib.admin.models import CHANGE, LogEntry
from django.core import signing
from django.db import transaction

from suppliers.models import VehicleGroup


class MissingDepositForm(forms.Form):
    amount = forms.DecimalField(label="Сумма депозита", min_value=0, max_digits=10, decimal_places=2)
    currency = forms.RegexField(label="Валюта (например, PLN)", regex=r"^[A-Z]{3}$", max_length=3)
    usage = forms.ChoiceField(label="Как использовать", choices=[
        ("once", "Только для этого заказа"),
        ("permanent", "Сохранить в базе для следующих расчётов"),
    ])
    context = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        if not user.has_perm("suppliers.change_vehiclegroup"):
            self.fields["usage"].choices = [("once", "Только для этого заказа")]


def deposit_context(group, option, user):
    return {"group": group.pk, "source": group.effective_rate_group.pk,
            "option": option.pk, "user": user.pk}


def new_deposit_form(group, option, user):
    return MissingDepositForm(user=user, prefix="deposit", initial={
        "currency": group.effective_rate_group.deposit_currency,
        "usage": "once",
        "context": signing.dumps(deposit_context(group, option, user), salt="missing-deposit"),
    })


def apply_deposit(form, result, option, user, *, save_permanently=False):
    """Return True only when the missing value was safely resolved."""
    if not form.is_valid():
        return False
    data = form.cleaned_data
    group = result["group"]
    try:
        context = signing.loads(data["context"], salt="missing-deposit", max_age=3600)
    except signing.BadSignature:
        context = None
    if context != deposit_context(group, option, user):
        form.add_error(None, "Автомобиль изменился или окно устарело. Пересчитайте и введите депозит заново.")
        return False
    if data["usage"] == "permanent":
        if not save_permanently:
            form.add_error(None, "Сначала сохраните депозит кнопкой в окне ввода.")
            return False
        with transaction.atomic():
            source = VehicleGroup.objects.select_for_update().get(pk=context["source"])
            if source.deposit_amount is not None:
                form.add_error(None, "Депозит уже заполнен. Пересчитайте, чтобы увидеть актуальную сумму.")
                return False
            source.deposit_amount = data["amount"]
            source.deposit_currency = data["currency"]
            source.save(update_fields=["deposit_amount", "deposit_currency"])
            LogEntry.objects.log_actions(user_id=user.pk, queryset=VehicleGroup.objects.filter(pk=source.pk),
                action_flag=CHANGE, change_message="Заполнен отсутствующий депозит: "
                f"{data['amount']} {data['currency']} (из оферты {option.quote.quote_number}).")
    result["deposit_amount"] = data["amount"]
    result["deposit_currency"] = data["currency"]
    return True
