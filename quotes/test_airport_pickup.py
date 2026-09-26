from types import SimpleNamespace

from django.test import TestCase

from suppliers.models import AirportPickupWording, Supplier, SupplierLocation

from .airport_pickup import airport_code_for_city, airport_pickup_messages, airport_service_messages


class AirportPickupTests(TestCase):
    def setUp(self):
        self.desk_supplier = Supplier.objects.create(supplier_code="DESK_TEST", supplier_name="Desk test")
        self.meet_supplier = Supplier.objects.create(supplier_code="MEET_TEST", supplier_name="Meet test")
        for supplier, desk, meet in (
            (self.desk_supplier, True, False),
            (self.meet_supplier, False, True),
        ):
            SupplierLocation.objects.create(
                supplier=supplier, location_code="KRK", location_name="Airport",
                city="Kraków", location_type="AIRPORT", airport_code="KRK",
                has_rental_desk=desk, supports_terminal_delivery=meet,
                supports_return=supplier == self.desk_supplier,
            )

    def test_airport_offer_uses_each_suppliers_confirmed_method(self):
        quote = SimpleNamespace(pickup_service="AIRPORT", pickup_city="Kraków")
        messages = airport_pickup_messages(quote, {self.desk_supplier.pk, self.meet_supplier.pk})
        self.assertEqual(messages[self.desk_supplier.pk], AirportPickupWording.objects.get(method_code="DESK").text_he)
        self.assertEqual(messages[self.meet_supplier.pk], AirportPickupWording.objects.get(method_code="MEET").text_he)

    def test_missing_location_uses_agreed_uncertain_message(self):
        quote = SimpleNamespace(pickup_service="AIRPORT", pickup_city="Unknown")
        messages = airport_pickup_messages(quote, {self.desk_supplier.pk})
        self.assertEqual(messages[self.desk_supplier.pk], AirportPickupWording.objects.get(method_code="UNKNOWN").text_he)

    def test_non_airport_pickup_has_no_airport_message(self):
        quote = SimpleNamespace(pickup_service="ADDRESS", pickup_city="Kraków")
        self.assertEqual(airport_pickup_messages(quote, {self.desk_supplier.pk}), {})

    def test_city_with_more_than_one_airport_is_not_guessed(self):
        SupplierLocation.objects.create(
            supplier=self.desk_supplier, location_code="KRK2", location_name="Another airport",
            city="Kraków North", location_type="AIRPORT", airport_code="KRN",
        )
        self.assertIsNone(airport_code_for_city("Kraków"))

    def test_airport_return_method_appears_when_pickup_is_at_an_address(self):
        quote = SimpleNamespace(
            pickup_service="ADDRESS", pickup_city="Kraków",
            return_service="AIRPORT", return_city="Kraków",
        )

        messages = airport_service_messages(
            quote, {self.desk_supplier.pk, self.meet_supplier.pk}
        )

        self.assertEqual(
            messages[self.desk_supplier.pk],
            AirportPickupWording.objects.get(method_code="RETURN_DESK").text_he,
        )
        self.assertEqual(
            messages[self.meet_supplier.pk],
            AirportPickupWording.objects.get(method_code="RETURN_MEET").text_he,
        )

    def test_collection_and_return_methods_are_both_in_the_offer(self):
        quote = SimpleNamespace(
            pickup_service="AIRPORT", pickup_city="Kraków",
            return_service="AIRPORT", return_city="Kraków",
        )

        message = airport_service_messages(quote, {self.desk_supplier.pk})[
            self.desk_supplier.pk
        ]

        self.assertIn(AirportPickupWording.objects.get(method_code="DESK").text_he, message)
        self.assertIn(AirportPickupWording.objects.get(method_code="RETURN_DESK").text_he, message)
