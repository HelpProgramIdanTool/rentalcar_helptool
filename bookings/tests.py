from datetime import datetime, timedelta, timezone

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from customers.models import Customer
from suppliers.models import Supplier, SupplierLocation, VehicleGroup

from .models import Booking, BookingDriver


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
