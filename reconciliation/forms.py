from django import forms
import re
from .models import Reconciliation


class UploadForm(forms.Form):
    file = forms.FileField(label='Excel .xlsx')
    kind = forms.ChoiceField(label='Тип файла', choices=[('OWN','Мои записи'),('SUPPLIER','Отчёт поставщика'),('EMPLOYEE','Список работника')])
    sheet = forms.CharField(label='Название листа (пусто — первый)', required=False)
    first_row = forms.IntegerField(label='Первая строка данных', min_value=1, initial=2)
    number = forms.CharField(label='Столбец номера заказа', initial='I')
    alternate_number = forms.CharField(label='Другой номер поставщика (Kaizen — C)', required=False)
    name = forms.CharField(label='Столбец имени', initial='A', required=False)
    amount = forms.CharField(label='Столбец суммы в моих записях / у работника', initial='E', required=False)
    gross = forms.CharField(label='Столбец брутто поставщика', required=False)
    net = forms.CharField(label='Столбец нетто поставщика', required=False)
    pickup = forms.CharField(label='Столбец получения', initial='B', required=False)
    return_column = forms.CharField(label='Столбец возврата', initial='C', required=False)
    email = forms.CharField(label='Столбец email', initial='H', required=False)
    phone = forms.CharField(label='Столбец телефона', initial='G', required=False)
    invoice = forms.CharField(label='Столбец номера счёта поставщика', required=False)
    orderer = forms.CharField(label='Столбец заказывающего (Kaizen — A)', required=False)
    color_rules = forms.BooleanField(label='В моих записях: красное или пустая сумма — отмена; другой цвет — прежняя отметка оплаты', required=False)
    confirm = forms.BooleanField(label='Столбцы проверены. Загрузить для проверки (существующие заказы пока не менять).')

    def mapping(self):
        result = {k:self.cleaned_data[k].strip().upper() for k in ('number','alternate_number','name','amount','gross','net','pickup','email','phone','invoice','orderer')}
        result['return'] = self.cleaned_data['return_column'].strip().upper()
        return result

    def clean(self):
        data = super().clean()
        for key in ('number','alternate_number','name','amount','gross','net','pickup','return_column','email','phone','invoice'):
            if data.get(key) and not re.fullmatch(r'[A-Za-z]{1,2}', data[key].strip()):
                self.add_error(key, 'Укажите букву столбца Excel, например A или AA.')
        if data.get('kind') == 'SUPPLIER' and not (data.get('net') or data.get('gross')):
            raise forms.ValidationError('Для поставщика укажите столбец нетто или брутто.')
        if data.get('kind') == 'OWN' and not data.get('amount'):
            self.add_error('amount', 'Укажите столбец суммы в своих записях.')
        return data


class PaymentForm(forms.ModelForm):
    class Meta:
        model = Reconciliation
        fields = ['invoice_number','invoice_date','invoice_amount','received','received_date','employee_paid','employee_paid_date']
        widgets = {key: forms.DateInput(attrs={'type':'date'}) for key in ('invoice_date','received_date','employee_paid_date')}


class CalculationForm(forms.ModelForm):
    class Meta:
        model = Reconciliation
        fields = ['employee','rate','vat','direct_orderer','direct_prefixes','direct_rate']
