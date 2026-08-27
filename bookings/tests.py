from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from customers.models import Customer
from suppliers.models import (
    Supplier,
    SupplierExtra,
    SupplierExtraRate,
    SupplierLocation,
    PriceDayRange,
    PriceList,
    PriceSeason,
    VehicleGroup,
    VehicleRate,
)

from .models import Booking, BookingDriver, BookingExtra


class BookingTests(TestCase):
    def setUp(self):
        self.customer = Customer.objects.create(
            first_name="Anna",
            last_name="Nowak",
            phone_1="+48 111 111 111",
        )
        self.supplier = Supplier.objects.create(
            supplier_code="TEST",
            supplier_name="Test Supplier",
        )

    def create_booking(self, **kwargs):
        return Booking.objects.create(
            customer=self.customer,
            supplier=self.supplier,
            **kwargs,
        )

    def create_vehicle_rate(
        self,
        vehicle_group,
        daily_rate="100.00",
        days_from=1,
        days_to=None,
    ):
        price_list = PriceList.objects.create(
            supplier=self.supplier,
            name="Test price list",
            version=f"TEST-{PriceList.objects.count() + 1}",
            effective_from=date(2026, 1, 1),
            status=PriceList.Status.ACTIVE,
        )
        season = PriceSeason.objects.create(
            price_list=price_list,
            season_code="ALL",
            season_name="All year",
            rental_date_from=date(2026, 1, 1),
            rental_date_to=date(2026, 12, 31),
        )
        day_range = PriceDayRange.objects.create(
            price_list=price_list,
            range_code="ALL",
            label="All days",
            days_from=days_from,
            days_to=days_to,
        )
        return VehicleRate.objects.create(
            season=season,
            vehicle_group=vehicle_group,
            day_range=day_range,
            daily_rate_gross=Decimal(daily_rate),
        )

    def test_internal_number_is_created_and_never_uses_supplier_number(self):
        booking = self.create_booking(supplier_booking_number="SUP-999")

        self.assertRegex(booking.booking_number, r"^RC-\d{4}-00001$")
        self.assertNotEqual(booking.booking_number, booking.supplier_booking_number)

    def test_booking_numbers_increase(self):
        first = self.create_booking()
        second = self.create_booking()

        self.assertEqual(first.booking_number[-5:], "00001")
        self.assertEqual(second.booking_number[-5:], "00002")

    def test_supplier_number_can_be_empty_while_waiting(self):
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            status=Booking.Status.WAITING_CONFIRMATION,
        )

        booking.full_clean()

    def test_confirmed_booking_requires_supplier_number(self):
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            status=Booking.Status.CONFIRMED,
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_six_hour_rental_counts_as_one_day(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=6),
        )

        self.assertEqual(booking.rental_days, 1)

    def test_exactly_twenty_four_hours_counts_as_one_day(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=24),
        )

        self.assertEqual(booking.rental_days, 1)

    def test_one_minute_over_twenty_four_hours_counts_as_two_days(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=24, minutes=1),
        )

        self.assertEqual(booking.rental_days, 2)

    def test_return_before_pickup_is_rejected(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            pickup_datetime=pickup,
            return_datetime=pickup - timedelta(minutes=1),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_booking_stores_locations_addresses_flight_and_vehicle_group(self):
        pickup_location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="WAW",
            location_name="Warsaw Airport",
            city="Warsaw",
            address="Zwirki i Wigury 1",
        )
        return_location = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="CITY",
            location_name="Warsaw City",
            city="Warsaw",
        )
        vehicle_group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="CDAR",
            group_name="C Automatic",
        )

        booking = self.create_booking(
            pickup_location=pickup_location,
            return_location=return_location,
            pickup_address="Customer address 1",
            return_address="Hotel address 2",
            hotel_name="Test Hotel",
            flight_number="LO123",
            vehicle_group=vehicle_group,
        )

        self.assertEqual(booking.pickup_address, "Customer address 1")
        self.assertEqual(booking.return_address, "Hotel address 2")
        self.assertEqual(booking.flight_number, "LO123")
        self.assertEqual(booking.vehicle_group, vehicle_group)
        self.assertIn("Warsaw Airport", booking.pickup_location_text)

    def test_location_of_another_supplier_is_rejected(self):
        other_supplier = Supplier.objects.create(
            supplier_code="OTHER",
            supplier_name="Other Supplier",
        )
        other_location = SupplierLocation.objects.create(
            supplier=other_supplier,
            location_code="OTHER-WAW",
            location_name="Other Warsaw",
            city="Warsaw",
        )
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            pickup_location=other_location,
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_vehicle_group_of_another_supplier_is_rejected(self):
        other_supplier = Supplier.objects.create(
            supplier_code="OTHER-GROUP",
            supplier_name="Other Group Supplier",
        )
        other_group = VehicleGroup.objects.create(
            supplier=other_supplier,
            group_code="CDAR",
            group_name="Other C Automatic",
        )
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            vehicle_group=other_group,
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_total_is_base_vehicle_price_plus_extras(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        vehicle_group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="PRICE-CDAR",
            group_name="Price C Automatic",
        )
        self.create_vehicle_rate(vehicle_group, daily_rate="100.00")
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=72),
            vehicle_group=vehicle_group,
        )
        child_seat = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="CHILD_SEAT",
            name="Child seat",
        )
        child_seat_rate = SupplierExtraRate.objects.create(
            extra=child_seat,
            rate_code="DAILY",
            calculation_type=SupplierExtraRate.CalculationType.PER_DAY,
            amount_gross=Decimal("20.00"),
            valid_from=date(2026, 1, 1),
        )

        BookingExtra.objects.create(
            booking=booking,
            extra=child_seat,
            rate=child_seat_rate,
            quantity=1,
        )
        booking.refresh_from_db()

        self.assertEqual(booking.extras_total_gross, Decimal("60.00"))
        self.assertEqual(booking.calculated_vehicle_price_gross, Decimal("300.00"))
        self.assertEqual(booking.total_price_gross, Decimal("360.00"))

    def test_one_rent_mandatory_delivery_is_added_automatically(self):
        self.supplier.supplier_name = "One Rent"
        self.supplier.save(update_fields=["supplier_name"])
        vehicle_group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="ONE-CDAR",
            group_name="One Rent C Automatic",
        )
        self.create_vehicle_rate(vehicle_group, daily_rate="1000.00")
        mandatory_delivery = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="CITY_AIRPORT_DELIVERY",
            name="Delivery and return in city or airport",
            is_mandatory=True,
        )
        SupplierExtraRate.objects.create(
            extra=mandatory_delivery,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.FORMULA,
            amount_gross=Decimal("200.00"),
            valid_from=date(2026, 1, 1),
            formula_config={"pickup_gross": "100.00", "return_gross": "100.00"},
        )

        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=48),
            vehicle_group=vehicle_group,
        )
        booking.refresh_from_db()
        booking_extra = booking.extras.get(extra=mandatory_delivery)

        self.assertTrue(booking_extra.is_mandatory_snapshot)
        self.assertEqual(booking_extra.calculated_price_gross, Decimal("200.00"))
        self.assertEqual(booking.calculated_vehicle_price_gross, Decimal("2000.00"))
        self.assertEqual(booking.total_price_gross, Decimal("2200.00"))

    def test_booking_extra_keeps_price_snapshot_after_rate_changes(self):
        booking = self.create_booking(
            manual_vehicle_price_gross=Decimal("500.00"),
            manual_price_override_reason="Test manual price",
        )
        extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="GPS",
            name="GPS",
        )
        extra_rate = SupplierExtraRate.objects.create(
            extra=extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_RENTAL,
            amount_gross=Decimal("50.00"),
            valid_from=date(2026, 1, 1),
        )
        booking_extra = BookingExtra.objects.create(
            booking=booking,
            extra=extra,
            rate=extra_rate,
        )

        extra_rate.amount_gross = Decimal("80.00")
        extra_rate.save(update_fields=["amount_gross"])
        booking_extra.quantity = 2
        booking_extra.save()
        booking_extra.refresh_from_db()

        self.assertEqual(booking_extra.unit_price_gross_snapshot, Decimal("50.00"))
        self.assertEqual(booking_extra.calculated_price_gross, Decimal("100.00"))

    def test_extra_of_another_supplier_is_rejected(self):
        booking = self.create_booking()
        other_supplier = Supplier.objects.create(
            supplier_code="OTHER-EXTRA",
            supplier_name="Other Extra Supplier",
        )
        other_extra = SupplierExtra.objects.create(
            supplier=other_supplier,
            extra_code="GPS",
            name="GPS",
        )
        other_rate = SupplierExtraRate.objects.create(
            extra=other_extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_RENTAL,
            amount_gross=Decimal("50.00"),
            valid_from=date(2026, 1, 1),
        )
        booking_extra = BookingExtra(
            booking=booking,
            extra=other_extra,
            rate=other_rate,
        )

        with self.assertRaises(ValidationError):
            booking_extra.full_clean()

    def test_manual_vehicle_price_requires_a_reason(self):
        booking = Booking(
            customer=self.customer,
            supplier=self.supplier,
            manual_vehicle_price_gross=Decimal("900.00"),
        )

        with self.assertRaises(ValidationError):
            booking.full_clean()

    def test_manual_vehicle_price_overrides_calculated_price(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        vehicle_group = VehicleGroup.objects.create(
            supplier=self.supplier,
            group_code="OVERRIDE",
            group_name="Override Group",
        )
        self.create_vehicle_rate(vehicle_group, daily_rate="100.00")

        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(hours=48),
            vehicle_group=vehicle_group,
            manual_vehicle_price_gross=Decimal("175.00"),
            manual_price_override_reason="Supplier approved a special price",
        )

        self.assertEqual(booking.vehicle_price_gross, Decimal("175.00"))
        self.assertEqual(booking.calculated_vehicle_price_gross, Decimal("200.00"))
        self.assertEqual(
            booking.price_calculation_status,
            Booking.PriceCalculationStatus.OVERRIDDEN,
        )

    def test_car_free_cross_border_formula_adds_base_and_daily_charge(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(days=4),
        )
        cross_border = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="CROSS_BORDER",
            name="Travel abroad",
        )
        cross_border_rate = SupplierExtraRate.objects.create(
            extra=cross_border,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.FORMULA,
            amount_gross=Decimal("299.00"),
            valid_from=date(2026, 1, 1),
            formula_config={
                "per_rental_gross": "299.00",
                "per_rental_day_gross": "30.00",
            },
        )

        booking_extra = BookingExtra.objects.create(
            booking=booking,
            extra=cross_border,
            rate=cross_border_rate,
        )

        self.assertEqual(booking_extra.calculated_price_gross, Decimal("419.00"))
        self.assertTrue(booking_extra.calculation_complete)

    def test_distance_formula_is_incomplete_until_kilometres_are_entered(self):
        booking = self.create_booking()
        delivery = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="OUTSIDE_CITY_DELIVERY",
            name="Delivery outside city",
        )
        delivery_rate = SupplierExtraRate.objects.create(
            extra=delivery,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.FORMULA,
            amount_gross=Decimal("100.00"),
            valid_from=date(2026, 1, 1),
            formula_config={"per_km_gross": "2.50"},
        )
        booking_extra = BookingExtra.objects.create(
            booking=booking,
            extra=delivery,
            rate=delivery_rate,
        )
        booking.refresh_from_db()

        self.assertFalse(booking_extra.calculation_complete)
        self.assertEqual(booking.extras_total_gross, Decimal("0.00"))

        booking_extra.distance_km = Decimal("10.00")
        booking_extra.save()
        booking.refresh_from_db()

        self.assertTrue(booking_extra.calculation_complete)
        self.assertEqual(booking_extra.calculated_price_gross, Decimal("125.00"))
        self.assertEqual(booking.extras_total_gross, Decimal("125.00"))

    def test_first_two_drivers_are_free_and_later_drivers_use_supplier_rate(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(days=3),
        )
        driver_extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="ADDITIONAL_DRIVER",
            name="Additional driver",
        )
        SupplierExtraRate.objects.create(
            extra=driver_extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_DAY,
            amount_gross=Decimal("15.00"),
            valid_from=date(2026, 1, 1),
        )
        BookingDriver.objects.create(
            booking=booking,
            first_name="Driver 1",
            last_name="Test",
            role=BookingDriver.Role.MAIN,
        )
        BookingDriver.objects.create(
            booking=booking,
            first_name="Driver 2",
            last_name="Test",
            role=BookingDriver.Role.ADDITIONAL,
        )

        self.assertFalse(booking.extras.filter(extra=driver_extra).exists())

        BookingDriver.objects.create(
            booking=booking,
            first_name="Driver 3",
            last_name="Test",
            role=BookingDriver.Role.ADDITIONAL,
        )
        paid_driver_extra = booking.extras.get(extra=driver_extra)
        self.assertEqual(paid_driver_extra.calculated_price_gross, Decimal("45.00"))

        BookingDriver.objects.create(
            booking=booking,
            first_name="Driver 4",
            last_name="Test",
            role=BookingDriver.Role.ADDITIONAL,
        )
        paid_driver_extra.refresh_from_db()
        self.assertEqual(paid_driver_extra.quantity, Decimal("2.00"))
        self.assertEqual(paid_driver_extra.calculated_price_gross, Decimal("90.00"))

    def test_young_driver_fee_uses_matching_drivers_and_rental_days(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(days=3),
        )
        young_driver_extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="YOUNG_DRIVER",
            name="Young driver",
        )
        SupplierExtraRate.objects.create(
            extra=young_driver_extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_DRIVER_DAY,
            amount_gross=Decimal("29.99"),
            valid_from=date(2026, 1, 1),
        )
        for order in range(1, 3):
            BookingDriver.objects.create(
                booking=booking,
                first_name=f"Young {order}",
                last_name="Driver",
                role=(
                    BookingDriver.Role.MAIN
                    if order == 1
                    else BookingDriver.Role.ADDITIONAL
                ),
                young_driver_status=True,
            )

        fee = booking.extras.get(extra=young_driver_extra)

        self.assertEqual(fee.calculated_price_gross, Decimal("179.94"))

    def test_night_service_counts_pickup_and_return_events(self):
        night_extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="NIGHT_SERVICE",
            name="Night service",
        )
        SupplierExtraRate.objects.create(
            extra=night_extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_UNIT,
            amount_gross=Decimal("70.00"),
            valid_from=date(2026, 1, 1),
        )
        warsaw = ZoneInfo("Europe/Warsaw")

        booking = self.create_booking(
            pickup_datetime=datetime(2026, 9, 1, 21, 0, tzinfo=warsaw),
            return_datetime=datetime(2026, 9, 2, 7, 0, tzinfo=warsaw),
        )
        fee = booking.extras.get(extra=night_extra)

        self.assertEqual(fee.quantity, Decimal("2.00"))
        self.assertEqual(fee.calculated_price_gross, Decimal("140.00"))

    def test_kaizen_selected_airports_do_not_charge_night_service(self):
        self.supplier.supplier_name = "Kaizen Rent"
        self.supplier.save(update_fields=["supplier_name"])
        airport = SupplierLocation.objects.create(
            supplier=self.supplier,
            location_code="KRK-AIRPORT",
            location_name="Krakow Airport",
            city="Krakow",
            location_type=SupplierLocation.LocationType.AIRPORT,
            airport_code="KRK",
        )
        night_extra = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="NIGHT_SERVICE",
            name="Night service",
        )
        SupplierExtraRate.objects.create(
            extra=night_extra,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_UNIT,
            amount_gross=Decimal("70.00"),
            valid_from=date(2026, 1, 1),
        )
        warsaw = ZoneInfo("Europe/Warsaw")

        booking = self.create_booking(
            pickup_datetime=datetime(2026, 9, 1, 21, 0, tzinfo=warsaw),
            return_datetime=datetime(2026, 9, 2, 7, 0, tzinfo=warsaw),
            pickup_location=airport,
            return_location=airport,
        )

        self.assertFalse(booking.extras.filter(extra=night_extra).exists())

    def test_daily_extra_respects_maximum_price(self):
        pickup = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)
        booking = self.create_booking(
            pickup_datetime=pickup,
            return_datetime=pickup + timedelta(days=15),
        )
        child_seat = SupplierExtra.objects.create(
            supplier=self.supplier,
            extra_code="CHILD_SEAT_CAP",
            name="Child seat",
        )
        child_seat_rate = SupplierExtraRate.objects.create(
            extra=child_seat,
            rate_code="DEFAULT",
            calculation_type=SupplierExtraRate.CalculationType.PER_DAY,
            amount_gross=Decimal("20.00"),
            maximum_amount_gross=Decimal("200.00"),
            valid_from=date(2026, 1, 1),
        )

        fee = BookingExtra.objects.create(
            booking=booking,
            extra=child_seat,
            rate=child_seat_rate,
        )

        self.assertEqual(fee.calculated_price_gross, Decimal("200.00"))

    def test_booking_copies_customer_and_invoice_details(self):
        self.customer.email = "customer@example.com"
        self.customer.phone_2 = "+972 222 222 222"
        self.customer.country = "Israel"
        self.customer.city = "Tel Aviv"
        self.customer.address = "Customer Street 1"
        self.customer.postal_code = "61000"
        self.customer.wants_invoice = True
        self.customer.invoice_name = "Customer Company Ltd"
        self.customer.invoice_tax_id = "IL123456789"
        self.customer.invoice_country = "Israel"
        self.customer.invoice_city = "Tel Aviv"
        self.customer.invoice_address = "Invoice Street 2"
        self.customer.invoice_postal_code = "62000"
        self.customer.invoice_email = "invoice@example.com"
        self.customer.save()

        booking = self.create_booking()

        self.assertEqual(booking.customer_email_snapshot, "customer@example.com")
        self.assertEqual(booking.customer_phone_2_snapshot, "+972 222 222 222")
        self.assertEqual(booking.customer_address_snapshot, "Customer Street 1")
        self.assertTrue(booking.wants_invoice_snapshot)
        self.assertEqual(booking.invoice_tax_id_snapshot, "IL123456789")
        self.assertEqual(booking.invoice_address_snapshot, "Invoice Street 2")

    def test_customer_changes_do_not_rewrite_existing_booking_snapshot(self):
        self.customer.email = "original@example.com"
        self.customer.invoice_tax_id = "ORIGINAL-TAX-ID"
        self.customer.save()
        booking = self.create_booking()

        self.customer.email = "new@example.com"
        self.customer.invoice_tax_id = "NEW-TAX-ID"
        self.customer.save()
        booking.status = Booking.Status.WAITING_CONFIRMATION
        booking.save()
        booking.refresh_from_db()

        self.assertEqual(booking.customer_email_snapshot, "original@example.com")
        self.assertEqual(booking.invoice_tax_id_snapshot, "ORIGINAL-TAX-ID")

    def test_booking_accepts_main_and_second_driver(self):
        booking = self.create_booking()
        BookingDriver.objects.create(
            booking=booking,
            customer=self.customer,
            first_name="Anna",
            last_name="Nowak",
            role=BookingDriver.Role.MAIN,
            display_order=1,
        )
        second_driver = BookingDriver.objects.create(
            booking=booking,
            first_name="Jan",
            last_name="Nowak",
            role=BookingDriver.Role.ADDITIONAL,
            display_order=2,
        )

        self.assertEqual(booking.drivers.count(), 2)
        self.assertEqual(second_driver.role, BookingDriver.Role.ADDITIONAL)

    def test_booking_can_have_more_than_two_drivers(self):
        booking = self.create_booking()
        for order in range(1, 6):
            BookingDriver.objects.create(
                booking=booking,
                first_name=f"Driver {order}",
                last_name="Test",
                role=(
                    BookingDriver.Role.MAIN
                    if order == 1
                    else BookingDriver.Role.ADDITIONAL
                ),
                display_order=order,
            )

        self.assertEqual(booking.drivers.count(), 5)

    def test_only_one_main_driver_is_allowed(self):
        booking = self.create_booking()
        BookingDriver.objects.create(
            booking=booking,
            first_name="Anna",
            last_name="Nowak",
            role=BookingDriver.Role.MAIN,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            BookingDriver.objects.create(
                booking=booking,
                first_name="Jan",
                last_name="Nowak",
                role=BookingDriver.Role.MAIN,
            )
