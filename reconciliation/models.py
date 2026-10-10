from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Reconciliation(models.Model):
    month = models.DateField('Месяц (первое число)')
    supplier = models.ForeignKey('suppliers.Supplier', on_delete=models.PROTECT, verbose_name='Фирма')
    employee = models.ForeignKey('employees.Employee', null=True, blank=True, on_delete=models.PROTECT, verbose_name='Работник')
    rate = models.DecimalField('Комиссия работника (%)', max_digits=5, decimal_places=2, default=Decimal('4'), validators=[MinValueValidator(0), MaxValueValidator(100)])
    vat = models.DecimalField('НДС для перевода брутто в нетто (%)', max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    state = models.CharField('Сверка', max_length=12, choices=[('DRAFT', 'В работе'), ('CLOSED', 'Сверено')], default='DRAFT')
    invoice_number = models.CharField('Номер фактуры', max_length=120, blank=True)
    invoice_date = models.DateField('Дата фактуры', null=True, blank=True)
    invoice_amount = models.DecimalField('Сумма фактуры, PLN (не оборот аренды)', max_digits=14, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0)])
    received = models.DecimalField('Получено от поставщика, PLN', max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    received_date = models.DateField('Дата получения последнего платежа', null=True, blank=True)
    employee_paid = models.DecimalField('Выплачено работнику, PLN', max_digits=14, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    employee_paid_date = models.DateField('Дата выплаты работнику', null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)
    direct_orderer = models.CharField('Заказывающий для прямых заказов', max_length=200, blank=True)
    direct_prefixes = models.CharField('Префиксы прямых заказов через запятую', max_length=100, blank=True)
    direct_rate = models.DecimalField('Моя комиссия за прямые заказы (%)', max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0), MaxValueValidator(100)])

    class Meta:
        verbose_name = 'Сверка за месяц'
        verbose_name_plural = 'Сверки за месяц'
        constraints = [models.UniqueConstraint(fields=['month', 'supplier'], name='unique_supplier_month_reconciliation')]
        ordering = ['-month', 'supplier']

    def __str__(self):
        return f'{self.month:%Y-%m} — {self.supplier}'

    def clean(self):
        if self.month and self.month.day != 1:
            raise ValidationError('Укажите первое число месяца.')
        if self.received and (not self.invoice_number or self.invoice_amount is None or not self.received_date):
            raise ValidationError('Для оплаты поставщиком нужны номер, сумма фактуры и дата платежа.')
        if self.employee_paid and not self.employee_paid_date:
            raise ValidationError('Укажите дату выплаты работнику.')
        if (self.received or self.employee_paid) and self.state != 'CLOSED':
            raise ValidationError('Сначала завершите сверку.')


class Upload(models.Model):
    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.PROTECT, related_name='uploads')
    kind = models.CharField(max_length=12, choices=[('OWN', 'Мои записи'), ('SUPPLIER', 'Отчёт поставщика'), ('EMPLOYEE', 'Список работника')])
    name = models.CharField(max_length=255)
    digest = models.CharField(max_length=64)
    mapping = models.JSONField(default=dict)
    content = models.BinaryField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=['reconciliation', 'kind', 'digest'], name='unique_reconciliation_file')]


class Row(models.Model):
    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.CASCADE, related_name='rows')
    number = models.CharField(max_length=100)
    booking = models.ForeignKey('bookings.Booking', null=True, blank=True, on_delete=models.PROTECT)
    own = models.JSONField(default=dict, blank=True)
    supplier_lines = models.JSONField(default=list, blank=True)
    employee_data = models.JSONField(default=dict, blank=True)
    issues = models.JSONField(default=list, blank=True)
    decision = models.CharField(max_length=12, default='REVIEW', choices=[('PREVIOUS', 'Учтён ранее'), ('REVIEW', 'Проверить'), ('INCLUDE', 'Включить'), ('DIRECT', 'Прямой заказ поставщика'), ('CANCEL', 'Отмена'), ('CARRY', 'Следующий месяц'), ('EXCLUDE', 'Не входит в этот месяц')])
    note = models.TextField(blank=True)
    previous_row = models.ForeignKey('self', null=True, blank=True, on_delete=models.PROTECT, related_name='later_rows')

    class Meta:
        constraints = [models.UniqueConstraint(fields=['reconciliation', 'number'], name='unique_reconciliation_reservation')]
        ordering = ['number']


class Revision(models.Model):
    reconciliation = models.ForeignKey(Reconciliation, on_delete=models.PROTECT, related_name='revisions')
    created_at = models.DateTimeField(auto_now_add=True)
    actor = models.CharField(max_length=150)
    reason = models.CharField(max_length=255)
    snapshot = models.JSONField()
    excel = models.BinaryField()
    own_excel = models.BinaryField(null=True, blank=True)
    digest = models.CharField(max_length=64)

    class Meta:
        ordering = ['-pk']
