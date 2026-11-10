from types import SimpleNamespace
from django.test import SimpleTestCase
from .message_content import supplier_location


class SupplierHotelLocationTests(SimpleTestCase):
    def booking(self, hotel='', address=''):
        return SimpleNamespace(source_quote_snapshot={'request': {
            'return_city': 'TEST-CITY', 'return_service': 'ADDRESS',
            'pickup_city': 'TEST-CITY', 'pickup_service': 'ADDRESS'}},
            return_address=address, return_hotel_name=hotel,
            pickup_address=address, hotel_name=hotel)

    def test_return_hotel_and_address_are_in_location(self):
        self.assertEqual(supplier_location(self.booking('TEST-HOTEL', 'TEST-STREET'), 'return'),
                         'TEST-HOTEL, TEST-STREET, TEST-CITY')

    def test_hotel_without_street_does_not_show_placeholder(self):
        self.assertEqual(supplier_location(self.booking('TEST-HOTEL'), 'return'),
                         'TEST-HOTEL, TEST-CITY')

    def test_pickup_uses_pickup_hotel(self):
        self.assertEqual(supplier_location(self.booking('TEST-HOTEL', 'TEST-STREET'), 'pickup'),
                         'TEST-HOTEL, TEST-STREET, TEST-CITY')

    def test_missing_location_still_requests_address(self):
        self.assertEqual(supplier_location(self.booking(), 'return'), '[street address], TEST-CITY')
