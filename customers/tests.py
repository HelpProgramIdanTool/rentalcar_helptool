from datetime import date

from django.contrib import admin
from django.test import TestCase

from bookings.models import Booking

from .models import Customer, CustomerEvent


class CustomerTests(TestCase):
    def test_customer_can_have_three_phone_numbers_and_home_address(self):
        customer = Customer.objects.create(
            first_name="Anna",
            last_name="Nowak",
            phone_1="+48 111 111 111",
            phone_2="+972 222 222 222",
            phone_3="+48 333 333 333",
            country="Poland",
            city="Warsaw",
            address="Example Street 1",
            postal_code="00-001",
        )

        self.assertEqual(customer.phone_3, "+48 333 333 333")
        self.assertEqual(customer.address, "Example Street 1")

    def test_customer_email_is_not_unique(self):
        Customer.objects.create(
            first_name="Anna",
            last_name="Nowak",
            email="shared@example.com",
            phone_1="+48 111 111 111",
        )

        second_customer = Customer.objects.create(
            first_name="Jan",
            last_name="Kowalski",
            email="shared@example.com",
            phone_1="+48 222 222 222",
        )

        self.assertEqual(second_customer.email, "shared@example.com")

    def test_customer_can_store_invoice_preference_and_details(self):
        customer = Customer.objects.create(
            first_name="Anna",
            last_name="Nowak",
            phone_1="+48 111 111 111",
            wants_invoice=True,
            invoice_name="Example Company Sp. z o.o.",
            invoice_tax_id="PL1234567890",
            invoice_country="Poland",
            invoice_city="Warsaw",
            invoice_address="Business Street 2",
            invoice_postal_code="00-002",
            invoice_email="invoice@example.com",
        )

        self.assertTrue(customer.wants_invoice)
        self.assertEqual(customer.invoice_tax_id, "PL1234567890")
        self.assertEqual(customer.invoice_address, "Business Street 2")

    def test_customer_event_is_visible_in_customer_history(self):
        customer = Customer.objects.create(
            first_name="Anna",
            last_name="Nowak",
            phone_1="+48 111 111 111",
        )
        event = CustomerEvent.objects.create(
            customer=customer,
            event_type=CustomerEvent.EventType.REFUSAL,
            event_date=date(2026, 8, 27),
            title="Customer declined the offer",
        )

        self.assertEqual(list(customer.events.all()), [event])

    def test_customer_and_events_are_available_in_admin(self):
        self.assertIn(Customer, admin.site._registry)
        self.assertIn(CustomerEvent, admin.site._registry)

    def test_customer_admin_shows_related_booking_history(self):
        customer_admin = admin.site._registry[Customer]

        self.assertTrue(
            any(inline.model is Booking for inline in customer_admin.inlines)
        )
