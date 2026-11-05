from django.test import SimpleTestCase, TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from .paste_entry import parse_booking_text
from .models import Booking

SAMPLE = '''Test Driver // Second Driver
48123456789
test@example.com
24/9/26, 15:00, Central railway station in Lublin
1/10/26, 15:00, Krakow Central Railway station
7 days
B MANUAL
Additional driver for free + full insurance
7x100+50=750//300
Example street 10
'''

LABELED = '''Customer name:** TEST DRIVER**
Customer phone number:** 48000111222**
Customer email: [**visible@example.test**](mailto:different@example.test)
Pickup details: **23/11/2026, 18:00, Kraków-Balice Airport (LY 1234)**
Drop off details:** 25/11/2026, 08:30, Kraków-Balice Airport**
Duration:** 2 days**
Category:** TEST CATEGORY**
Extras:** Additional driver for free + full insurance with no application fee for damage **
Final price:** 2x100 = 200 || 500**
**Test Street 5, Test Town**'''


class ParseBookingTests(SimpleTestCase):
    def test_labeled_markdown_request_prefills_manual_customer_and_trip(self):
        data=parse_booking_text(LABELED.replace('Customer name:', 'Customer name:&#xA0;'))
        self.assertEqual(data['customer_name'],'TEST DRIVER')
        self.assertEqual(data['driver_names'],'TEST DRIVER')
        self.assertEqual(data['driver_count'],1)
        self.assertEqual(data['email'],'visible@example.test')
        self.assertEqual(data['phone_1'],'48000111222')
        self.assertEqual(data['pickup_date'],'23-11-2026')
        self.assertEqual(data['pickup_time'],'18:00')
        self.assertEqual(data['return_date'],'25-11-2026')
        self.assertEqual(data['return_time'],'08:30')
        self.assertEqual(data['pickup_city'],'Kraków')
        self.assertEqual(data['return_city'],'Kraków')
        self.assertEqual(data['flight_number'],'LY 1234')
        self.assertEqual(data['vehicle_note'],'TEST CATEGORY')
        self.assertEqual(data['pasted_total_gross'],'200.00')
        self.assertEqual(data['pasted_deposit'],'500.00')
        self.assertEqual(data['address'],'Test Street 5, Test Town')
        self.assertIn('2x100 = 200 || 500',data['internal_notes'])
        self.assertEqual(data['customer_notes'],LABELED.replace('Customer name:', 'Customer name:&#xA0;'))

    def test_html_mail_uses_visible_email_instead_of_different_link_target(self):
        source=LABELED.replace('**','')
        source=source.replace('[visible@example.test](mailto:different@example.test)',
            '<a href="mailto:different@example.test"><b>visible@example.test</b></a>')
        source='<div>'+'</div><div>'.join(source.splitlines())+'</div>'
        data=parse_booking_text(source)
        self.assertEqual(data['email'],'visible@example.test')
        self.assertEqual(data['customer_name'],'TEST DRIVER')
        self.assertEqual(data['pasted_total_gross'],'200.00')

    def test_label_can_be_on_separate_line_and_legacy_format_remains_supported(self):
        data=parse_booking_text(LABELED.replace('Customer name:** TEST DRIVER**',
            'Customer name:\nTEST DRIVER'))
        self.assertEqual(data['customer_name'],'TEST DRIVER')
        compact=parse_booking_text(SAMPLE)
        self.assertEqual(compact['customer_name'],'Test Driver')
        self.assertEqual(compact['pasted_total_gross'],'750.00')
        self.assertEqual(compact['pasted_deposit'],'300.00')

    def test_compact_request(self):
        data = parse_booking_text(SAMPLE)
        self.assertEqual(data['driver_count'], 2)
        self.assertEqual(data['driver_names'], 'Test Driver\nSecond Driver')
        self.assertEqual(data['pickup_date'], '24-09-2026')
        self.assertEqual(data['return_date'], '01-10-2026')
        self.assertEqual(data['pickup_city'], 'Lublin')
        self.assertEqual(data['return_city'], 'Kraków')
        self.assertEqual(data['pickup_service'], 'ADDRESS')
        self.assertEqual(data['return_address'], 'Krakow Central Railway station')
        self.assertEqual(data['vehicle_note'], 'B MANUAL')
        self.assertEqual(data['address'], 'Example street 10')
        self.assertIn('750//300', data['internal_notes'])
        self.assertEqual(data['customer_notes'], SAMPLE)

    def test_invalid_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_booking_text(SAMPLE.replace('24/9/26','32/9/26'))

    def test_incomplete_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_booking_text('Only a name')


class PasteBookingViewTests(TestCase):
    def test_labeled_request_only_returns_fields_without_creating_order(self):
        self.client.force_login(get_user_model().objects.create_user(username='labeled-paste-test'))
        response=self.client.post(reverse('quotes:paste_booking'),{'text':LABELED})
        self.assertEqual(response.status_code,200)
        self.assertEqual(response.json()['fields']['customer_name'],'TEST DRIVER')
        self.assertEqual(response.json()['fields']['flight_number'],'LY 1234')
        self.assertEqual(Booking.objects.count(),0)
    def test_authentication_and_no_booking_created(self):
        url = reverse('quotes:paste_booking')
        self.assertEqual(self.client.post(url, {'text': SAMPLE}).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user(username='paste-test'))
        self.assertEqual(self.client.post(url, {'text': SAMPLE}).status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(self.client.post(url, {'text': ''}).status_code, 400)
