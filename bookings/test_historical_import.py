from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from bookings.models import Booking
from customers.models import Customer
from suppliers.models import Supplier


class HistoricalImportTests(TestCase):
    def test_import_save_and_status_change_preserve_original_total(self):
        supplier = Supplier.objects.create(supplier_code="IMPORT_TEST", supplier_name="Test")
        customer = Customer.objects.create(first_name="Test")
        with patch.object(Booking, "_calculate_vehicle_price", side_effect=AssertionError("Repriced")), patch.object(Booking, "_sync_mandatory_extras", side_effect=AssertionError("Added extras")):
            booking = Booking.objects.create(supplier=supplier, customer=customer,
                total_price_gross=Decimal("1234"),
                source_quote_snapshot={"historical_import": {"row": 2, "raw": {"D": "TEST-GROUP"}},
                    "supplier_statement": {"period": "TEST-PERIOD"}})
            booking.status = Booking.Status.COMPLETED
            booking.save()
            booking.recalculate_totals()
        booking.refresh_from_db()
        self.assertEqual(booking.total_price_gross, Decimal("1234"))
        self.assertEqual(booking.status, Booking.Status.COMPLETED)
        self.assertFalse(booking.extras.exists())
        self.client.force_login(get_user_model().objects.create_user(username="import_test"))
        for name, args in [("quotes:booking_detail", [booking.pk]), ("quotes:booking_list", [])]:
            response = self.client.get(reverse(name, args=args))
            self.assertContains(response, "TEST-PERIOD")
            self.assertContains(response, "TEST-GROUP")
