from django import forms
from django.forms import modelformset_factory, BaseModelFormSet
from .models import Quote, QuoteDocumentBlock, QuoteOption
from .email_content import REQUIRED_BLOCKS

BLOCK_LABELS = {
    "GREETING": "Приветствие и представление", "IMPORTANT": "Возраст, стаж и важные условия",
    "CROSS_BORDER": "Выезд за пределы Польши", "PAYMENT_DEPOSIT": "Депозит",
    "PAYMENT": "Оплата", "BOOKING_PROCESS": "Подтверждение бронирования",
    "CANCELLATION": "Отмена", "CHANGES": "Изменения бронирования",
    "CHANGES_CANCELLATION": "Изменения и отмена — прежний текст",
    "DURING_RENTAL": "Поддержка во время аренды", "TOLLS": "Платные дороги",
    "ORDER_DETAILS": "Данные для бронирования", "DRIVING_DOCUMENTS": "Водительские документы",
    "USEFUL_LINKS": "Полезные ссылки", "SIGNATURE": "Контакты и подпись",
}


class EmailSubjectForm(forms.ModelForm):
    class Meta:
        model = Quote
        fields = ["email_subject"]
        labels = {"email_subject": "Тема письма"}

    def clean_email_subject(self):
        value = self.cleaned_data["email_subject"]
        if "\n" in value or "\r" in value:
            raise forms.ValidationError("Тема должна занимать одну строку.")
        return value


class BlockForm(forms.ModelForm):
    class Meta:
        model = QuoteDocumentBlock
        fields = ["title", "content", "is_enabled", "display_order"]
        labels = {"title": "Заголовок", "content": "Текст", "is_enabled": "Включить в письмо", "display_order": "Порядок"}
        widgets = {"title": forms.TextInput(attrs={"dir": "rtl"}), "content": forms.Textarea(attrs={"dir": "rtl", "rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.editor_label = BLOCK_LABELS.get(self.instance.block_key, self.instance.title or "Текст письма")
        if self.instance.block_key in REQUIRED_BLOCKS:
            self.initial["is_enabled"] = True
            self.fields["is_enabled"].disabled = True
        self.fields["content"].required = False

    def clean(self):
        data = super().clean()
        if (data.get("is_enabled") or self.instance.block_key in REQUIRED_BLOCKS) and not data.get("content"):
            self.add_error("content", "Добавьте текст или отключите этот блок.")
        return data


class ScopedFormSet(BaseModelFormSet):
    def clean(self):
        super().clean()
        if any(self.errors):
            return
        expected = set(self.get_queryset().values_list("pk", flat=True))
        received = [form.cleaned_data.get("id").pk for form in self.forms if form.cleaned_data.get("id")]
        if set(received) != expected or len(received) != len(expected):
            raise forms.ValidationError("Список изменился. Обновите страницу и повторите сохранение.")


BlockFormSet = modelformset_factory(QuoteDocumentBlock, form=BlockForm, formset=ScopedFormSet, extra=0)
OptionFormSet = modelformset_factory(QuoteOption, formset=ScopedFormSet, fields=["customer_comment"], extra=0,
    widgets={"customer_comment": forms.Textarea(attrs={"dir": "rtl", "rows": 3})},
    labels={"customer_comment": "Комментарий клиенту"})
