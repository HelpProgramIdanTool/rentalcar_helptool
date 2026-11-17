from django.test import TestCase
from django.core import mail
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils import translation
from copy import deepcopy
import importlib

from . import test_manual as manual_data
from .amendments import order_body
from .models import Booking
from .supplier_format import render_supplier_booking, new_booking_html


class SupplierNewFormatTests(TestCase):
    setUp = manual_data.ManualBookingTests.setUp
    review = manual_data.ManualBookingTests.review
    confirm = manual_data.ManualBookingTests.confirm

    def create(self, **changes):
        data,response = self.review(**changes)
        self.confirm(data,response)
        return Booking.objects.get()

    def enable(self, booking):
        profile = importlib.import_module('suppliers.migrations.0059_one_rent_new_booking_format')
        booking.supplier.new_booking_email_template = profile.TEMPLATE
        booking.supplier.new_booking_email_options = deepcopy(profile.OPTIONS)
        booking.supplier.save()
        return booking

    def test_configuration_migration_only_initializes_one_rent_once(self):
        from django.apps import apps
        from django.db import connection
        from types import SimpleNamespace
        profile = importlib.import_module('suppliers.migrations.0059_one_rent_new_booking_format')
        supplier = self.create().supplier
        profile.enable(apps, SimpleNamespace(connection=connection))
        supplier.refresh_from_db()
        self.assertEqual(supplier.new_booking_email_template, '')
        supplier.supplier_name = 'One Rent'
        supplier.save()
        profile.enable(apps, SimpleNamespace(connection=connection))
        supplier.refresh_from_db()
        self.assertEqual(supplier.new_booking_email_template, profile.TEMPLATE)
        supplier.new_booking_email_template = 'CUSTOM $driver_names'
        supplier.save()
        profile.enable(apps, SimpleNamespace(connection=connection))
        supplier.refresh_from_db()
        self.assertEqual(supplier.new_booking_email_template, 'CUSTOM $driver_names')

    def test_legacy_body_is_preserved_exactly(self):
        data,response = self.review()
        self.confirm(data,response)
        booking = Booking.objects.get()
        expected = ('Test Driver\n\nnew@example.com\n01/10/26, 10:00, Kraków city branch\n'
            '04/10/26, 10:00, Kraków city branch\n3 days\nTest car (TEST)\n'
            'Additional driver for free + full insurance with zero excess + unlimited mileage\n'
            '3x100=300 PLN // Deposit: 300.00 PLN')
        self.assertEqual(order_body(booking),expected)
        page = self.client.get(reverse('quotes:supplier_message',args=[booking.pk]))
        self.assertEqual(page.context['body'],expected)

    def test_only_new_letters_use_profile_and_fields_have_english_dates(self):
        booking = self.enable(self.create(driver_count=2,driver_1_name='TEST FIRST',driver_2_name='TEST SECOND',
            phone_1='TEST-PHONE',email='test@example.invalid',address='TEST STREET',country='TEST COUNTRY'))
        Booking.objects.filter(pk=booking.pk).update(customer_city_snapshot='TEST CITY',customer_postal_code_snapshot='TEST POSTAL')
        booking.refresh_from_db()
        before = booking.total_price_gross
        for language in ['ru','pl','en']:
            with translation.override(language):
                body = render_supplier_booking(booking)
            self.assertTrue(body.startswith('Customer: TEST FIRST / TEST SECOND\n'))
            self.assertIn('Address: TEST STREET, TEST CITY, TEST COUNTRY, TEST POSTAL',body)
            self.assertIn('Phone: TEST-PHONE',body)
            self.assertIn('Email: test@example.invalid',body)
            self.assertIn('Pick-up Date: 1 October 2026, 10:00',body)
            self.assertIn('Return Date: 4 October 2026, 10:00',body)
            self.assertIn('Vehicle Class: TEST CAR (TEST)',body)
            self.assertIn('Days: 3',body)
            self.assertTrue(body.endswith('Deposit: 300.00 PLN\nPrice calculation: 3x100=300 PLN'))
            self.assertNotIn('- Extra Cleaning',body)
            self.assertNotIn('- GPS Navigation',body)
            self.assertNotIn('- Airport Vehicle Delivery',body)
        update = order_body(booking)
        self.assertFalse(update.startswith('Customer:'))
        self.assertIn('TEST FIRST // TEST SECOND',update)
        booking.refresh_from_db()
        self.assertEqual(booking.total_price_gross,before)

    def test_selected_services_young_drivers_and_manual_description_are_not_lost(self):
        from suppliers.models import SupplierExtra, SupplierExtraRate
        fee = SupplierExtra.objects.create(supplier=self.supplier,extra_code='YOUNG_DRIVER',name='TEST Young fee')
        SupplierExtraRate.objects.create(extra=fee,calculation_type='PER_DRIVER_DAY',amount_gross=10,valid_from='2026-01-01')
        booking = self.enable(self.create(driver_1_young='on',manual_adjustment_label='TEST EXTRA',manual_adjustment_amount='100'))
        body = render_supplier_booking(booking)
        self.assertIn('- Young/new drivers (1): Test Driver',body)
        self.assertIn('- Manual surcharge: TEST EXTRA: 100.00 PLN',body)
        self.assertIn('Price calculation: 3x100+30+100=430 PLN',body)
        from .message_content import booking_price_error
        self.assertEqual(booking_price_error(booking,body=body),'')

    def test_saved_operator_draft_is_not_replaced_by_new_format(self):
        booking = self.create()
        url = reverse('quotes:supplier_message',args=[booking.pk])
        body = 'TEST SAVED OPERATOR DRAFT'
        self.client.post(url,dict(action='save',recipient='test@example.invalid',subject='TEST',body=body))
        self.enable(booking)
        response = self.client.get(url)
        self.assertEqual(response.context['body'],body)
        self.assertFalse(mail.outbox)
        self.client.post(url,dict(action='load_supplier_format'))
        self.assertEqual(self.client.get(url).context['body'],body)
        self.client.post(url,dict(action='load_supplier_format',confirm_format_reset='yes'))
        self.assertTrue(self.client.get(url).context['body'].startswith('Customer: Test Driver'))
        self.assertTrue(booking.history_events.filter(changes__message__body=body).exists())
        self.assertFalse(mail.outbox)

    def test_actual_send_has_matching_plain_and_safe_html_parts(self):
        booking = self.enable(self.create(driver_1_name='TEST <script>DRIVER</script>'))
        url = reverse('quotes:supplier_message',args=[booking.pk])
        page = self.client.get(url)
        body = page.context['body']+'\nTEST OPERATOR NOTE'
        response = self.client.post(url,dict(action='send',recipient='test@example.invalid',subject='TEST',
            body=body,send_token=page.context['send_token']))
        self.assertEqual(response.status_code,302)
        email = mail.outbox[0]
        self.assertEqual(email.body,body)
        html = email.alternatives[0].content
        self.assertIn('<strong>Customer:</strong>',html)
        self.assertIn('TEST OPERATOR NOTE',html)
        self.assertIn('&lt;script&gt;DRIVER&lt;/script&gt;',html)
        self.assertNotIn('<script>',html)
        self.assertEqual(booking.supplier_deliveries.get().body,body)

    def test_invalid_editable_template_is_reported_without_sending_or_crashing(self):
        booking = self.enable(self.create())
        booking.supplier.new_booking_email_template = 'Customer: $UNKNOWN'
        with self.assertRaises(ValidationError):
            booking.supplier.full_clean()
        booking.supplier.save()
        response = self.client.get(reverse('quotes:supplier_message',args=[booking.pk]))
        self.assertEqual(response.status_code,200)
        self.assertTrue(response.context['format_error'])
        self.assertFalse(mail.outbox)

    def test_only_selected_service_names_and_one_airport_delivery_line_are_listed(self):
        from suppliers.models import SupplierExtra, SupplierExtraRate
        for code in ['AIRPORT_FEE','CITY_AIRPORT_DELIVERY','GPS','CHILD_SEAT','SNOW_CHAINS','CROSS_BORDER']:
            extra = SupplierExtra.objects.create(supplier=self.supplier,extra_code=code,name='TEST '+code,
                is_mandatory=code=='CITY_AIRPORT_DELIVERY')
            SupplierExtraRate.objects.create(extra=extra,calculation_type='PER_RENTAL',amount_gross=10,valid_from='2026-01-01')
        booking = self.enable(self.create(pickup_city='Warszawa',return_city='Warszawa',
            pickup_service='AIRPORT',return_service='AIRPORT',flight_number='TEST123',
            extra_choices=['NAVIGATION','CHILD_SEAT','SNOW_CHAINS'],child_seat_quantity=1,
            child_seat_1_type_number='2',child_seat_1_age='4',child_seat_1_height='100',cross_border_requested=True))
        body = render_supplier_booking(booking)
        self.assertIn('Pick-up Location: Warsaw Airport',body)
        self.assertIn('Return Location: Warsaw Airport',body)
        self.assertIn('Flight Number: TEST123',body)
        self.assertEqual(body.count('- Airport Vehicle Delivery'),1)
        self.assertIn('- GPS Navigation',body)
        self.assertIn('- Snow Chains',body)
        self.assertIn('- Child Seat – Group 2, age 4, height 100 cm',body)
        self.assertEqual(body.count('- Access to Travel Abroad'),1)
        self.assertNotIn('- Extra Cleaning',body)
        self.assertNotIn('- Delivery / Return Outside the City',body)

    def test_update_stays_plain_even_when_new_booking_profile_is_enabled(self):
        booking = self.enable(self.create())
        Booking.objects.filter(pk=booking.pk).update(status='CONFIRMED',supplier_booking_number='TEST-RES')
        url = reverse('quotes:supplier_message',args=[booking.pk])
        response = self.client.get(url,{'change':'1'})
        self.assertTrue(response.context['body'].startswith('Please update existing reservation TEST-RES.'))
        self.assertNotIn('Pick-up Date:',response.context['body'])
        self.assertIsNone(new_booking_html(booking,'UPDATE',response.context['body']))
