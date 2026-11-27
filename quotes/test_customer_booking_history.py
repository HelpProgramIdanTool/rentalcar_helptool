from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from bookings.models import Booking
from customers.models import Customer
from suppliers.models import Supplier, VehicleGroup


class CustomerBookingHistoryTests(TestCase):
    def test_imported_booking_class_is_read_from_original_excel_data(self):
        Booking.objects.create(customer=self.customer,supplier=self.supplier,status='COMPLETED',
            source_quote_snapshot={'historical_import':{'raw':{'D':'TEST-LEGACY-CLASS'}}})
        html=self.client.get(self.url,{'email':self.customer.email}).json()['booking_history_html']
        self.assertIn('TEST-LEGACY-CLASS',html)
        self.assertIn('TEST-FIRM',html)

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user(username='history-test'))
        self.customer = Customer.objects.create(first_name='TEST-FIRST', email='history@example.invalid')
        self.supplier = Supplier.objects.create(supplier_code='HISTORY-TEST', supplier_name='TEST-FIRM')
        self.group = VehicleGroup.objects.create(supplier=self.supplier, group_code='TEST-CODE', group_name='TEST-CLASS')
        self.url = reverse('quotes:customer_lookup')

    def booking(self, **values):
        return Booking.objects.create(customer=self.customer, supplier=self.supplier,
            vehicle_group=self.group, status='CONFIRMED', **values)

    def test_firms_classes_and_numbers_come_from_customer_bookings(self):
        self.booking(supplier_booking_number='TEST-RESERVATION')
        self.booking(supplier_booking_number='TEST-SECOND')
        data = self.client.get(self.url, {'email':self.customer.email}).json()
        html = data['booking_history_html']
        for value in ['TEST-FIRM', 'TEST-CLASS', 'TEST-CODE', 'TEST-RESERVATION', 'TEST-SECOND']:
            self.assertIn(value, html)
        self.assertIn('· 2', html)

    def test_cancelled_draft_no_show_and_other_customer_not_shown(self):
        for status in ['CANCELLED','DRAFT','NO_SHOW']:
            Booking.objects.create(customer=self.customer, supplier=self.supplier,
                vehicle_group=self.group, status=status, supplier_booking_number='HIDDEN')
        other = Customer.objects.create(email='other@example.invalid')
        Booking.objects.create(customer=other, supplier=self.supplier, status='CONFIRMED')
        self.assertEqual(self.client.get(self.url, {'email':self.customer.email}).json()['booking_history_html'].strip(), '')

    def test_selected_customer_without_email_still_has_history(self):
        self.booking(supplier_booking_number='SELECTED-BOOKING')
        self.assertIn('SELECTED-BOOKING', self.client.get(self.url, {'customer_id':self.customer.pk}).json()['booking_history_html'])

    def test_shared_email_requires_unambiguous_customer(self):
        Customer.objects.create(first_name='OTHER-NAME', email=self.customer.email)
        self.assertEqual(self.client.get(self.url, {'email':self.customer.email}).json(), {'found':False,'ambiguous':True})
        data = self.client.get(self.url, {'email':self.customer.email,'full_name':'TEST-FIRST'}).json()
        self.assertEqual(data['id'], self.customer.pk)

    def test_history_values_are_escaped_and_response_not_cached(self):
        self.group.group_name = '<script>TEST</script>'
        self.group.save(update_fields=['group_name'])
        self.booking(supplier_booking_number='SAFE-NUMBER')
        response = self.client.get(self.url, {'email':self.customer.email})
        self.assertIn('&lt;script&gt;TEST&lt;/script&gt;', response.json()['booking_history_html'])
        self.assertIn('no-store', response.headers['Cache-Control'])

    def test_history_block_is_before_vehicle_choices(self):
        response = self.client.get(reverse('quotes:new_inquiry'))
        content = response.content.decode()
        self.assertLess(content.index('id="customer-history"'),content.index('id="vehicle-choice-title"'))
