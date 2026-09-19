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


class ParseBookingTests(SimpleTestCase):
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
    def test_authentication_and_no_booking_created(self):
        url = reverse('quotes:paste_booking')
        self.assertEqual(self.client.post(url, {'text': SAMPLE}).status_code, 302)
        self.client.force_login(get_user_model().objects.create_user(username='paste-test'))
        self.assertEqual(self.client.post(url, {'text': SAMPLE}).status_code, 200)
        self.assertEqual(Booking.objects.count(), 0)
        self.assertEqual(self.client.post(url, {'text': ''}).status_code, 400)
