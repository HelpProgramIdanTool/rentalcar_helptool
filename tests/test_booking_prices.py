from decimal import Decimal

from django.test import SimpleTestCase

from bookings.models import Booking, BookingExtra
from suppliers.models import SupplierExtra


class BookingPriceTests(SimpleTestCase):
    """Exercise individual price rules using unsaved objects only."""

    def test_manual_price_replaces_vehicle_price_but_keeps_calculated_value(self):
        booking = Booking(
            vehicle_price_gross=Decimal("300"),
            calculated_vehicle_price_gross=Decimal("300"),
            manual_vehicle_price_gross=Decimal("250"),
        )
        booking._apply_manual_vehicle_price()
        self.assertEqual(booking.vehicle_price_gross, Decimal("250"))
        self.assertEqual(booking.calculated_vehicle_price_gross, Decimal("300"))
        self.assertEqual(booking.price_calculation_status, Booking.PriceCalculationStatus.OVERRIDDEN)

    def test_zero_manual_price_is_a_real_override(self):
        booking = Booking(vehicle_price_gross=Decimal("300"), manual_vehicle_price_gross=Decimal("0"))
        booking._apply_manual_vehicle_price()
        self.assertEqual(booking.vehicle_price_gross, Decimal("0"))
        self.assertEqual(booking.price_calculation_status, Booking.PriceCalculationStatus.OVERRIDDEN)

    def test_empty_manual_price_keeps_calculated_price_and_status(self):
        booking = Booking(vehicle_price_gross=Decimal("300"),
                          price_calculation_status=Booking.PriceCalculationStatus.CALCULATED)
        booking._apply_manual_vehicle_price()
        self.assertEqual(booking.vehicle_price_gross, Decimal("300"))
        self.assertEqual(booking.price_calculation_status, Booking.PriceCalculationStatus.CALCULATED)

    def test_extra_uses_saved_unit_price_and_quantity_without_loading_a_rate(self):
        item = BookingExtra(
            booking=Booking(rental_days=4), extra=SupplierExtra(extra_code="TEST-EXTRA"),
            calculation_type_snapshot="PER_RENTAL", unit_price_gross_snapshot=Decimal("50"),
            quantity=Decimal("2"),
        )
        self.assertEqual(item._calculate_price(), Decimal("100"))
        self.assertTrue(item.calculation_complete)

    def test_daily_extra_uses_saved_price_and_booking_duration(self):
        item = BookingExtra(
            booking=Booking(rental_days=4), extra=SupplierExtra(extra_code="TEST-EXTRA"),
            calculation_type_snapshot="PER_DAY", unit_price_gross_snapshot=Decimal("50"),
            quantity=Decimal("2"),
        )
        self.assertEqual(item._calculate_price(), Decimal("400"))
