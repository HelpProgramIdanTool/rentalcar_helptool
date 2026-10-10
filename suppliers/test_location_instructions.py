from types import SimpleNamespace
from django.test import TestCase, SimpleTestCase
from suppliers.models import Supplier, SupplierLocation
from quotes.airport_pickup import airport_service_messages
from bookings.message_content import supplier_location


class LocationInstructionTests(TestCase):
    def test_each_operation_uses_its_own_language_specific_instructions(self):
        supplier=Supplier.objects.create(supplier_code='LOCATION-TEST',supplier_name='Test Location')
        SupplierLocation.objects.create(supplier=supplier,location_code='TEST',location_name='Test Airport',city='Test City',airport_code='TST',location_type='AIRPORT',
            supports_terminal_delivery=True,localized_service_instructions={
                'pickup':{'Hebrew':'TEST-PICKUP-HE','Russian':'TEST-PICKUP-RU'},
                'return':{'Hebrew':'TEST-RETURN-HE','Russian':'TEST-RETURN-RU'},
            })
        quote=SimpleNamespace(pickup_service='AIRPORT',return_service='AIRPORT',pickup_city='Test City',return_city='Test City')
        self.assertEqual(airport_service_messages(quote,[supplier.pk],'Hebrew')[supplier.pk], 'TEST-PICKUP-HE\nTEST-RETURN-HE')
        self.assertEqual(airport_service_messages(quote,[supplier.pk],'Russian')[supplier.pk], 'TEST-PICKUP-RU\nTEST-RETURN-RU')


class SupplierMessageLocationTests(SimpleTestCase):
    def test_airport_instructions_are_not_in_supplier_order_message(self):
        for side in ('pickup', 'return'):
            with self.subTest(side=side):
                booking = SimpleNamespace(
                    source_quote_snapshot={'request': {
                        f'{side}_city': 'Test City', f'{side}_service': 'AIRPORT',
                    }},
                    **{
                        f'{side}_address': '',
                        f'{side}_location': SimpleNamespace(**{
                            f'default_{side}_instructions': 'TEST-CUSTOMER-INSTRUCTIONS',
                        }),
                    },
                )
                self.assertEqual(supplier_location(booking, side), 'Test City Airport')
