from io import StringIO
from decimal import Decimal

from django.core.management import call_command, CommandError
from django.test import TestCase

from .models import Supplier, SupplierExtra, SupplierExtraRate


class YoungDriverConfigurationTests(TestCase):
    def setUp(self):
        self.first = Supplier.objects.create(supplier_code='TEST-YOUNG-A',supplier_name='TEST YOUNG A')
        self.second = Supplier.objects.create(supplier_code='TEST-YOUNG-B',supplier_name='TEST YOUNG B')
        self.extra = SupplierExtra.objects.create(supplier=self.second,extra_code='YOUNG_DRIVER',name='TEST EXISTING FEE')
        self.old = SupplierExtraRate.objects.create(extra=self.extra,rate_code='OLD',calculation_type='PER_DRIVER_DAY',
            amount_gross=10,valid_from='2026-01-01')

    def command(self, **options):
        call_command('configure_young_driver_rate','--supplier',self.first.supplier_name,
            '--supplier',self.second.supplier_name,'--amount','100','--valid-from','2026-11-15',
            stdout=StringIO(),**options)

    def test_preview_does_not_change_any_tariffs(self):
        self.command()
        self.assertFalse(self.first.extras.exists())
        self.assertEqual(SupplierExtraRate.objects.count(),1)

    def test_apply_is_repeatable_keeps_old_rate_and_reads_requested_amount(self):
        for _ in range(2):
            self.command(apply=True,name_he='TEST-NAME-HE')
        self.old.refresh_from_db()
        self.assertEqual(self.old.amount_gross,10)
        for supplier in [self.first,self.second]:
            extra = supplier.extras.get(extra_code='YOUNG_DRIVER')
            rate = extra.rates.get(rate_code='OWNER_20261115')
            self.assertEqual(rate.amount_gross,Decimal('100'))
            self.assertEqual(rate.calculation_type,'PER_DRIVER_DAY')
            self.assertEqual(extra.customer_name_he,'TEST-NAME-HE')
            self.assertEqual(extra.name,'Young/new driver fee')
            self.assertIsNone(rate.maximum_amount_gross)
        self.assertEqual(SupplierExtraRate.objects.count(),3)

    def test_invalid_supplier_rolls_back_whole_configuration(self):
        with self.assertRaisesMessage(CommandError,'Supplier must identify exactly one existing record'):
            call_command('configure_young_driver_rate','--supplier',self.first.supplier_name,
                '--supplier','DOES NOT EXIST','--amount','100','--valid-from','2026-11-15',apply=True,stdout=StringIO())
        self.assertFalse(self.first.extras.exists())

    def test_configuration_does_not_change_existing_order_or_send_messages(self):
        from bookings.models import Booking, BookingDriver
        from customers.models import Customer
        from django.core import mail
        customer = Customer.objects.create(first_name='TEST CUSTOMER')
        booking = Booking.objects.create(customer=customer,supplier=self.first)
        Booking.objects.filter(pk=booking.pk).update(manual_adjustment_amount=100,total_price_gross=100)
        BookingDriver.objects.bulk_create([
            BookingDriver(booking=booking,first_name='TEST FIRST',last_name='DRIVER',young_driver_status=True,role='MAIN'),
            BookingDriver(booking=booking,first_name='TEST SECOND',last_name='DRIVER',young_driver_status=True,role='ADDITIONAL')])
        before = list(Booking.all_objects.values('id','total_price_gross','manual_adjustment_amount','source_quote_snapshot'))
        self.command(apply=True)
        self.assertEqual(before,list(Booking.all_objects.values('id','total_price_gross','manual_adjustment_amount','source_quote_snapshot')))
        self.assertFalse(booking.extras.exists())
        self.assertFalse(mail.outbox)
