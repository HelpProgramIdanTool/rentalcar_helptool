from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from quotes.services import _service_extra_requests


class OneRentAirportFeeTests(SimpleTestCase):
    def test_fee_applies_only_when_car_is_collected_at_airport(self):
        for pickup, returning, expected in (
            ("AIRPORT", "ADDRESS", {"AIRPORT_FEE": Decimal("1")}),
            ("AIRPORT", "AIRPORT", {"AIRPORT_FEE": Decimal("1")}),
            ("ADDRESS", "AIRPORT", {}),
            ("ADDRESS", "ADDRESS", {}),
        ):
            with self.subTest(pickup=pickup, returning=returning):
                quote = SimpleNamespace(pickup_service=pickup, return_service=returning)
                self.assertEqual(_service_extra_requests(quote, "02"), expected)
