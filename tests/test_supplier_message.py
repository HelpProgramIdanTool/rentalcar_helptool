from decimal import Decimal
from types import SimpleNamespace

from django.test import SimpleTestCase

from bookings.message_content import price_breakdown, supplier_location


class SupplierPriceBreakdownTests(SimpleTestCase):
    def booking(self, base="500", total="650", daily="100"):
        return SimpleNamespace(vehicle_price_gross=Decimal(base), total_price_gross=Decimal(total),
            vehicle_daily_rate_gross_snapshot=Decimal(daily), rental_days=5, currency="PLN")

    def extra(self, amount, included=True, complete=True):
        return SimpleNamespace(calculated_price_gross=Decimal(amount), included_in_total=included, calculation_complete=complete)

    def test_equation_uses_saved_days_rate_and_extras(self):
        self.assertEqual(price_breakdown(self.booking(), [self.extra("50"), self.extra("100")]), "5x100+50+100=650 PLN")

    def test_manual_price_does_not_show_a_false_daily_equation(self):
        self.assertEqual(price_breakdown(self.booking(base="400", total="450"), [self.extra("50")]), "400+50=450 PLN")

    def test_excluded_and_incomplete_extras_are_not_added(self):
        self.assertEqual(price_breakdown(self.booking(total="500"), [self.extra("50", included=False), self.extra("100", complete=False)]), "5x100=500 PLN")

    def test_inconsistent_saved_total_requests_verification(self):
        self.assertEqual(price_breakdown(self.booking(total="999"), []), "Total: 999 PLN [please verify breakdown]")

    def test_location_uses_supplier_facing_labels_and_preserves_address(self):
        booking = SimpleNamespace(source_quote_snapshot={"request": {
            "pickup_city": "Test city", "pickup_service": "ADDRESS",
            "return_city": "Test city", "return_service": "AIRPORT"}},
            pickup_address="Example street 10", return_address="",
            pickup_location_text="", return_location_text="")
        self.assertEqual(supplier_location(booking, "pickup"), "Example street 10, Test city")
        self.assertEqual(supplier_location(booking, "return"), "Test city Airport")
