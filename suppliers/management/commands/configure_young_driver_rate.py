"""Store an operator-confirmed tariff without changing existing bookings."""
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Max

from config.driver_fees import YOUNG_DRIVER_CODES
from suppliers.models import Supplier, SupplierExtra, SupplierExtraRate


class Command(BaseCommand):
    help = 'Preview an owner-confirmed per-driver daily tariff. Use --apply to save configuration only.'

    def add_arguments(self, parser):
        parser.add_argument('--supplier', action='append', required=True)
        parser.add_argument('--amount', required=True)
        parser.add_argument('--valid-from', required=True)
        parser.add_argument('--currency', default='PLN')
        parser.add_argument('--name-he', default='')
        parser.add_argument('--apply', action='store_true')

    @transaction.atomic
    def handle(self, *args, **options):
        try:
            amount = Decimal(options['amount'])
            valid_from = date.fromisoformat(options['valid_from'])
            if not amount.is_finite() or amount < 0 or amount >= Decimal('100000000') or amount != amount.quantize(Decimal('.01')):
                raise ValueError
        except (InvalidOperation, ValueError):
            raise CommandError('Enter a non-negative amount with at most two decimals and an ISO valid-from date.')
        currency = options['currency'].upper()
        if len(currency) != 3 or not currency.isalpha():
            raise CommandError('Enter a three-letter currency code.')
        plans = []
        for name in dict.fromkeys(options['supplier']):
            try:
                supplier = Supplier.objects.get(supplier_name__iexact=name)
            except (Supplier.DoesNotExist, Supplier.MultipleObjectsReturned):
                raise CommandError('Supplier must identify exactly one existing record: '+name)
            extras = list(supplier.extras.filter(extra_code__in=YOUNG_DRIVER_CODES))
            if len(extras) > 1:
                raise CommandError('Multiple young-driver services found; review configuration for '+name)
            extra = extras[0] if extras else None
            plans.append((supplier, extra))
        for supplier, extra in plans:
            self.stdout.write(f'{supplier}: {amount:.2f} {currency} per marked driver per rental day, from {valid_from}; no cap.')
            if not options['apply']:
                continue
            if extra is None:
                extra = SupplierExtra.objects.create(supplier=supplier, extra_code=YOUNG_DRIVER_CODES[0],
                    name='Young/new driver fee',category='DRIVER',
                    description='Owner-confirmed service: charged once per marked driver per rental day.')
            changes = {'is_active': True, 'name': 'Young/new driver fee'}
            if options['name_he']:
                changes['customer_name_he'] = options['name_he']
            SupplierExtra.objects.filter(pk=extra.pk).update(**changes)
            code = 'OWNER_'+valid_from.strftime('%Y%m%d')
            existing = SupplierExtraRate.objects.filter(extra=extra,rate_code=code).first()
            other_priority = SupplierExtraRate.objects.filter(extra=extra).exclude(rate_code=code).aggregate(value=Max('priority'))['value'] or 0
            priority = max(existing.priority if existing else 0, other_priority+1)
            if priority > 32767:
                raise CommandError('Tariff priorities must be reviewed for '+str(supplier))
            SupplierExtraRate.objects.update_or_create(extra=extra,rate_code=code,defaults=dict(
                calculation_type=SupplierExtraRate.CalculationType.PER_DRIVER_DAY,amount_gross=amount,currency=currency,
                valid_from=valid_from,valid_to=None,priority=priority,location=None,days_from=None,days_to=None,
                minimum_amount_gross=None,maximum_amount_gross=None,formula_config={},is_active=True,
                note='Owner-confirmed tariff. Existing booking and offer snapshots are unchanged.'))
        self.stdout.write('APPLIED: tariff configuration only; no bookings changed and no emails sent.' if options['apply'] else 'PREVIEW ONLY: no changes. Add --apply after reviewing the configuration.')
