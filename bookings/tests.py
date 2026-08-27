from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from customers.models import Customer
from suppliers.models import Supplier

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
