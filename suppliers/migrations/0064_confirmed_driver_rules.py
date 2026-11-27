"""Owner-confirmed rules, 27 November 2026. Existing orders stay unchanged."""
from decimal import Decimal
from datetime import date
from django.db import migrations
from django.db.models import Max


def configure(apps, schema_editor):
    Supplier = apps.get_model('suppliers', 'Supplier')
    Extra = apps.get_model('suppliers', 'SupplierExtra')
    Rate = apps.get_model('suppliers', 'SupplierExtraRate')
    configurations = [
        ('Kaizen Rent', 18, 6, 24, 0, '29.99', None),
        ('Car Free', 21, 12, 0, 0, None, None),
        ('One Rent', 18, 0, 24, 12, '30.00', None),
        ('MM Cars', 18, 0, 21, 0, '20.00', '200.00'),
    ]
    for name, age, months, fee_age, fee_months, amount, cap in configurations:
        for supplier in Supplier.objects.filter(supplier_name__iexact=name):
            conditions = dict(supplier.customer_conditions or {})
            conditions['driver_rules'] = {'version': 1, 'surcharge_age_below': fee_age,
                'surcharge_license_months_below': fee_months, 'messages': {
                    'ru': 'Водитель {driver}: минимальный возраст — {age} лет, стаж — {months} месяцев.',
                    'en': 'Driver {driver}: minimum age {age}; minimum licence experience {months} months.',
                    'pl': 'Kierowca {driver}: minimalny wiek {age} lat; prawo jazdy od co najmniej {months} miesięcy.',
                    'he': 'נהג {driver}: גיל מינימלי {age}; ותק רישיון לפחות {months} חודשים.'}}
            supplier.minimum_driver_age, supplier.minimum_license_months = age, months
            supplier.customer_conditions = conditions
            supplier.save(update_fields=['minimum_driver_age', 'minimum_license_months', 'customer_conditions'])
            if amount is None:
                continue
            extra = Extra.objects.filter(supplier=supplier, extra_code__in=['YOUNG_DRIVER', 'YOUNG_DRIVER_21_24']).order_by('extra_code').first()
            if not extra:
                extra = Extra.objects.create(supplier=supplier, extra_code='YOUNG_DRIVER',
                    name='Young/new driver fee', category='DRIVER')
            extra.is_active = True
            extra.name = 'Young/new driver fee'
            extra.customer_name_he = 'תוספת נהג צעיר / חדש'
            extra.save(update_fields=['is_active', 'name', 'customer_name_he'])
            priority = (Rate.objects.filter(extra=extra).aggregate(value=Max('priority'))['value'] or 0) + 1
            Rate.objects.update_or_create(extra=extra, rate_code='OWNER_20261127', defaults={
                'calculation_type': 'PER_DRIVER_DAY', 'amount_gross': Decimal(amount),
                'maximum_amount_gross': Decimal(cap) if cap else None, 'minimum_amount_gross': None,
                'currency': 'PLN', 'priority': priority, 'is_active': True,
                'valid_from': date(2026, 11, 27), 'valid_to': None, 'days_from': None, 'days_to': None,
                'location': None, 'formula_config': {},
                'note': 'Owner confirmed: per eligible driver; age OR experience, charged once.'})


class Migration(migrations.Migration):
    dependencies = [('suppliers', '0063_confirm_czech_supplier_tariffs')]
    operations = [migrations.RunPython(configure, migrations.RunPython.noop)]
